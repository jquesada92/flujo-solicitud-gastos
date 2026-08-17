"""Send a diagnostic email using the application's configured transport.

Run from the backend project root:
    python -m scripts.test_email --to user@example.com

Inside Docker Compose:
    docker compose exec backend python -m scripts.test_email --to user@example.com
"""

import argparse

from app.core.config import get_settings
from app.services.email_service import _send


def main() -> None:
    parser = argparse.ArgumentParser(description='Send a diagnostic email using configured EMAIL_MODE')
    parser.add_argument('--to', dest='recipient', help='Recipient email. Defaults to ADMIN_EMAIL.')
    args = parser.parse_args()

    settings = get_settings()
    recipient = (args.recipient or settings.admin_email).strip()
    if not recipient:
        raise SystemExit('A recipient is required via --to or ADMIN_EMAIL')

    print(
        'Email diagnostic: '
        f'mode={settings.email_mode}, '
        f'host={settings.smtp_host if settings.email_mode == "smtp" else "n/a"}, '
        f'port={settings.smtp_port if settings.email_mode == "smtp" else "n/a"}, '
        f'security={settings.smtp_security if settings.email_mode == "smtp" else "n/a"}, '
        f'from={settings.email_from}, '
        f'to={recipient}'
    )

    _send(
        recipient,
        'Prueba de correo · Gestión de Solicitudes',
        'Este correo confirma que el transporte configurado por la aplicación funciona correctamente.',
        '<p>Este correo confirma que el transporte configurado por la aplicación funciona correctamente.</p>',
    )
    print('Email accepted by the configured transport.')


if __name__ == '__main__':
    main()
