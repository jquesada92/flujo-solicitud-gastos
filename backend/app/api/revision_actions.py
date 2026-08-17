import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import require_permission
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
from app.services.approval_engine import expire_open_approvals, start_approval_flow
from app.services.email_service import send_quotation_vote_request
from app.services.iam_service import users_with_permission

router = APIRouter()
logger = logging.getLogger(__name__)


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

    voters = users_with_permission(
        db,
        'requests:approve',
        exclude_email=actor.email.lower(),
    )
    if not voters:
        raise HTTPException(
            status_code=422,
            detail='No existe otro usuario activo con permiso de aprobación para participar en la votación',
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
    user: User = Depends(require_permission('requests:create')),
):
    """Correct and restart a request without changing its workflow type.

    A MULTI_QUOTE correction remains MULTI_QUOTE and restarts its voting round.
    A SIMPLE correction remains SIMPLE. The canonical type is also inferred from
    durable quotation evidence for legacy rows with an incorrect SIMPLE default.
    """
    _validate_classification(db, payload.expense_type, payload.expense_subcategory)
    expense = _load_expense(db, request_id)
    db.scalar(select(Expense.id).where(Expense.id == expense.id).with_for_update())
    db.refresh(expense)

    if expense.status == ExpenseStatus.CLOSED:
        raise HTTPException(status_code=409, detail='Una solicitud cerrada no puede corregirse')

    stored_type = _canonical_request_type(expense)
    if payload.request_type != stored_type:
        raise HTTPException(
            status_code=409,
            detail='Una corrección no puede cambiar el tipo original de la solicitud',
        )
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

    db.commit()

    if stored_type == 'MULTI_QUOTE':
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
            start_approval_flow(db, expense)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _present(db, expense.id)
