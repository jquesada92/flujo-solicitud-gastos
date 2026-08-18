import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, exists, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import current_user, require_permission
from app.models.entities import (
    Approval,
    ApprovalStatus,
    ApprovalStepEvent,
    Expense,
    ExpenseArea,
    ExpenseAttachment,
    ExpenseStatus,
    ExpenseSubcategory,
    InvoiceChangeEvent,
    QuotationOption,
    QuotationVote,
    QuotationVoteEvent,
    QuotationVotingInvitation,
    User,
    UserRole,
)
from app.schemas.expense import AttachmentOut, ExpenseCreate, ExpenseOut, InvoiceOut
from app.services.approval_engine import expire_open_approvals, start_approval_flow
from app.services.email_service import send_quotation_vote_request

router = APIRouter()
logger = logging.getLogger(__name__)
APP_TIME_ZONE = os.getenv('APP_TIME_ZONE', 'America/Panama')
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', '/app/uploads'))
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_STORAGE_MB = int(os.getenv('MAX_UPLOAD_STORAGE_MB', '450'))
MAX_UPLOAD_STORAGE = MAX_UPLOAD_STORAGE_MB * 1024 * 1024
ALLOWED_TYPES = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}
CONTENT_SIGNATURES = {
    'application/pdf': (b'%PDF-',),
    'image/jpeg': (b'\xff\xd8\xff',),
    'image/png': (b'\x89PNG\r\n\x1a\n',),
    'image/webp': (b'RIFF',),
}
SAFE_SUFFIXES = {
    'application/pdf': '.pdf',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}


def _ensure_storage_capacity(additional_bytes: int) -> None:
    """Keep uploaded documents below the configured application storage budget."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    used_bytes = sum(path.stat().st_size for path in UPLOAD_DIR.iterdir() if path.is_file())
    if used_bytes + additional_bytes > MAX_UPLOAD_STORAGE:
        raise HTTPException(
            status_code=507,
            detail=f'El almacenamiento de documentos alcanzó su límite de {MAX_UPLOAD_STORAGE_MB} MB. Contacta al administrador.',
        )


def _validate_file_content(content: bytes, content_type: str) -> str:
    signatures = CONTENT_SIGNATURES.get(content_type)
    if not signatures or not any(content.startswith(signature) for signature in signatures):
        raise HTTPException(status_code=415, detail='El contenido del archivo no coincide con su formato declarado')
    if content_type == 'image/webp' and (len(content) < 12 or content[8:12] != b'WEBP'):
        raise HTTPException(status_code=415, detail='El archivo WEBP no es válido')
    return SAFE_SUFFIXES[content_type]


def _next_display_id(db: Session, area_code: str) -> str:
    """Generate a stable display identifier using the legacy counter table."""
    year = datetime.utcnow().year
    counter_key = f'{area_code}:{year}'
    value = db.execute(
        text('''INSERT INTO category_counters (category, last_value) VALUES (:area_key, 1)
                ON CONFLICT (category) DO UPDATE SET last_value = category_counters.last_value + 1
                RETURNING last_value'''),
        {'area_key': counter_key},
    ).scalar_one()
    prefix = area_code[:3].upper().ljust(3, 'X')[:3]
    return f'{prefix}-{year}-{value:011d}'


class CancellationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


def _user_names(db: Session) -> dict[str, str]:
    return {email.lower(): full_name for email, full_name in db.execute(select(User.email, User.name)).all()}


def _display_name(value: str | None, names: dict[str, str]) -> str | None:
    if not value:
        return None
    return names.get(value.lower(), 'Sistema')


def _as_utc(value: datetime | None) -> datetime | None:
    """Legacy timestamps are stored as naive UTC; expose one consistent zone."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _present_expense(
    expense: Expense,
    names: dict[str, str],
    last_event: ApprovalStepEvent | None = None,
    quotation_voter_count: int = 0,
) -> ExpenseOut:
    output = ExpenseOut.model_validate(expense)
    return output.model_copy(update={
        'created_at': _as_utc(expense.created_at),
        'requested_by': _display_name(output.requested_by, names),
        'cancelled_by': _display_name(output.cancelled_by, names),
        'closed_by': _display_name(output.closed_by, names),
        'approvals': [
            item.model_copy(update={'approver_name': _display_name(item.approver_email, names)})
            for item in output.approvals
        ],
        'quotation_votes': [
            item.model_copy(update={'voter_name': _display_name(item.voter_email, names)})
            for item in output.quotation_votes
        ],
        'quotation_voter_count': quotation_voter_count,
        'last_event_at': _as_utc(last_event.occurred_at) if last_event else _as_utc(expense.created_at),
        'last_event_type': last_event.event_type if last_event else 'REQUEST_CREATED',
    })


