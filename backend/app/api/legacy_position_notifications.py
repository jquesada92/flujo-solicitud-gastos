from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.users import _apply_user_changes
from app.core.database import get_db
from app.core.security import require_permission
from app.models.entities import AccessProfile, User
from app.models.iam import Permission, Position, UserPosition
from app.schemas.user import UserBulkUpdate, UserOut
from app.services.email_service import send_user_access_updated
from app.services.iam_service import effective_permission_codes

router = APIRouter(dependencies=[Depends(require_permission('config:manage'))])


def _legacy_position_code(profile_code: str) -> str:
    return f"legacy-{profile_code.lower().replace('_', '-')}"


def _position_for_profile(db: Session, profile: AccessProfile) -> Position:
    position = db.scalar(
        select(Position)
        .where(
            Position.active.is_(True),
            or_(
                func.lower(Position.name) == profile.name.lower(),
                Position.code == _legacy_position_code(profile.code),
            ),
        )
        .order_by(Position.id)
    )
    if not position:
        raise HTTPException(
            status_code=409,
            detail=(
                f'El cargo {profile.name} todavía no está sincronizado con Accesos/IAM. '
                'Configúralo en Accesos antes de asignarlo a un usuario.'
            ),
        )
    return position


def _replace_canonical_position(
    db: Session,
    user: User,
    profile: AccessProfile | None,
) -> bool:
    current_ids = set(
        db.scalars(
            select(UserPosition.position_id).where(UserPosition.user_id == user.id)
        ).all()
    )
    target_ids: set[int] = set()
    if profile is not None:
        target_ids.add(_position_for_profile(db, profile).id)
    if current_ids == target_ids:
        return False

    db.execute(delete(UserPosition).where(UserPosition.user_id == user.id))
    db.add_all(
        UserPosition(user_id=user.id, position_id=position_id)
        for position_id in sorted(target_ids)
    )
    return True


def _access_email_summary(
    db: Session,
    user: User,
) -> tuple[list[str], list[tuple[str, str]]]:
    position_names = list(
        db.scalars(
            select(Position.name)
            .join(UserPosition, UserPosition.position_id == Position.id)
            .where(
                UserPosition.user_id == user.id,
                Position.active.is_(True),
            )
            .order_by(Position.name)
        ).all()
    )
    effective_codes = effective_permission_codes(db, user.id)
    if not effective_codes:
        return position_names, []

    permissions_by_code = {
        item.code: item.name
        for item in db.scalars(
            select(Permission)
            .where(
                Permission.code.in_(effective_codes),
                Permission.active.is_(True),
            )
            .order_by(Permission.name, Permission.code)
        ).all()
    }
    permissions = [
        (permissions_by_code.get(code, code), code)
        for code in sorted(
            effective_codes,
            key=lambda value: (permissions_by_code.get(value, value), value),
        )
    ]
    return position_names, permissions


@router.patch('/bulk', response_model=list[UserOut])
def bulk_update_users_with_access_notifications(
    payload: UserBulkUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission('config:manage')),
):
    """Compatibility handler for Organigrama -> Asignación de cargos.

    The legacy screen still submits ``users.title``. This route keeps that display
    field working while making ``user_positions`` the canonical IAM assignment.
    Cargo-change emails are generated from canonical Positions + effective IAM
    permissions, exactly like the Access Management screen.
    """
    ids = [item.id for item in payload.users]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail='La solicitud contiene usuarios repetidos')

    records = {
        user.id: user
        for user in db.scalars(
            select(User).where(User.id.in_(ids)).with_for_update()
        ).all()
    }
    missing = [user_id for user_id in ids if user_id not in records]
    if missing:
        raise HTTPException(status_code=404, detail=f'Usuarios no encontrados: {missing}')

    notify_user_ids: list[int] = []
    try:
        for item in payload.users:
            user = records[item.id]
            original_title = user.title
            changes = item.model_dump(exclude={'id'}, exclude_unset=True)
            _apply_user_changes(db, user, changes, actor)

            title_changed = 'title' in changes and user.title != original_title
            if title_changed:
                profile = None
                if user.title != 'SIN_ASIGNAR':
                    profile = db.scalar(
                        select(AccessProfile).where(AccessProfile.code == user.title)
                    )
                    if not profile:
                        raise HTTPException(status_code=422, detail='El cargo seleccionado no existe')
                canonical_changed = _replace_canonical_position(db, user, profile)
                if canonical_changed and user.active:
                    notify_user_ids.append(user.id)
            db.flush()

        db.flush()
        for user_id in notify_user_ids:
            user = records[user_id]
            positions, permissions = _access_email_summary(db, user)
            send_user_access_updated(user, positions, permissions)

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail='Ya existe un usuario con ese correo o cédula',
        ) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        if notify_user_ids:
            raise HTTPException(
                status_code=502,
                detail='No se pudo actualizar el cargo y enviar la notificación al usuario',
            ) from exc
        raise

    return list(db.scalars(select(User).order_by(User.name)).all())
