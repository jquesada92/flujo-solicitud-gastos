import html
import json
import logging
import smtplib
from email.message import EmailMessage
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module aliases remain patchable in tests, but their source of truth is Settings.
SMTP_HOST = settings.smtp_host
SMTP_PORT = settings.smtp_port
SMTP_USER = settings.smtp_user
SMTP_PASSWORD = settings.smtp_password
SMTP_SECURITY = settings.smtp_security
EMAIL_FROM = settings.email_from
EMAIL_MODE = settings.email_mode
PUBLIC_URL = settings.public_url.rstrip('/')
BREVO_API_KEY = settings.brevo_api_key or ''
BREVO_SENDER_NAME = settings.brevo_sender_name
BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'
PRODUCT_NAME = 'Gestión de Solicitudes'


def _send_brevo(to: str, subject: str, text_body: str, html_body: str | None) -> None:
    if not BREVO_API_KEY:
        raise RuntimeError('BREVO_API_KEY is required when EMAIL_MODE=brevo')
    if not EMAIL_FROM:
        raise RuntimeError('A verified EMAIL_FROM is required when EMAIL_MODE=brevo')
    payload = {
        'sender': {'email': EMAIL_FROM, 'name': BREVO_SENDER_NAME},
        'to': [{'email': to}],
        'subject': subject,
    }
    if html_body:
        payload['htmlContent'] = html_body
    else:
        payload['textContent'] = text_body
    request = Request(
        BREVO_API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'accept': 'application/json',
            'api-key': BREVO_API_KEY,
            'content-type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 201:
                raise RuntimeError(f'Brevo rejected the email with HTTP {response.status}')
    except HTTPError as exc:
        raise RuntimeError(f'Brevo rejected the email with HTTP {exc.code}') from exc
    except URLError as exc:
        raise RuntimeError('Could not connect to the Brevo email API') from exc


def _send(to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    if EMAIL_MODE == 'console':
        logger.warning(
            '\n--- EMAIL (console mode) ---\nTO: %s\nSUBJECT: %s\n%s\n----------------------------',
            to,
            subject,
            text_body,
        )
        return
    if EMAIL_MODE == 'brevo':
        _send_brevo(to, subject, text_body, html_body)
        return
    if EMAIL_MODE != 'smtp':
        raise RuntimeError(f'Unsupported EMAIL_MODE: {EMAIL_MODE}')

    msg = EmailMessage()
    msg['From'], msg['To'], msg['Subject'] = EMAIL_FROM, to, subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')

    if SMTP_SECURITY == 'starttls':
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)


def _layout(title: str, content: str) -> str:
    return f'''<!doctype html><html><body style="margin:0;background:#f4f6fa;font-family:Arial,sans-serif;color:#172033">
<div style="max-width:640px;margin:24px auto;background:white;border:1px solid #e3e7ee;border-radius:16px;overflow:hidden">
<div style="background:#111827;color:white;padding:20px 26px"><b>{html.escape(PRODUCT_NAME)}</b><div style="font-size:12px;color:#b8c0cf;margin-top:4px">{html.escape(title)}</div></div>
<div style="padding:26px">{content}</div></div></body></html>'''


def _access_summary_text(
    position_names: list[str] | None,
    permissions: list[tuple[str, str]] | None,
) -> str:
    positions = position_names or []
    effective = permissions or []
    position_lines = '\n'.join(f'- {name}' for name in positions) or '- Sin cargo asignado'
    permission_lines = '\n'.join(
        f'- {name} ({code})' for name, code in effective
    ) or '- Sin permisos efectivos adicionales'
    return f'''Cargo(s):
{position_lines}

Permisos efectivos:
{permission_lines}'''


def _access_summary_html(
    position_names: list[str] | None,
    permissions: list[tuple[str, str]] | None,
) -> str:
    positions = position_names or []
    effective = permissions or []
    position_items = ''.join(f'<li>{html.escape(name)}</li>' for name in positions) or '<li>Sin cargo asignado</li>'
    permission_items = ''.join(
        f'<li>{html.escape(name)} <code>{html.escape(code)}</code></li>'
        for name, code in effective
    ) or '<li>Sin permisos efectivos adicionales</li>'
    return f'''<div style="background:#f7f8fa;padding:16px;border-radius:10px;margin:18px 0">
<b>Cargo(s)</b><ul>{position_items}</ul>
<b>Permisos efectivos</b><ul>{permission_items}</ul>
</div>'''


def send_user_invitation(
    user,
    temporary_password: str,
    position_names: list[str] | None = None,
    permissions: list[tuple[str, str]] | None = None,
) -> None:
    access_text = _access_summary_text(position_names, permissions)
    access_html = _access_summary_html(position_names, permissions)
    text_body = f'''Acceso a {PRODUCT_NAME}

Hola {user.name},

Se creó una cuenta para ti.

Usuario: {user.email}
Contraseña temporal: {temporary_password}
Acceso: {PUBLIC_URL}

{access_text}

Al iniciar sesión deberás crear una contraseña nueva antes de continuar.
No compartas estas credenciales.
'''
    html_body = _layout(
        'INVITACIÓN DE USUARIO',
        f'''<h2>Hola {html.escape(user.name)}</h2><p>Se creó una cuenta para ti.</p>
<div style="background:#f7f8fa;padding:16px;border-radius:10px;line-height:1.8"><b>Usuario:</b> {html.escape(user.email)}<br><b>Contraseña temporal:</b> <code>{html.escape(temporary_password)}</code></div>
{access_html}
<p>Al iniciar sesión deberás reemplazar esta contraseña antes de usar el sistema.</p>
<a href="{html.escape(PUBLIC_URL)}" style="display:inline-block;background:#172033;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Iniciar sesión</a>''',
    )
    _send(user.email, f'Tu acceso a {PRODUCT_NAME}', text_body, html_body)


def send_password_reset_link(user, reset_token: str) -> None:
    reset_link = f'{PUBLIC_URL}/reset-password#token={quote(reset_token, safe="")}'
    expires_in = settings.password_reset_token_expire_minutes
    text_body = f'''Restablecimiento de contraseña de {PRODUCT_NAME}

Hola {user.name},

Un administrador generó un enlace para que restablezcas tu contraseña.
El enlace vence en {expires_in} minutos y solo puede utilizarse una vez:

{reset_link}

Tu contraseña y tus sesiones actuales siguen vigentes hasta que completes el restablecimiento.
Si no esperabas este mensaje, comunícate con el administrador del sistema.
'''
    html_body = _layout(
        'RESTABLECIMIENTO DE CONTRASEÑA',
        f'''<h2>Hola {html.escape(user.name)}</h2>
<p>Un administrador generó un enlace para que restablezcas tu contraseña.</p>
<p>El enlace vence en {expires_in} minutos y solo puede utilizarse una vez.</p>
<a href="{html.escape(reset_link)}" style="display:inline-block;background:#172033;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Restablecer contraseña</a>
<p style="color:#697386">Tu contraseña y tus sesiones actuales siguen vigentes hasta que completes el restablecimiento. Si no esperabas este mensaje, comunícate con el administrador del sistema.</p>''',
    )
    _send(user.email, f'Restablece tu contraseña · {PRODUCT_NAME}', text_body, html_body)


def send_password_reset_completed(user) -> None:
    text_body = f'''Contraseña actualizada en {PRODUCT_NAME}

Hola {user.name},

Tu contraseña fue restablecida correctamente y las sesiones anteriores fueron cerradas.

Si no realizaste esta acción, comunícate de inmediato con el administrador del sistema.
Acceso: {PUBLIC_URL}
'''
    html_body = _layout(
        'CONTRASEÑA ACTUALIZADA',
        f'''<h2>Hola {html.escape(user.name)}</h2>
<p>Tu contraseña fue restablecida correctamente y las sesiones anteriores fueron cerradas.</p>
<p style="color:#697386">Si no realizaste esta acción, comunícate de inmediato con el administrador del sistema.</p>
<a href="{html.escape(PUBLIC_URL)}" style="display:inline-block;background:#172033;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Abrir sistema</a>''',
    )
    _send(user.email, f'Contraseña actualizada · {PRODUCT_NAME}', text_body, html_body)


def send_user_access_updated(
    user,
    position_names: list[str],
    permissions: list[tuple[str, str]],
) -> None:
    access_text = _access_summary_text(position_names, permissions)
    access_html = _access_summary_html(position_names, permissions)
    text_body = f'''Actualización de acceso a {PRODUCT_NAME}

Hola {user.name},

Tu cargo en el sistema fue actualizado. A continuación se muestra tu configuración vigente:

{access_text}

Estos permisos son los permisos efectivos actuales de tu cuenta y pueden provenir de tu cargo, grupos, roles o asignaciones directas.
Acceso: {PUBLIC_URL}
'''
    html_body = _layout(
        'ACTUALIZACIÓN DE CARGO Y PERMISOS',
        f'''<h2>Hola {html.escape(user.name)}</h2>
<p>Tu cargo en el sistema fue actualizado. Esta es tu configuración vigente:</p>
{access_html}
<p style="color:#697386">Los permisos mostrados son los permisos efectivos actuales de tu cuenta y pueden provenir de tu cargo, grupos, roles o asignaciones directas.</p>
<a href="{html.escape(PUBLIC_URL)}" style="display:inline-block;background:#172033;color:white;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">Abrir sistema</a>''',
    )
    _send(user.email, f'Actualización de cargo y permisos · {PRODUCT_NAME}', text_body, html_body)


def send_approval_request(approval) -> None:
    expense = approval.expense
    detail_link = f'{PUBLIC_URL}/email-action/approval/{approval.token}'
    approve_link = f'{detail_link}?action=APPROVED'
    reject_link = f'{detail_link}?action=REJECTED'
    review_link = f'{detail_link}?action=REVISION_REQUESTED'
    supports = [f'URL: {expense.item_url}'] if expense.item_url else []
    supports.extend(f'Archivo: {item.original_name}' for item in expense.attachments)
    text_body = f'''Solicitud pendiente de decisión

Solicitud: {expense.display_id}
Título: {expense.title}
Área: {expense.expense_type}
Categoría: {expense.expense_subcategory or '-'}
Proveedor: {expense.supplier or '-'}
Monto: ${expense.amount}
Solicitante: {expense.requested_by}
Descripción: {expense.description}
{chr(10).join(supports)}

APROBAR: {approve_link}
RECHAZAR: {reject_link}
ENVIAR A REVISIÓN: {review_link}
VER DETALLE: {detail_link}
'''
    html_body = _layout(
        'APROBACIÓN REQUERIDA',
        f'''<div style="font-size:12px;color:#697386">Solicitud {html.escape(expense.display_id)}</div>
<h2>{html.escape(expense.title)}</h2><div style="font-size:34px;font-weight:bold;margin:18px 0">${expense.amount}</div>
<p><b>Área:</b> {html.escape(expense.expense_type)}<br><b>Categoría:</b> {html.escape(expense.expense_subcategory or '-')}<br><b>Proveedor:</b> {html.escape(expense.supplier or '-')}</p>
<div style="background:#f7f8fa;padding:14px;border-radius:9px;margin:18px 0">{html.escape(expense.description)}</div>
<div style="display:flex;gap:8px;flex-wrap:wrap"><a href="{approve_link}" style="background:#17653a;color:white;text-decoration:none;padding:12px 20px;border-radius:8px">Aprobar</a><a href="{reject_link}" style="background:#b42318;color:white;text-decoration:none;padding:12px 20px;border-radius:8px">Rechazar</a><a href="{review_link}" style="background:#b7791f;color:white;text-decoration:none;padding:12px 20px;border-radius:8px">Enviar a revisión</a></div>''',
    )
    _send(approval.approver_email, f'Aprobación requerida · {expense.display_id}', text_body, html_body)


def send_quotation_vote_request(expense, user, invitation) -> None:
    options = '\n'.join(
        f'Opción {item.option_number}: {item.supplier} · ${item.amount}'
        for item in expense.quotation_options
    )
    vote_base = f'{PUBLIC_URL}/email-action/vote/{invitation.token}'
    options_html = ''.join(
        f'<div style="padding:12px;border:1px solid #e3e7ee;border-radius:9px;margin:8px 0"><b>Opción {item.option_number}: {html.escape(item.supplier)}</b><div style="font-size:22px;margin:5px 0">${item.amount}</div><a href="{vote_base}?option={item.id}">Votar por esta opción</a></div>'
        for item in expense.quotation_options
    )
    text_body = f'''Votación de cotizaciones pendiente

Solicitud: {expense.display_id}
Título: {expense.title}
Descripción: {expense.description}

{options}

ABRIR VOTACIÓN: {vote_base}
'''
    html_body = _layout(
        'VOTACIÓN DE COTIZACIONES',
        f'''<div style="font-size:12px;color:#697386">Solicitud {html.escape(expense.display_id)}</div><h2>{html.escape(expense.title)}</h2><p>{html.escape(expense.description)}</p>{options_html}<a href="{html.escape(vote_base)}">Ver todas las opciones</a>''',
    )
    _send(user.email, f'Votación pendiente · {expense.display_id}', text_body, html_body)


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
    revision_note = revision.comment if revision else None
    support_text = '\n'.join(
        ([f'URL: {expense.item_url}'] if expense.item_url else [])
        + [f'Archivo: {item.original_name}' for item in expense.attachments]
    ) or 'Sin soportes registrados'
    body = f'''Actualización de solicitud

Solicitud: {expense.display_id}
Título: {expense.title}
Área: {expense.expense_type}
Categoría: {expense.expense_subcategory or '-'}
Proveedor: {expense.supplier or '-'}
Monto: ${expense.amount}
Estado: {status_label}
Descripción: {expense.description}
Soportes:\n{support_text}
{f'Revisión solicitada: {revision_note}' if revision_note else ''}
'''
    correction_html = f'<div style="padding:14px;background:#fff7df;border-radius:9px"><b>Revisión solicitada:</b> {html.escape(revision_note)}</div>' if revision_note else ''
    html_body = _layout(
        status_label,
        f'''<div style="font-size:12px;color:#697386">Solicitud {html.escape(expense.display_id)}</div><h2>{html.escape(expense.title)}</h2><div style="font-size:34px;font-weight:bold;margin:18px 0">${expense.amount}</div><p><b>Área:</b> {html.escape(expense.expense_type)}<br><b>Categoría:</b> {html.escape(expense.expense_subcategory or '-')}<br><b>Estado:</b> {html.escape(status_label)}</p>{correction_html}<p>{html.escape(expense.description)}</p><a href="{html.escape(PUBLIC_URL)}">Abrir sistema</a>''',
    )
    _send(expense.requested_by, f'Solicitud {expense.display_id}: {status_label}', body, html_body)