def _validate_area_selection(db: Session, area_code: str, subcategory_code: str | None) -> None:
    area = db.scalar(select(ExpenseArea).where(
        ExpenseArea.code == area_code,
        ExpenseArea.active.is_(True),
    ))
    if not area:
        raise HTTPException(status_code=422, detail='El área seleccionada no existe o está inactiva')
    if not subcategory_code:
        raise HTTPException(status_code=422, detail='Debes seleccionar una subcategoría')
    subcategory = db.scalar(select(ExpenseSubcategory).where(
        ExpenseSubcategory.area_id == area.id,
        ExpenseSubcategory.code == subcategory_code,
        ExpenseSubcategory.active.is_(True),
    ))
    if not subcategory:
        raise HTTPException(status_code=422, detail='La subcategoría no pertenece al área seleccionada o está inactiva')


@router.get('', response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != UserRole.ADMIN and not user.can_view:
        raise HTTPException(status_code=403, detail='No tienes permiso para consultar solicitudes')
    open_statuses = (
        ExpenseStatus.SUBMITTED,
        ExpenseStatus.PENDING_APPROVAL,
        ExpenseStatus.APPROVED,
        ExpenseStatus.NEEDS_REVISION,
        ExpenseStatus.QUOTATION_VOTING,
    )
    has_invoice = exists(select(ExpenseAttachment.id).where(
        ExpenseAttachment.expense_id == Expense.id,
        ExpenseAttachment.document_type == 'INVOICE',
    ))
    stmt = (
        select(Expense)
        .where(or_(
            Expense.status.in_(open_statuses),
            and_(
                Expense.status == ExpenseStatus.CLOSED,
                Expense.closed_at >= func.now() - text("INTERVAL '7 days'"),
                has_invoice,
            ),
        ))
        .options(
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
        )
        .order_by(Expense.id.desc())
    )
    if user.role == UserRole.REQUESTER:
        stmt = stmt.where(Expense.requested_by == user.email)
    names = _user_names(db)
    expenses = list(db.scalars(stmt).all())
    expense_ids = [expense.id for expense in expenses]
    latest_events = {}
    quotation_voter_counts = {}
    if expense_ids:
        events = db.scalars(select(ApprovalStepEvent).where(
            ApprovalStepEvent.expense_id.in_(expense_ids),
        ).order_by(
            ApprovalStepEvent.expense_id,
            ApprovalStepEvent.occurred_at.desc(),
            ApprovalStepEvent.event_sequence.desc(),
        )).all()
        for event in events:
            latest_events.setdefault(event.expense_id, event)
        quotation_voter_counts = dict(db.execute(select(
            QuotationVotingInvitation.expense_id,
            func.count(QuotationVotingInvitation.id),
        ).where(
            QuotationVotingInvitation.expense_id.in_(expense_ids),
        ).group_by(QuotationVotingInvitation.expense_id)).all())
    output = []
    for expense in expenses:
        event = latest_events.get(expense.id)
        lifecycle = [
            (expense.closed_at, 'REQUEST_CLOSED'),
            (expense.cancelled_at, 'REQUEST_CANCELLED'),
        ]
        lifecycle_at, lifecycle_type = max(
            ((at, kind) for at, kind in lifecycle if at),
            default=(None, None),
            key=lambda item: item[0],
        )
        if lifecycle_at and (
            not event or lifecycle_at.replace(tzinfo=None) > event.occurred_at.replace(tzinfo=None)
        ):
            presented = _present_expense(
                expense, names, event, quotation_voter_counts.get(expense.id, 0),
            ).model_copy(update={
                'last_event_at': _as_utc(lifecycle_at),
                'last_event_type': lifecycle_type,
            })
        else:
            presented = _present_expense(
                expense, names, event, quotation_voter_counts.get(expense.id, 0),
            )
        if presented.last_event_at and presented.last_event_at < presented.created_at:
            presented = presented.model_copy(update={
                'last_event_at': presented.created_at,
                'last_event_type': 'REQUEST_CREATED',
            })
        output.append(presented)
    return output


@router.get('/dashboard')
def expense_dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != UserRole.ADMIN and not user.can_view:
        raise HTTPException(status_code=403, detail='No tienes permiso para consultar el dashboard')
    now_local = datetime.now(ZoneInfo(APP_TIME_ZONE))
    now_utc = now_local.astimezone(timezone.utc).replace(tzinfo=None)
    period_start_utc = (now_local - timedelta(days=30)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    ).astimezone(timezone.utc).replace(tzinfo=None)
    open_statuses = [
        ExpenseStatus.QUOTATION_VOTING,
        ExpenseStatus.SUBMITTED,
        ExpenseStatus.PENDING_APPROVAL,
        ExpenseStatus.APPROVED,
        ExpenseStatus.NEEDS_REVISION,
    ]
    in_process = db.scalar(select(func.count(Expense.id)).where(
        Expense.status.in_(open_statuses),
    )) or 0
    closed_24h = db.scalar(select(func.count(Expense.id)).where(
        Expense.status == ExpenseStatus.CLOSED,
        Expense.closed_at >= now_utc - timedelta(hours=24),
    )) or 0
    pending_ids = set()
    if user.role != UserRole.ADMIN and user.can_approve:
        pending_ids.update(db.scalars(select(Approval.expense_id).where(
            func.lower(Approval.approver_email) == user.email.lower(),
            Approval.status == ApprovalStatus.PENDING,
        )).all())
        voted = select(QuotationVote.expense_id).where(QuotationVote.voter_user_id == user.id)
        pending_ids.update(db.scalars(select(Expense.id).where(
            Expense.status == ExpenseStatus.QUOTATION_VOTING,
            Expense.id.not_in(voted),
        )).all())
    pending_ids.update(db.scalars(select(Expense.id).where(
        Expense.status == ExpenseStatus.APPROVED,
    )).all())
    pending_items = list(db.scalars(select(Expense).where(
        Expense.id.in_(pending_ids),
    ).order_by(Expense.created_at.asc()).limit(8)).all()) if pending_ids else []
    month_rows = db.execute(select(Expense.status, func.count(Expense.id)).where(
        Expense.created_at >= period_start_utc,
    ).group_by(Expense.status)).all()
    month_by_status = {status.value: count for status, count in month_rows}
    month_amount = db.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.created_at >= period_start_utc,
        Expense.status.in_([ExpenseStatus.APPROVED, ExpenseStatus.CLOSED]),
    )) or 0
    return {
        'timezone': APP_TIME_ZONE,
        'pending_my_action': len(pending_ids),
        'in_process': in_process,
        'closed_last_24h': closed_24h,
        'last_31_days': {
            'created': sum(month_by_status.values()),
            'approved': month_by_status.get('APPROVED', 0) + month_by_status.get('CLOSED', 0),
            'closed': month_by_status.get('CLOSED', 0),
            'rejected': month_by_status.get('REJECTED', 0),
            'cancelled': month_by_status.get('CANCELLED', 0),
            'approved_amount': str(month_amount),
        },
        'pending_items': [{
            'request_id': item.request_id,
            'display_id': item.display_id,
            'title': item.title,
            'urgency': item.urgency,
            'status': item.status.value,
            'created_at': _as_utc(item.created_at),
        } for item in pending_items],
    }


