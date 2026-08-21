"""Persistent live workflow demonstration with 30 seconds between actions."""
import time
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.expenses import UPLOAD_DIR, _next_display_id
from app.core.database import SessionLocal
from app.demo_monitoring import DEMO_PASSWORD, dummy_pdf, ensure_user
from app.models.entities import (
    Approval, ApprovalPolicy, ApprovalStatus, Expense, ExpenseAttachment,
    ExpenseStatus, User, UserRole,
)
from app.services.approval_engine import apply_decision, expire_open_approvals, record_step_event, start_approval_flow

INTERVAL_SECONDS = 30
PRODUCTS = {
    'ADMINISTRATION': ('SUPPLIES', 'Papel Amazon Basics', Decimal('54.99'), 'https://www.amazon.com/dp/B01FV0F13E'),
    'MAINTENANCE': ('EQUIPMENT', 'Taladro DEWALT', Decimal('249.00'), 'https://www.amazon.com/dp/B07DXNXMTK'),
    'POOL': ('SUPPLIES', 'Kit de mantenimiento de piscina', Decimal('92.50'), 'https://www.amazon.com/s?k=pool+maintenance+supplies'),
    'LEGAL': ('PROCEDURES', 'Material de archivo legal', Decimal('35.00'), 'https://www.amazon.com/s?k=legal+file+folders'),
}


def announce(message):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {message}', flush=True)


def wait_next():
    announce(f'Esperando {INTERVAL_SECONDS} segundos para la siguiente acción...')
    time.sleep(INTERVAL_SECONDS)


def create_expense(db, run_id, category, scenario):
    subcategory, product, amount, url = PRODUCTS[category]
    requester = db.scalar(select(User).where(User.email == 'solicitante.prueba@example.com'))
    expense = Expense(title=f'[PRUEBA EN VIVO {run_id}] {scenario}',
        description=f'Producto de referencia: {product}. Escenario persistente para monitoreo en vivo.',
        expense_type=category, expense_subcategory=subcategory, amount=amount, supplier='Amazon',
        item_url=url, requested_by=requester.email, requester_analytics_id=requester.analytics_id,
        display_id=_next_display_id(db, category))
    db.add(expense); db.commit(); db.refresh(expense); start_approval_flow(db, expense)
    announce(f'{expense.display_id} creada: {scenario} (PENDIENTE)')
    return expense.id


def pending_approval(db, expense_id):
    expense = db.scalar(select(Expense).where(Expense.id == expense_id).options(selectinload(Expense.approvals)))
    return expense, next(item for item in expense.approvals if item.status == ApprovalStatus.PENDING)


def main():
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S')
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id))
        ensure_user(db, 'TEST-REQUESTER-002', 'Solicitante Prueba', 'solicitante.prueba@example.com', 'PROPIETARIO', True, False)
        treasurer = ensure_user(db, 'TEST-TREASURER-002', 'Tesorero Prueba', 'tesorero.prueba@example.com', 'TESORERO', True, True)
        if not db.scalar(select(ApprovalPolicy).where(ApprovalPolicy.name == '[PRUEBA] Aprobación por tesorero')):
            raise RuntimeError('Ejecuta primero python -m app.demo_monitoring para crear la regla demo')

        approved_id = create_expense(db, run_id, 'ADMINISTRATION', 'Aprobar y cerrar con factura')
        wait_next(); expense, approval = pending_approval(db, approved_id)
        apply_decision(db, approval, ApprovalStatus.APPROVED, 'Aprobada durante demostración en vivo', treasurer.email)
        announce(f'{expense.display_id}: APROBADA')
        wait_next(); expense = db.get(Expense, approved_id)
        content = dummy_pdf(expense.title, expense.amount); UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored = f'live-{expense.request_id}.pdf'; (UPLOAD_DIR / stored).write_bytes(content)
        db.add(ExpenseAttachment(expense_id=expense.id, original_name=f'factura-prueba-{expense.display_id}.pdf',
            stored_name=stored, content_type='application/pdf', size=len(content), document_type='INVOICE'))
        expense.status = ExpenseStatus.CLOSED; expense.closed_at = datetime.utcnow(); expense.closed_by = admin.email
        expense.closure_notes = 'PRUEBA EN VIVO - SIN VALOR FISCAL'
        approval = db.scalar(select(Approval).where(Approval.expense_id == expense.id))
        record_step_event(db, approval, 'EXPENSE_CLOSED', approval.status, actor_email=admin.email,
                          comment='Factura dummy registrada'); db.commit()
        announce(f'{expense.display_id}: CERRADA con factura dummy')

        wait_next(); rejected_id = create_expense(db, run_id, 'MAINTENANCE', 'Flujo rechazado')
        wait_next(); expense, approval = pending_approval(db, rejected_id)
        apply_decision(db, approval, ApprovalStatus.REJECTED, 'Rechazo controlado de prueba', treasurer.email)
        announce(f'{expense.display_id}: RECHAZADA')

        wait_next(); revision_id = create_expense(db, run_id, 'POOL', 'Solicitud de corrección')
        wait_next(); expense, approval = pending_approval(db, revision_id)
        apply_decision(db, approval, ApprovalStatus.REVISION_REQUESTED, 'Corregir cantidad y descripción del producto', treasurer.email)
        announce(f'{expense.display_id}: REQUIERE REVISIÓN')

        wait_next(); pending_id = create_expense(db, run_id, 'LEGAL', 'Dejar pendiente para aprobación manual')
        wait_next(); cancelled_id = create_expense(db, run_id, 'ADMINISTRATION', 'Cancelar solicitud')
        wait_next(); expense, _ = pending_approval(db, cancelled_id)
        expense.status = ExpenseStatus.CANCELLED; expense.cancelled_at = datetime.utcnow()
        expense.cancelled_by = 'solicitante.prueba@example.com'; expense.cancellation_reason = 'Cancelación controlada de prueba'
        expire_open_approvals(db, expense, actor_email=expense.cancelled_by); db.commit()
        announce(f'{expense.display_id}: CANCELADA')
        announce(f'Demostración {run_id} terminada. Todos los datos permanecen guardados.')


if __name__ == '__main__': main()
