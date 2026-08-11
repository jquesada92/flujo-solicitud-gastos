import html
import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_SECURITY = os.getenv('SMTP_SECURITY', 'ssl').lower()
EMAIL_FROM = os.getenv('EMAIL_FROM', SMTP_USER or 'noreply@ph.local')
EMAIL_MODE = os.getenv('EMAIL_MODE', 'console').lower()
PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:3000').rstrip('/')


def _send(to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    if EMAIL_MODE != 'smtp':
        logger.warning('\n--- EMAIL (console mode) ---\nTO: %s\nSUBJECT: %s\n%s\n----------------------------', to, subject, text_body)
        return
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError('SMTP_USER and SMTP_PASSWORD are required when EMAIL_MODE=smtp')

    msg = EmailMessage()
    msg['From'], msg['To'], msg['Subject'] = EMAIL_FROM, to, subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')

    if SMTP_SECURITY == 'starttls':
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(); server.login(SMTP_USER, SMTP_PASSWORD); server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD); server.send_message(msg)


def send_approval_request(approval) -> None:
    expense = approval.expense
    detail_link = f'{PUBLIC_URL}/approve/{approval.token}'
    review_link = f'{detail_link}?action=revision'
    approve_link = f'{detail_link}?action=approve'
    reject_link = f'{detail_link}?action=reject'
    support_text = []
    support_html = []
    if expense.item_url:
        support_text.append(f'URL: {expense.item_url}')
        support_html.append(f'<a href="{html.escape(expense.item_url)}">Ver producto o servicio</a>')
    for attachment in expense.attachments:
        support_text.append(f'Cotización adjunta en el sistema: {attachment.original_name}')
        support_html.append(f'<span>📎 {html.escape(attachment.original_name)}</span>')

    text_body = f'''PH - Solicitud de gasto pendiente

Solicitud: {expense.display_id}
Flujo: {expense.flow_id}
Título: {expense.title}
Categoría: {expense.expense_type} / {expense.expense_subcategory or '-'}
Proveedor: {expense.supplier}
Monto: ${expense.amount}
Solicitado por: {expense.requested_by}
Descripción: {expense.description}
{chr(10).join(support_text)}

APROBAR: {approve_link}
RECHAZAR: {reject_link}
ENVIAR A REVISIÓN: {review_link}
VER DETALLE: {detail_link}

Por seguridad, deberá iniciar sesión y confirmar la decisión.
'''
    html_body = f'''<!doctype html><html><body style="margin:0;background:#f4f6fa;font-family:Arial,sans-serif;color:#172033">
<div style="max-width:640px;margin:24px auto;background:white;border:1px solid #e3e7ee;border-radius:16px;overflow:hidden">
<div style="background:#111827;color:white;padding:20px 26px"><b>PH · Gestión de Gastos</b><div style="font-size:12px;color:#b8c0cf;margin-top:4px">APROBACIÓN REQUERIDA</div></div>
<div style="padding:26px"><div style="font-size:12px;color:#697386">Solicitud {html.escape(expense.display_id)} · Flujo {html.escape(expense.flow_id)}</div>
<h2 style="margin:10px 0">{html.escape(expense.title)}</h2><div style="font-size:34px;font-weight:bold;margin:18px 0">${expense.amount}</div>
<table style="width:100%;font-size:14px;border-collapse:collapse"><tr><td style="padding:7px 0;color:#697386">Categoría</td><td>{html.escape(expense.expense_type)} / {html.escape(expense.expense_subcategory or '-')}</td></tr><tr><td style="padding:7px 0;color:#697386">Proveedor</td><td>{html.escape(expense.supplier)}</td></tr><tr><td style="padding:7px 0;color:#697386">Solicitante</td><td>{html.escape(expense.requested_by)}</td></tr></table>
<div style="background:#f7f8fa;padding:14px;border-radius:9px;margin:18px 0;line-height:1.5">{html.escape(expense.description)}</div>
<div style="display:grid;gap:6px;margin-bottom:22px">{''.join(f'<div>{item}</div>' for item in support_html)}</div>
<div style="display:flex;gap:8px;flex-wrap:wrap"><a href="{approve_link}" style="background:#17653a;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Aprobar</a><a href="{reject_link}" style="background:#b42318;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Rechazar</a><a href="{review_link}" style="background:#b7791f;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Enviar a revisión</a><a href="{detail_link}" style="background:#e9edf3;color:#172033;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Ver detalle</a></div>
<p style="font-size:11px;color:#7a8494;margin-top:20px">El enlace requiere iniciar sesión. Aprobar o rechazar siempre exige confirmación para evitar decisiones accidentales.</p></div></div></body></html>'''
    _send(approval.approver_email, f'Aprobación requerida · {expense.display_id}', text_body, html_body)