@router.get('/invoices', response_model=list[InvoiceOut])
def list_invoices(
    q: str | None = Query(default=None, max_length=200),
    area: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role != UserRole.ADMIN and not user.can_view:
        raise HTTPException(status_code=403, detail='No tienes permiso para consultar facturas')
    stmt = (
        select(ExpenseAttachment, Expense)
        .join(Expense, Expense.id == ExpenseAttachment.expense_id)
        .where(ExpenseAttachment.document_type == 'INVOICE')
        .order_by(ExpenseAttachment.created_at.desc(), ExpenseAttachment.id.desc())
    )
    if user.role == UserRole.REQUESTER:
        stmt = stmt.where(Expense.requested_by == user.email)
    if area:
        stmt = stmt.where(Expense.expense_type == area)
    if q and q.strip():
        term = f'%{q.strip()}%'
        stmt = stmt.where(or_(
            ExpenseAttachment.original_name.ilike(term),
            Expense.display_id.ilike(term),
            Expense.request_id.ilike(term),
            Expense.flow_id.ilike(term),
            Expense.title.ilike(term),
            Expense.supplier.ilike(term),
            Expense.requested_by.ilike(term),
        ))
    names = _user_names(db)
    return [
        InvoiceOut(
            attachment_id=attachment.id,
            original_name=attachment.original_name,
            content_type=attachment.content_type,
            size=attachment.size,
            uploaded_at=attachment.created_at,
            request_id=expense.request_id,
            display_id=expense.display_id,
            flow_id=expense.flow_id,
            title=expense.title,
            expense_type=expense.expense_type,
            expense_subcategory=expense.expense_subcategory,
            urgency=expense.urgency,
            supplier=expense.supplier,
            amount=expense.amount,
            requested_by=_display_name(expense.requested_by, names),
            requester_analytics_id=expense.requester_analytics_id,
            expense_status=expense.status.value,
            closed_at=expense.closed_at,
            closed_by=_display_name(expense.closed_by, names),
        )
        for attachment, expense in db.execute(stmt).all()
    ]


@router.post('', response_model=ExpenseOut, status_code=201)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_request')),
):
    _validate_area_selection(db, payload.expense_type, payload.expense_subcategory)
    quotation_pending = payload.quotation_pending
    quote_values = payload.quotation_options
    values = payload.model_dump(mode='json', exclude={'quotation_pending', 'quotation_options'})
    revised_from = values.get('revised_from_request_id')
    source = None
    if revised_from:
        raise HTTPException(
            status_code=409,
            detail='Esta pantalla de corrección está desactualizada. Recarga la aplicación y usa nuevamente “Corregir / reenviar”.',
        )
    expense = Expense(
        **values,
        requested_by=user.email,
        requester_analytics_id=user.analytics_id,
        display_id=_next_display_id(db, payload.expense_type),
    )
    if payload.request_type == 'MULTI_QUOTE':
        expense.status = ExpenseStatus.QUOTATION_VOTING
    if source:
        expire_open_approvals(db, source, actor_email=user.email)
        if source.status in (
            ExpenseStatus.SUBMITTED,
            ExpenseStatus.PENDING_APPROVAL,
            ExpenseStatus.APPROVED,
        ):
            source.status = ExpenseStatus.CANCELLED
            source.cancelled_at = datetime.utcnow()
            source.cancelled_by = user.email
            source.cancellation_reason = 'Flujo reemplazado por una solicitud corregida'
    db.add(expense)
    db.flush()
    if payload.request_type == 'MULTI_QUOTE':
        db.add_all([
            QuotationOption(
                expense_id=expense.id,
                option_number=index,
                supplier=option.supplier,
                amount=option.amount,
                item_url=str(option.item_url) if option.item_url else None,
                notes=option.notes,
            )
            for index, option in enumerate(quote_values, 1)
        ])
    db.commit()
    db.refresh(expense)

    if payload.request_type == 'MULTI_QUOTE':
        voters = list(db.scalars(select(User).where(
            User.active.is_(True),
            User.can_approve.is_(True),
            User.role != UserRole.ADMIN,
        )).all())
        for voter in voters:
            invitation = QuotationVotingInvitation(expense_id=expense.id, voter_user_id=voter.id)
            db.add(invitation)
            db.flush()
            try:
                send_quotation_vote_request(expense, voter, invitation)
            except Exception:
                logger.exception('Quotation voting email delivery failed; request was still saved')
        db.commit()

    if payload.request_type == 'SIMPLE' and not quotation_pending:
        try:
            start_approval_flow(db, expense)
        except ValueError as exc:
            db.delete(expense)
            db.commit()
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    stmt = select(Expense).where(Expense.id == expense.id).options(
        selectinload(Expense.approvals),
        selectinload(Expense.attachments),
        selectinload(Expense.quotation_options),
        selectinload(Expense.quotation_votes),
    )
    return db.scalars(stmt).one()


