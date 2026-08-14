"""Create persistent local demo workflows for visual monitoring.

Run explicitly with: python -m app.demo_monitoring
The script is idempotent and never deletes existing records.
"""
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.expenses import UPLOAD_DIR, _next_display_id
from app.core.database import SessionLocal
from app.core.privacy import analytics_identifier, mask_email
from app.core.security import hash_password
from app.models.entities import (
    Approval, ApprovalPolicy, ApprovalPolicyChangeEvent, ApprovalStatus,
    Expense, ExpenseAttachment, ExpenseStatus, PersonType, User,
    UserChangeEvent, UserRole,
)
from app.services.approval_engine import apply_decision, start_approval_flow

DEMO_PASSWORD = 'Demo12345!'
DEMO_USERS = (
    ('TEST-REQUESTER-001', 'Solicitante Prueba', 'solicitante.prueba@ph.local', 'PROPIETARIO', True, False),
    ('TEST-TREASURER-001', 'Tesorero Prueba', 'tesorero.prueba@ph.local', 'TESORERO', True, True),
)
DEMO_CASES = (
    ('[PRUEBA] Papel para administración', 'ADMINISTRATION', 'SUPPLIES', Decimal('49.99'),
     'Amazon', 'https://www.amazon.com/dp/B01FV0F13E', 'PENDING'),
    ('[PRUEBA] Taladro para mantenimiento', 'MAINTENANCE', 'EQUIPMENT', Decimal('249.00'),
     'Amazon', 'https://www.amazon.com/dp/B07DXNXMTK', 'APPROVED'),
    ('[PRUEBA] Suministros para piscina', 'POOL', 'SUPPLIES', Decimal('89.50'),
     'Amazon', 'https://www.amazon.com/s?k=pool+maintenance+supplies', 'CLOSED'),
)


def dummy_pdf(title: str, amount: Decimal) -> bytes:
    text = f'PRUEBA - SIN VALOR FISCAL | {title} | USD {amount}'
    stream = f'BT /F1 12 Tf 50 740 Td ({text}) Tj ET'.encode('latin-1', 'replace')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    pdf = bytearray(b'%PDF-1.4\n'); offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf)); pdf.extend(f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(pdf); pdf.extend(f'xref\n0 {len(objects)+1}\n'.encode()); pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]: pdf.extend(f'{offset:010d} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(pdf)


def ensure_user(db, identity, name, email, title, can_request, can_approve):
    user = db.scalar(select(User).where(User.email == email))
    if user: return user
    first, last = name.split(' ', 1)
    user = User(name=name, identity_document=identity, analytics_id=analytics_identifier(identity, email),
        first_name=first, last_name=last, phone='6000-0000', person_type=PersonType.OWNER,
        email=email, password_hash=hash_password(DEMO_PASSWORD),
        role=UserRole.APPROVER if can_approve else UserRole.REQUESTER, title=title,
        active=True, can_request=can_request, can_approve=can_approve, can_view=True,
        can_configure=False, must_change_password=False)
    db.add(user); db.flush()
    admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id))
    db.add(UserChangeEvent(event_type='USER_CREATED', user_id=user.id, user_email=mask_email(user.email),
        actor_user_id=admin.id, actor_email=mask_email(admin.email), changed_fields=['demo_fixture'],
        before_state=None, after_state={'name': name, 'title': title, 'active': True, 'demo': True}))
    db.commit(); db.refresh(user); return user


def main():
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id))
        if not admin: raise RuntimeError('No existe el administrador del sistema')
        users = {item[3]: ensure_user(db, *item) for item in DEMO_USERS}
        policy = db.scalar(select(ApprovalPolicy).where(ApprovalPolicy.name == '[PRUEBA] Aprobación por tesorero'))
        if not policy:
            policy = ApprovalPolicy(name='[PRUEBA] Aprobación por tesorero', expense_type='ALL',
                min_amount=Decimal('0.00'), max_amount=None, approval_mode='ANY',
                approver_profile_codes=['TESORERO'], active=True)
            db.add(policy); db.flush()
            state = {'name': policy.name, 'expense_type': 'ALL', 'min_amount': '0.00',
                     'max_amount': None, 'approval_mode': 'ANY',
                     'approver_profile_codes': ['TESORERO'], 'active': True}
            db.add(ApprovalPolicyChangeEvent(event_type='POLICY_CREATED', policy_id=policy.id,
                policy_name=policy.name, actor_user_id=admin.id, actor_email=mask_email(admin.email),
                changed_fields=list(state), before_state=None, after_state=state)); db.commit()

        for title, category, subcategory, amount, supplier, url, target in DEMO_CASES:
            if db.scalar(select(Expense).where(Expense.title == title)): continue
            expense = Expense(title=title, description='Escenario persistente para monitorear el flujo de aprobación.',
                expense_type=category, expense_subcategory=subcategory, amount=amount, supplier=supplier,
                item_url=url, requested_by=users['PROPIETARIO'].email,
                requester_analytics_id=users['PROPIETARIO'].analytics_id,
                display_id=_next_display_id(db, category))
            db.add(expense); db.commit(); db.refresh(expense); start_approval_flow(db, expense)
            if target in ('APPROVED', 'CLOSED'):
                expense = db.scalar(select(Expense).where(Expense.id == expense.id).options(selectinload(Expense.approvals)))
                approval = next(item for item in expense.approvals if item.status == ApprovalStatus.PENDING)
                apply_decision(db, approval, ApprovalStatus.APPROVED, 'Aprobación de escenario de prueba', users['TESORERO'].email)
            if target == 'CLOSED':
                content = dummy_pdf(title, amount); UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                filename = f'factura-prueba-{expense.display_id}.pdf'; stored = f'demo-{expense.request_id}.pdf'
                (UPLOAD_DIR / stored).write_bytes(content)
                db.add(ExpenseAttachment(expense_id=expense.id, original_name=filename, stored_name=stored,
                    content_type='application/pdf', size=len(content), document_type='INVOICE'))
                expense.status = ExpenseStatus.CLOSED; expense.closed_at = datetime.utcnow()
                expense.closed_by = admin.email; expense.closure_notes = 'Factura dummy: PRUEBA - SIN VALOR FISCAL'
                db.commit()
            print(f'{expense.display_id}: {title} -> {target}')
        print('Credenciales demo locales: solicitante.prueba@ph.local / Demo12345!')


if __name__ == '__main__': main()
