import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import current_user
from app.models.entities import (
    Expense,
    ExpenseArea,
    ExpenseAttachment,
    ExpenseStatus,
    ExpenseSubcategory,
    QuotationOption,
    QuotationVote,
    QuotationVotingInvitation,
    User,
)
from app.schemas.expense import ExpenseCreate, ExpenseOut
from app.services.approval_engine import (
    expire_open_approvals,
    notify_approval_flow_started,
    start_approval_flow,
)
from app.services.approval_policy_service import (
    DIRECT_EXPENSE_REQUIRED_DETAIL,
    find_applicable_policy,
    is_no_approval_policy,
    participants_for_policy,
    snapshot_policy_resolution,
)
from app.services.email_service import send_quotation_vote_request
from app.services.iam_service import is_system_account

router = APIRouter()
logger = logging.getLogger(__name__)

CORRECTABLE_STATUSES = {
    ExpenseStatus.QUOTATION_VOTING,
    ExpenseStatus.SUBMITTED,
    ExpenseStatus.PENDING_APPROVAL,
    ExpenseStatus.NEEDS_REVISION,
    ExpenseStatus.APPROVED,
    ExpenseStatus.REJECTED,
}


def can_correct_expense(
    db: Session,
    expense: Expense,
    user: User,
    *,
    system_admin: bool | None = None,
) -> bool:
    """Correction is resource ownership, not a general requests:create capability.

    Only the original requester or the protected system administrator can edit
    and resubmit a request. Approvers/reviewers must use REVISION_REQUESTED with
    a comment instead of modifying somebody else's request.
    """
    if expense.status not in CORRECTABLE_STATUSES:
        return False
    requester = (expense.requested_by or '').strip().lower()
    actor = (user.email or '').strip().lower()
    technical_admin = is_system_account(db, user.id) if system_admin is None else system_admin
    return requester == actor or technical_admin


def _validate_classification(db: Session, area_code: str, category_code: str | None) -> None:
    area = db.scalar(
        select(ExpenseArea).where(
            ExpenseArea.code == area_code,
            ExpenseArea.active.is_(True),
        )
    )
    if not area:
        raise HTTPException(status_code=422, detail='El área seleccionada no existe o está inactiva')
    if not category_code:
        raise HTTPException(status_code=422, detail='Debes seleccionar una categoría')
    category = db.scalar(
        select(ExpenseSubcategory).where(
            ExpenseSubcategory.area_id == area.id,
            ExpenseSubcategory.code == category_code,
            ExpenseSubcategory.active.is_(True),
        )
    )
    if not category:
        raise HTTPException(
            status_code=422,
            detail='La categoría no está habilitada para el área seleccionada o está inactiva',
        )


def _load_expense(db: Session, request_id: str) -> Expense:
    expense = db.scalar(
        select(Expense)
        .where(or_(Expense.request_id == request_id, Expense.display_id == request_id))
        .options(
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
        )
    )
    if not expense:
        raise HTTPException(status_code=404, detail='Solicitud no encontrada')
    return expense


def _canonical_request_type(expense: Expense) -> str:
    """Derive the workflow type from durable business evidence.

    Legacy rows may still carry the historical SIMPLE default even though they
    have multiple quotation options or are/were in quotation voting. Corrections
    must follow the request itself, never whichever frontend tab was selected.
    """
    if expense.request_type == 'MULTI_QUOTE':
        return 'MULTI_QUOTE'
    if expense.status == ExpenseStatus.QUOTATION_VOTING:
        return 'MULTI_QUOTE'
    if len(expense.quotation_options or []) >= 2:
        return 'MULTI_QUOTE'
    return 'SIMPLE'


def _present(db: Session, expense_id: int) -> Expense:
    return db.scalars(
        select(Expense)
        .where(Expense.id == expense_id)
        .options(
            selectinload(Expense.approvals),
            selectinload(Expense.attachments),
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
        )
    ).one()


def _apply_common_fields(expense: Expense, payload: ExpenseCreate) -> None:
    expense.title = payload.title
    expense.description = payload.description
    expense.expense_type = payload.expense_type
    expense.expense_subcategory = payload.expense_subcategory
    expense.urgency = payload.urgency
    expense.cancelled_at = None
    expense.cancelled_by = None
    expense.cancellation_reason = None
    expense.closed_at = None
    expense.closed_by = None
    expense.closure_notes = None
    expense.flow_id = str(uuid.uuid4())
    expense.approval_policy_id = None
    expense.approval_policy_mode = None
    expense.policy_evaluation_amount = None
    expense.minimum_votes_required = None