class QuotationVoteRequest(BaseModel):
    quotation_option_id: int


@router.get('/quotation-vote-email/{token}')
def get_email_quotation_vote(token: str, db: Session = Depends(get_db)):
    invitation = db.scalar(select(QuotationVotingInvitation).where(
        QuotationVotingInvitation.token == token,
    ))
    if not invitation:
        raise HTTPException(status_code=404, detail='Invitación de votación no encontrada')
    expense = db.scalar(select(Expense).where(
        Expense.id == invitation.expense_id,
    ).options(
        selectinload(Expense.quotation_options),
        selectinload(Expense.quotation_votes),
        selectinload(Expense.attachments),
    ))
    if expense.status != ExpenseStatus.QUOTATION_VOTING:
        raise HTTPException(status_code=410, detail='La votación ya no está abierta')
    current = next((
        vote.quotation_option_id for vote in expense.quotation_votes
        if vote.voter_user_id == invitation.voter_user_id
    ), None)
    return {
        'kind': 'QUOTATION_VOTE',
        'token': token,
        'current_option_id': current,
        'expense': {
            'display_id': expense.display_id,
            'title': expense.title,
            'description': expense.description,
            'urgency': expense.urgency,
            'options': [{
                'id': option.id,
                'option_number': option.option_number,
                'supplier': option.supplier,
                'amount': str(option.amount),
                'item_url': option.item_url,
                'notes': option.notes,
                'attachments': [{
                    'id': item.id,
                    'original_name': item.original_name,
                } for item in expense.attachments if item.quotation_option_id == option.id],
            } for option in expense.quotation_options],
        },
    }


