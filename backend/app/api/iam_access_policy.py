from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_permission

router = APIRouter(dependencies=[Depends(require_permission('config:manage'))])


@router.put('/users/{user_id}/permissions/{permission_code}')
def reject_direct_permission(user_id: int, permission_code: str):
    raise HTTPException(
        status_code=409,
        detail='Los permisos no se asignan directamente a usuarios. Asigna un rol al usuario o a uno de sus grupos.',
    )


@router.put('/positions/{position_id}/roles/{role_id}')
def reject_position_role(position_id: int, role_id: int):
    raise HTTPException(
        status_code=409,
        detail='Los cargos pertenecen al organigrama y no otorgan acceso. Asigna el rol al usuario o a un grupo.',
    )
