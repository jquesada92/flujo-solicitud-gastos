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
from app.core.audit_context import set_system_audit_actor
from app.core.privacy import analytics_identifier
from app.core.security import hash_password
from app.models.entities import (
    Approval, ApprovalPolicy, ApprovalStatus,
    Expense, ExpenseArea, ExpenseAttachment, ExpenseStatus, ExpenseSubcategory,
    QuotationOption, QuotationVotingInvitation, User, UserRole,
)
from app.models.iam import Permission, Role, RolePermission, UserRoleAssignment
import app.models.audit_capture  # noqa: F401  Register canonical audit capture hooks.
from app.services.approval_engine import apply_decision, start_approval_flow
from app.services.iam_service import users_with_permission
from app.services.quotation_service import cast_quotation_vote

DEMO_PASSWORD = 'Demo12345!'
DEMO_USERS = (
    ('TEST-REQUESTER-002', 'Solicitante Prueba', 'solicitante.prueba@example.com', 'PROPIETARIO', True, False),
    ('TEST-TREASURER-002', 'Tesorero Prueba', 'tesorero.prueba@example.com', 'TESORERO', True, True),
)
DEMO_CASES = (
    ('[PRUEBA] Papel para administración', 'ADMINISTRATION', 'SUPPLIES', Decimal('49.99'),
     'Amazon', 'https://www.amazon.com/dp/B01FV0F13E', 'PENDING'),
    ('[PRUEBA] Taladro para mantenimiento', 'MAINTENANCE', 'EQUIPMENT', Decimal('249.00'),
     'Amazon', 'https://www.amazon.com/dp/B07DXNXMTK', 'APPROVED'),
    ('[PRUEBA] Suministros para piscina', 'POOL', 'SUPPLIES', Decimal('89.50'),
     'Amazon', 'https://www.amazon.com/s?k=pool+maintenance+supplies', 'CLOSED'),
)
DEMO_MULTI_CASES = (
    ('[PRUEBA MULTIPLE] Equipos de oficina - votación abierta', False),
    ('[PRUEBA MULTIPLE] Servicio de mantenimiento - voto parcial', True),
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
    if not user:
        first, last = name.split(' ', 1)
        user = User(name=name, identity_document=identity, analytics_id=analytics_identifier(identity, email),
            first_name=first, last_name=last, phone='6000-0000',
            email=email, password_hash=hash_password(DEMO_PASSWORD),
            role=UserRole.APPROVER if can_approve else UserRole.REQUESTER, title=title,
            active=True, can_request=can_request, can_approve=can_approve, can_view=True,
            can_configure=False, must_change_password=False)
        db.add(user); db.flush()

    permission_codes = ['requests:read']
    if can_request: permission_codes.append('requests:create')
    if can_approve: permission_codes.append('requests:approve')
    role_code = 'demo-approver' if can_approve else 'demo-requester'
    role = db.scalar(select(Role).where(Role.code == role_code))
    if not role:
        role = Role(code=role_code, name=f'[PRUEBA] {"Aprobador" if can_approve else "Solicitante"}',
            active=True, system_managed=False)
        db.add(role); db.flush()
    existing_permission_ids = set(db.scalars(select(RolePermission.permission_id).where(
        RolePermission.role_id == role.id)).all())
    permissions = list(db.scalars(select(Permission).where(Permission.code.in_(permission_codes))).all())
    db.add_all(RolePermission(role_id=role.id, permission_id=item.id)
        for item in permissions if item.id not in existing_permission_ids)
    if not db.scalar(select(UserRoleAssignment.id).where(
        UserRoleAssignment.user_id == user.id, UserRoleAssignment.role_id == role.id)):
        db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
    db.commit(); db.refresh(user); return user


def ensure_classification_catalog(db):
    for _title, area_code, category_code, *_rest in DEMO_CASES:
        area = db.scalar(select(ExpenseArea).where(ExpenseArea.code == area_code))
        if not area:
            area = ExpenseArea(code=area_code, name=area_code.title(), active=True)
            db.add(area); db.flush()
        if not db.scalar(select(ExpenseSubcategory.id).where(
            ExpenseSubcategory.area_id == area.id,
            ExpenseSubcategory.code == category_code,
        )):
            db.add(ExpenseSubcategory(
                area_id=area.id,
                code=category_code,
                name=category_code.title(),
                active=True,
            ))
    db.commit()


def ensure_multi_quote_case(db, requester, treasurer, title, with_partial_vote):
    existing = db.scalar(select(Expense).where(Expense.title == title))
    if existing:
        return existing
    expense = Expense(
        title=title,
        description='Escenario persistente MULTI_QUOTE para probar votación de cotizaciones.',
        request_type='MULTI_QUOTE',
        expense_type='MAINTENANCE',
        expense_subcategory='EQUIPMENT',
        urgency='HIGH',
        amount=None,
        supplier=None,
        requested_by=requester.email,
        requester_analytics_id=requester.analytics_id,
        status=ExpenseStatus.QUOTATION_VOTING,
        display_id=_next_display_id(db, 'MAINTENANCE'),
    )
    db.add(expense); db.flush()
    options = [
        QuotationOption(expense_id=expense.id, option_number=1, supplier='Proveedor Alpha',
            amount=Decimal('325.00'), item_url='https://example.com/cotizacion-alpha', notes='Entrega inmediata'),
        QuotationOption(expense_id=expense.id, option_number=2, supplier='Proveedor Beta',
            amount=Decimal('299.00'), item_url='https://example.com/cotizacion-beta', notes='Entrega en cinco días'),
        QuotationOption(expense_id=expense.id, option_number=3, supplier='Proveedor Gamma',
            amount=Decimal('340.00'), item_url='https://example.com/cotizacion-gamma', notes='Garantía extendida'),
    ]
    db.add_all(options); db.flush()
    voters = users_with_permission(db, 'requests:approve', exclude_email=requester.email)
    db.add_all(QuotationVotingInvitation(expense_id=expense.id, voter_user_id=user.id) for user in voters)
    db.commit()
    if with_partial_vote:
        expense = db.scalar(select(Expense).where(Expense.id == expense.id).options(
            selectinload(Expense.quotation_options),
            selectinload(Expense.quotation_votes),
            selectinload(Expense.attachments),
        ))
        cast_quotation_vote(db, expense, treasurer, options[1].id)
    print(f'{expense.display_id}: {title} -> QUOTATION_VOTING')
    return expense


def main():
    with SessionLocal() as db:
        set_system_audit_actor(db, 'SYSTEM:demo_monitoring')
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id))
        if not admin: raise RuntimeError('No existe el administrador del sistema')
        ensure_classification_catalog(db)
        users = {item[3]: ensure_user(db, *item) for item in DEMO_USERS}
        policy = db.scalar(select(ApprovalPolicy).where(ApprovalPolicy.name == '[PRUEBA] Aprobación por tesorero'))
        if not policy:
            policy = ApprovalPolicy(name='[PRUEBA] Aprobación por tesorero', expense_type='ALL',
                min_amount=Decimal('0.00'), max_amount=None, approval_mode='ANY',
                approver_profile_codes=['TESORERO'], active=True)
            db.add(policy); db.flush()
            db.commit()

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
        for title, with_partial_vote in DEMO_MULTI_CASES:
            ensure_multi_quote_case(db, users['PROPIETARIO'], users['TESORERO'], title, with_partial_vote)
        print('Credenciales demo locales: solicitante.prueba@example.com / Demo12345!')


if __name__ == '__main__': main()