@router.get('/quotation-vote-email/{token}/attachments/{attachment_id}')
def view_email_quotation_attachment(token: str, attachment_id: int, db: Session = Depends(get_db)):
    invitation = db.scalar(select(QuotationVotingInvitation).where(
        QuotationVotingInvitation.token == token,
    ))
    if not invitation:
        raise HTTPException(status_code=404, detail='Invitación de votación no encontrada')
    expense = db.get(Expense, invitation.expense_id)
    if expense.status != ExpenseStatus.QUOTATION_VOTING:
        raise HTTPException(status_code=410, detail='La votación ya no está abierta')
    attachment = db.scalar(select(ExpenseAttachment).where(
        ExpenseAttachment.id == attachment_id,
        ExpenseAttachment.expense_id == expense.id,
        ExpenseAttachment.quotation_option_id.is_not(None),
    ))
    if not attachment:
        raise HTTPException(status_code=404, detail='Cotización no encontrada')
    path = UPLOAD_DIR / attachment.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail='El archivo ya no está disponible')
    return FileResponse(
        path,
        media_type=attachment.content_type,
        filename=attachment.original_name,
        content_disposition_type='inline',
    )


@router.post('/quotation-vote-email/{token}')
def decide_email_quotation_vote(
    token: str,
    payload: QuotationVoteRequest,
    db: Session = Depends(get_db),
):
    invitation = db.scalar(select(QuotationVotingInvitation).where(
        QuotationVotingInvitation.token == token,
    ))
    if not invitation:
        raise HTTPException(status_code=404, detail='Invitación de votación no encontrada')
    user = db.get(User, invitation.voter_user_id)
    if not user or not user.active or not user.can_approve:
        raise HTTPException(status_code=403, detail='El usuario delegado para votar ya no está habilitado')
    target = db.get(Expense, invitation.expense_id)
    expense = vote_quotation(target.request_id, payload, db, user)
    return {
        'status': expense.status.value,
        'display_id': expense.display_id,
        'quotation_option_id': payload.quotation_option_id,
    }