def _reset_multi_quote_round(
    db: Session,
    expense: Expense,
    payload: ExpenseCreate,
    actor: User,
) -> list[tuple[User, QuotationVotingInvitation]]:
    existing_options = sorted(expense.quotation_options, key=lambda item: item.option_number)
    if len(payload.quotation_options) != len(existing_options):
        raise HTTPException(
            status_code=409,
            detail=(
                'La corrección de múltiples cotizaciones debe conservar la cantidad de opciones existente. '
                'Puedes editar proveedor, monto, URL y observaciones de cada opción.'
            ),
        )

    for option, incoming in zip(existing_options, payload.quotation_options, strict=True):
        option.supplier = incoming.supplier
        option.amount = incoming.amount
        option.item_url = str(incoming.item_url) if incoming.item_url else None
        option.notes = incoming.notes

    db.execute(delete(QuotationVote).where(QuotationVote.expense_id == expense.id))
    db.execute(
        delete(QuotationVotingInvitation).where(
            QuotationVotingInvitation.expense_id == expense.id,
        )
    )

    expense.request_type = 'MULTI_QUOTE'
    expense.amount = None
    expense.supplier = None
    expense.item_url = None
    expense.selected_quotation_id = None
    expense.status = ExpenseStatus.QUOTATION_VOTING

    evaluation_amount = max(option.amount for option in payload.quotation_options)
    try:
        policy = find_applicable_policy(db, expense.expense_type, evaluation_amount)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if policy is not None and is_no_approval_policy(policy):
        raise HTTPException(status_code=422, detail=DIRECT_EXPENSE_REQUIRED_DETAIL)
    voters = participants_for_policy(
        db,
        policy,
        exclude_email=expense.requested_by.lower(),
    )
    if not voters:
        raise HTTPException(
            status_code=422,
            detail='No existe otro usuario activo con permiso de aprobación para participar en la votación',
        )
    snapshot_policy_resolution(
        expense,
        policy,
        evaluation_amount,
        len(voters),
        default_mode='ALL',
    )

    invitations: list[tuple[User, QuotationVotingInvitation]] = []
    for voter in voters:
        invitation = QuotationVotingInvitation(
            expense_id=expense.id,
            voter_user_id=voter.id,
        )
        db.add(invitation)
        db.flush()
        invitations.append((voter, invitation))
    return invitations


@router.put('/{request_id}/resubmit', response_model=ExpenseOut)
def resubmit_expense(
    request_id: str,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Correct and restart a request without changing its workflow type.

    Only the original requester or the protected system administrator can
    correct/resubmit. Reviewers must request revision with comments instead.
    A MULTI_QUOTE correction remains MULTI_QUOTE and restarts its voting round.
    A SIMPLE correction remains SIMPLE. The canonical type is also inferred from
    durable quotation evidence for legacy rows with an incorrect SIMPLE default.
    """
    _validate_classification(db, payload.expense_type, payload.expense_subcategory)
    expense = _load_expense(db, request_id)
    db.scalar(select(Expense.id).where(Expense.id == expense.id).with_for_update())
    db.refresh(expense)

    if not can_correct_expense(db, expense, user):
        if expense.status == ExpenseStatus.CLOSED:
            raise HTTPException(status_code=409, detail='Una solicitud cerrada no puede corregirse')
        if expense.status == ExpenseStatus.CANCELLED:
            raise HTTPException(status_code=409, detail='Una solicitud cancelada no puede corregirse')
        raise HTTPException(
            status_code=403,
            detail=(
                'Solo el solicitante original o el Administrador del sistema pueden corregir y reenviar. '
                'Los aprobadores deben usar Enviar a revisión e indicar sus comentarios.'
            ),
        )

    stored_type = _canonical_request_type(expense)
    if payload.request_type != stored_type:
        raise HTTPException(
            status_code=409,
            detail='Una corrección no puede cambiar el tipo original de la solicitud',
        )

    evaluation_amount = (
        max(option.amount for option in payload.quotation_options)
        if stored_type == 'MULTI_QUOTE'
        else payload.amount
    )
    try:
        applicable_policy = find_applicable_policy(
            db,
            payload.expense_type,
            evaluation_amount,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if applicable_policy is not None and is_no_approval_policy(applicable_policy):
        raise HTTPException(status_code=422, detail=DIRECT_EXPENSE_REQUIRED_DETAIL)

    # Repair an inconsistent legacy row even before the Alembic backfill has run.
    expense.request_type = stored_type

    expire_open_approvals(db, expense, actor_email=user.email)
    _apply_common_fields(expense, payload)

    invitations: list[tuple[User, QuotationVotingInvitation]] = []
    if stored_type == 'MULTI_QUOTE':
        invitations = _reset_multi_quote_round(db, expense, payload, user)
    else:
        expense.request_type = 'SIMPLE'
        expense.amount = payload.amount
        expense.supplier = payload.supplier
        expense.item_url = str(payload.item_url) if payload.item_url else None
        expense.selected_quotation_id = None
        expense.status = ExpenseStatus.SUBMITTED

    if stored_type == 'MULTI_QUOTE':
        db.commit()
        refreshed = _present(db, expense.id)
        for voter, invitation in invitations:
            try:
                send_quotation_vote_request(refreshed, voter, invitation)
            except Exception:
                logger.exception('Quotation voting email delivery failed; corrected request remains saved')
        return refreshed

    has_existing_support = db.scalar(
        select(ExpenseAttachment.id).where(
            ExpenseAttachment.expense_id == expense.id,
            ExpenseAttachment.quotation_option_id.is_(None),
            ExpenseAttachment.document_type != 'INVOICE',
        ).limit(1)
    ) is not None
    if expense.item_url or has_existing_support:
        try:
            approvals = start_approval_flow(db, expense, commit=False)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        db.commit()
        notify_approval_flow_started(approvals)
    else:
        db.commit()

    return _present(db, expense.id)
