from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.privacy import analytics_identifier
from app.core.security import hash_password, normalize_email
from app.models.entities import User, UserRole
from app.models.iam import Role, SystemAccount


def main() -> None:
    settings = get_settings()
    email = normalize_email(settings.admin_email)

    with SessionLocal() as db:
        # The technical role is still seeded as protected product metadata, but
        # technical accounts do not receive ordinary group-scoped role grants.
        # Their authorization comes exclusively from SystemAccount policy.
        role = db.scalar(select(Role).where(Role.code == 'system-administrator'))
        if not role:
            raise RuntimeError('IAM migrations must run before bootstrap_admin.py')

        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if not user:
            user = User(
                name=settings.admin_name,
                email=email,
                analytics_id=analytics_identifier(None, email),
                password_hash=hash_password(settings.admin_password),
                role=UserRole.ADMIN,  # compatibility metadata; never authorization authority
                title='ADMIN_SISTEMA',
                active=True,
                can_request=False,
                can_approve=False,
                can_view=True,
                can_configure=True,
                must_change_password=False,
            )
            db.add(user)
            db.flush()

        if not db.scalar(select(SystemAccount.id).where(SystemAccount.user_id == user.id)):
            db.add(SystemAccount(user_id=user.id, account_type='TECHNICAL_ADMIN'))

        # Compatibility fields mirror the technical account policy for the
        # legacy frontend only. No UserRoleAssignment is created here.
        user.can_request = False
        user.can_approve = False
        user.can_view = True
        user.can_configure = True
        db.commit()


if __name__ == '__main__':
    main()