@router.post('/{request_id}/quotation-vote', response_model=ExpenseOut)
def vote_quotation(
    request_id: str,
    payload: QuotationVoteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_approve')),
):
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail='El Administrador del sistema no participa en votaciones operativas')
    expense = db.scalar(select(Expense).where(or_(
        Expense.request_id == request_id,
        Expense.display_id == request_id,
    )).options(
        selectinload(Expense.quotation_options),
        selectinload(Expense.quotation_votes),
        selectinload(Expense.approvals),
        selectinload(Expense.attachments),
    ))
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    if expense.status != ExpenseStatus.QUOTATION_VOTING:
        raise HTTPException(status_code=409, detail='La votación de cotizaciones ya no está abierta')
    supported_option_ids = set(db.scalars(select(
        ExpenseAttachment.quotation_option_id,
    ).where(
        ExpenseAttachment.expense_id == expense.id,
        ExpenseAttachment.quotation_option_id.is_not(None),
    )).all())
    unsupported = [
        item.option_number for item in expense.quotation_options
        if not item.item_url and item.id not in supported_option_ids
    ]
    if unsupported:
        raise HTTPException(
            status_code=409,
            detail=f'Falta soporte en las opciones: {", ".join(map(str, unsupported))}',
        )
    option = next((
        item for item in expense.quotation_options
        if item.id == payload.quotation_option_id
    ), None)
    if not option:
        raise HTTPException(status_code=422, detail='La cotización no pertenece a esta solicitud')
    vote = next((
        item for item in expense.quotation_votes if item.voter_user_id == user.id
    ), None)
    previous = vote.quotation_option_id if vote else None
    if vote:
        vote.quotation_option_id = option.id
    else:
        vote = QuotationVote(
            expense_id=expense.id,
            quotation_option_id=option.id,
            voter_user_id=user.id,
            voter_email=user.email,
            voter_role=user.title,
        )
        db.add(vote)
    db.add(QuotationVoteEvent(
        expense_id=expense.id,
        flow_id=expense.flow_id,
        voter_user_id=user.id,
        voter_email=user.email,
        voter_role=user.title,
        previous_option_id=previous,
        selected_option_id=option.id,
    ))
    db.commit()
    eligible_count = db.scalar(select(func.count(User.id)).where(
        User.active.is_(True),
        User.can_approve.is_(True),
        User.role != UserRole.ADMIN,
    )) or 0
    votes = list(db.scalars(select(QuotationVote).where(
        QuotationVote.expense_id == expense.id,
    )).all())
    if eligible_count and len(votes) >= eligible_count:
        counts = {}
        for item in votes:
            counts[item.quotation_option_id] = counts.get(item.quotation_option_id, 0) + 1
        highest = max(counts.values())
        winners = [option_id for option_id, count in counts.items() if count == highest]
        if len(winners) == 1:
            winner = db.get(QuotationOption, winners[0])
            expense.selected_quotation_id = winner.id
            expense.supplier = winner.supplier
            expense.amount = winner.amount
            expense.item_url = winner.item_url
            expense.status = ExpenseStatus.APPROVED
            db.commit()
            db.refresh(expense)
    stmt = select(Expense).where(Expense.id == expense.id).options(
        selectinload(Expense.approvals),
        selectinload(Expense.attachments),
        selectinload(Expense.quotation_options),
        selectinload(Expense.quotation_votes),
    )
    return db.scalars(stmt).one()


@router.put('/{request_id}/resubmit', response_model=ExpenseOut)
def resubmit_expense(
    request_id: str,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_request')),
):
    _validate_area_selection(db, payload.expense_type, payload.expense_subcategory)
    expense = _expense_for_user(db, request_id, user)
    db.scalar(select(Expense).where(Expense.id == expense.id).with_for_update())
    db.refresh(expense)
    if expense.status == ExpenseStatus.CLOSED:
        raise HTTPException(status_code=409, detail='Una solicitud cerrada no puede corregirse')

    expire_open_approvals(db, expense, actor_email=user.email)
    values = payload.model_dump(mode='json', exclude={'quotation_pending', 'revised_from_request_id'})
    for field, value in values.items():
        setattr(expense, field, value)
    expense.flow_id = str(uuid.uuid4())
    expense.status = ExpenseStatus.SUBMITTED
    expense.cancelled_at = None
    expense.cancelled_by = None
    expense.cancellation_reason = None
    db.commit()
    db.refresh(expense)

    if not payload.quotation_pending:
        try:
            start_approval_flow(db, expense)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    stmt = select(Expense).where(Expense.id == expense.id).options(
        selectinload(Expense.approvals),
        selectinload(Expense.attachments),
    )
    return db.scalars(stmt).one()


def _expense_for_user(db: Session, request_id: str, user: User) -> Expense:
    expense = db.scalar(select(Expense).where(or_(
        Expense.request_id == request_id,
        Expense.display_id == request_id,
    )))
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    if user.role == UserRole.REQUESTER and expense.requested_by != user.email:
        raise HTTPException(status_code=403, detail='No tienes acceso a esta solicitud')
    return expense


