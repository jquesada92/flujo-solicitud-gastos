from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.privacy import analytics_identifier
from app.core.security import hash_password, normalize_email
from app.models.entities import User, UserRole
from app.models.iam import Role, UserRoleAssignment


def main() -> None:
    settings = get_settings()
    email = normalize_email(settings.admin_email)

    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.code == 'system-administrator'))
        if not role:
            raise RuntimeError('IAM migration must run before bootstrap_admin.py')

        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if not user:
            user = User(
                name=settings.admin_name,
                email=email,
                analytics_id=analytics_identifier(None, email),
                password_hash=hash_password(settings.admin_password),
                role=UserRole.ADMIN,  # compatibility metadata; not authorization authority
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

        assignment = db.scalar(select(UserRoleAssignment.id).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role_id == role.id,
        ))
        if not assignment:
            db.add(UserRoleAssignment(user_id=user.id, role_id=role.id))

        # Compatibility fields are intentionally constrained to match the
        # technical administrator's effective permissions.
        user.can_request = False
        user.can_approve = False
        user.can_view = True
        user.can_configure = True
        db.commit()


if __name__ == '__main__':
    main()