def send_final_notification(expense) -> None:
    status_labels = {
        'APPROVED': 'APROBADA',
        'REJECTED': 'RECHAZADA',
        'NEEDS_REVISION': 'REQUIERE REVISIÓN',
        'CANCELLED': 'CANCELADA',
        'CLOSED': 'CERRADA',
    }
    status = expense.status.value
    status_label = status_labels.get(status, status)
    revision = next(
        (approval for approval in expense.approvals if approval.status.value == 'REVISION_REQUESTED'),
        None,
    )
    revision_note = ''
    if revision:
        revision_note = f'''\nCorrecciones solicitadas:\n{revision.comment or 'Revisa la solicitud y corrige la información indicada.'}\n\nIngresa al sistema para corregir y reenviar la solicitud: {PUBLIC_URL}\n'''
    supports = []
    if expense.item_url:
        supports.append(f'URL del producto o servicio: {expense.item_url}')
    supports.extend(f'Archivo adjunto en el sistema: {item.original_name}' for item in expense.attachments)
    support_text = '\n'.join(supports) or 'Sin soportes registrados'
    body = f'''PH - Actualización de solicitud de gasto

Solicitud: {expense.display_id}
Flujo: {expense.flow_id}
Título: {expense.title}
Categoría: {expense.expense_type}
Subcategoría: {expense.expense_subcategory or '-'}
Proveedor: {expense.supplier}
Monto: ${expense.amount}
Solicitante: {expense.requested_by}
Estado: {status_label}
Descripción / justificación:
{expense.description}

Soportes:
{support_text}
{revision_note}
'''
    revision_html = ''
    if revision:
        revision_html = f'<div style="margin:18px 0;padding:14px;background:#fff7df;border-radius:9px"><b>Correcciones solicitadas</b><p>{html.escape(revision.comment or "Revisa la solicitud y corrige la información indicada.")}</p></div>'
    support_html = ''.join(
        [f'<div><a href="{html.escape(expense.item_url)}">Ver producto o servicio</a></div>'] if expense.item_url else []
    ) + ''.join(f'<div>📎 {html.escape(item.original_name)}</div>' for item in expense.attachments)
    html_body = f'''<!doctype html><html><body style="margin:0;background:#f4f6fa;font-family:Arial,sans-serif;color:#172033">
<div style="max-width:640px;margin:24px auto;background:white;border:1px solid #e3e7ee;border-radius:16px;overflow:hidden">
<div style="background:#111827;color:white;padding:20px 26px"><b>PH · Gestión de Gastos</b><div style="font-size:12px;color:#b8c0cf;margin-top:4px">{html.escape(status_label)}</div></div>
<div style="padding:26px"><div style="font-size:12px;color:#697386">Solicitud {html.escape(expense.display_id)} · Flujo {html.escape(expense.flow_id)}</div>
<h2>{html.escape(expense.title)}</h2><div style="font-size:34px;font-weight:bold;margin:18px 0">${expense.amount}</div>
<table style="width:100%;font-size:14px;border-collapse:collapse"><tr><td style="padding:7px 0;color:#697386">Categoría</td><td>{html.escape(expense.expense_type)} / {html.escape(expense.expense_subcategory or '-')}</td></tr><tr><td style="padding:7px 0;color:#697386">Proveedor</td><td>{html.escape(expense.supplier)}</td></tr><tr><td style="padding:7px 0;color:#697386">Solicitante</td><td>{html.escape(expense.requested_by)}</td></tr></table>
<div style="background:#f7f8fa;padding:14px;border-radius:9px;margin:18px 0"><b>Descripción / justificación</b><p style="white-space:pre-wrap">{html.escape(expense.description)}</p></div>
{revision_html}<div style="display:grid;gap:6px;margin:18px 0">{support_html or '<span>Sin soportes registrados</span>'}</div>
<a href="{PUBLIC_URL}" style="display:inline-block;background:#172033;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Abrir sistema</a>
</div></div></body></html>'''
    _send(expense.requested_by, f'Solicitud {expense.display_id}: {status_label}', body, html_body)