@router.post('/{request_id}/attachments', response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    request_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_request')),
):
    expense = _expense_for_user(db, request_id, user)
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail='Solo se permiten archivos PDF, JPG, PNG o WEBP')
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='El archivo supera el límite de 10 MB')
    suffix = _validate_file_content(content, file.content_type)
    safe_original = Path(file.filename or 'cotizacion').name[:255]
    stored_name = f'{secrets.token_hex(20)}{suffix}'
    _ensure_storage_capacity(len(content))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / stored_name).write_bytes(content)
    attachment = ExpenseAttachment(
        expense_id=expense.id,
        original_name=safe_original,
        stored_name=stored_name,
        content_type=file.content_type,
        size=len(content),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    if not any(approval.flow_id == expense.flow_id for approval in expense.approvals):
        try:
            start_approval_flow(db, expense)
        except ValueError as exc:
            db.delete(attachment)
            db.commit()
            path = UPLOAD_DIR / stored_name
            if path.exists():
                path.unlink()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return attachment


@router.post('/{request_id}/quotation-options/{option_id}/attachment', response_model=AttachmentOut, status_code=201)
async def upload_quotation_option_attachment(
    request_id: str,
    option_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission('can_request')),
):
    expense = _expense_for_user(db, request_id, user)
    if expense.request_type != 'MULTI_QUOTE':
        raise HTTPException(status_code=409, detail='Esta solicitud no utiliza múltiples cotizaciones')
    option = db.scalar(select(QuotationOption).where(
        QuotationOption.id == option_id,
        QuotationOption.expense_id == expense.id,
    ))
    if not option:
        raise HTTPException(status_code=404, detail='Cotización no encontrada')
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail='Solo se permiten archivos PDF, JPG, PNG o WEBP')
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='El archivo supera el límite de 10 MB')
    suffix = _validate_file_content(content, file.content_type)
    safe_original = Path(file.filename or f'cotizacion-{option.option_number}').name[:255]
    duplicate_name = db.scalar(select(ExpenseAttachment.id).where(
        ExpenseAttachment.expense_id == expense.id,
        ExpenseAttachment.quotation_option_id.is_not(None),
        func.lower(ExpenseAttachment.original_name) == safe_original.lower(),
    ))
    if duplicate_name:
        raise HTTPException(status_code=409, detail='Cada cotización debe usar un archivo con nombre diferente')
    stored_name = f'{secrets.token_hex(20)}{suffix}'
    _ensure_storage_capacity(len(content))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / stored_name).write_bytes(content)
    attachment = ExpenseAttachment(
        expense_id=expense.id,
        quotation_option_id=option.id,
        original_name=safe_original,
        stored_name=stored_name,
        content_type=file.content_type,
        size=len(content),
        document_type='QUOTATION_OPTION',
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get('/attachments/{attachment_id}')
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    attachment = db.scalar(select(ExpenseAttachment).where(
        ExpenseAttachment.id == attachment_id,
    ).options(selectinload(ExpenseAttachment.expense)))
    if not attachment:
        raise HTTPException(status_code=404, detail='Archivo no encontrado')
    if user.role == UserRole.REQUESTER and attachment.expense.requested_by != user.email:
        raise HTTPException(status_code=403, detail='No tienes acceso a este archivo')
    path = UPLOAD_DIR / attachment.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail='El archivo ya no está disponible')
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.post('/{request_id}/cancel', response_model=ExpenseOut)
def cancel_expense(
    request_id: str,
    payload: CancellationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    expense = _expense_for_user(db, request_id, user)
    db.scalar(select(Expense).where(Expense.id == expense.id).with_for_update())
    db.refresh(expense)
    if user.role != UserRole.ADMIN and not user.can_request:
        raise HTTPException(status_code=403, detail='No tienes permiso para cancelar solicitudes')
    if expense.status == ExpenseStatus.CLOSED:
        raise HTTPException(status_code=409, detail='Una solicitud cerrada no puede cancelarse')
    if expense.status == ExpenseStatus.CANCELLED:
        raise HTTPException(status_code=409, detail='La solicitud ya está cancelada')
    if expense.status == ExpenseStatus.REJECTED:
        raise HTTPException(status_code=409, detail='Una solicitud rechazada debe corregirse y reenviarse, no cancelarse')
    expense.status = ExpenseStatus.CANCELLED
    expire_open_approvals(db, expense, actor_email=user.email)
    expense.cancelled_at = datetime.utcnow()
    expense.cancelled_by = user.email
    expense.cancellation_reason = payload.reason.strip()
    db.commit()
    stmt = select(Expense).where(Expense.id == expense.id).options(
        selectinload(Expense.approvals),
        selectinload(Expense.attachments),
    )
    return db.scalars(stmt).one()


@router.post('/{request_id}/close', response_model=ExpenseOut)
async def close_expense(
    request_id: str,
    invoice: UploadFile = File(...),
    notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    expense = db.scalar(select(Expense).where(or_(
        Expense.request_id == request_id,
        Expense.display_id == request_id,
    )).with_for_update())
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    db.refresh(expense)
    if expense.status != ExpenseStatus.APPROVED:
        raise HTTPException(status_code=409, detail='Solo se pueden cerrar solicitudes aprobadas')
    documents = [('INVOICE', invoice)]
    prepared = []
    for document_type, upload in documents:
        if upload.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail='La factura debe ser un archivo PDF, JPG, PNG o WEBP')
        content = await upload.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail='Cada archivo debe pesar máximo 10 MB')
        suffix = _validate_file_content(content, upload.content_type)
        original = Path(upload.filename or document_type.lower()).name[:255]
        stored = f'{secrets.token_hex(20)}{suffix}'
        prepared.append((document_type, upload.content_type, original, stored, content))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_storage_capacity(sum(len(item[4]) for item in prepared))
    written = []
    try:
        for document_type, content_type, original, stored, content in prepared:
            path = UPLOAD_DIR / stored
            path.write_bytes(content)
            written.append(path)
            db.add(ExpenseAttachment(
                expense_id=expense.id,
                original_name=original,
                stored_name=stored,
                content_type=content_type,
                size=len(content),
                document_type=document_type,
            ))
        expense.status = ExpenseStatus.CLOSED
        expense.closed_at = datetime.utcnow()
        expense.closed_by = user.email
        expense.closure_notes = notes.strip() if notes else None
        db.commit()
    except Exception:
        db.rollback()
        for path in written:
            if path.exists():
                path.unlink()
        raise
    stmt = select(Expense).where(Expense.id == expense.id).options(
        selectinload(Expense.approvals),
        selectinload(Expense.attachments),
    )
    return db.scalars(stmt).one()


@router.put('/{request_id}/invoice', response_model=ExpenseOut)
async def replace_invoice(
    request_id: str,
    invoice: UploadFile = File(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if len(reason.strip()) < 3:
        raise HTTPException(status_code=422, detail='Debes indicar el motivo de la corrección')
    expense = db.scalar(select(Expense).where(or_(
        Expense.request_id == request_id,
        Expense.display_id == request_id,
    )).with_for_update())
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    if expense.status != ExpenseStatus.CLOSED:
        raise HTTPException(status_code=409, detail='Solo se puede corregir la factura de una solicitud cerrada')
    previous = db.scalar(select(ExpenseAttachment).where(
        ExpenseAttachment.expense_id == expense.id,
        ExpenseAttachment.document_type == 'INVOICE',
    ).order_by(ExpenseAttachment.id.desc()))
    if not previous:
        raise HTTPException(status_code=409, detail='La solicitud no tiene una factura vigente para reemplazar')
    if invoice.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail='La factura debe ser un archivo PDF, JPG, PNG o WEBP')
    content = await invoice.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='La factura debe pesar máximo 10 MB')
    suffix = _validate_file_content(content, invoice.content_type)
    original = Path(invoice.filename or 'factura').name[:255]
    stored = f'{secrets.token_hex(20)}{suffix}'
    _ensure_storage_capacity(len(content))
    path = UPLOAD_DIR / stored
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        previous.document_type = 'INVOICE_REPLACED'
        replacement = ExpenseAttachment(
            expense_id=expense.id,
            original_name=original,
            stored_name=stored,
            content_type=invoice.content_type,
            size=len(content),
            document_type='INVOICE',
        )
        db.add(replacement)
        db.flush()
        db.add(InvoiceChangeEvent(
            expense_id=expense.id,
            previous_attachment_id=previous.id,
            new_attachment_id=replacement.id,
            actor_email=user.email,
            reason=reason.strip(),
        ))
        db.commit()
    except Exception:
        db.rollback()
        if path.exists():
            path.unlink()
        raise
    stmt = select(Expense).where(Expense.id == expense.id).options(
        selectinload(Expense.approvals),
        selectinload(Expense.attachments),
    )
    return db.scalars(stmt).one()
