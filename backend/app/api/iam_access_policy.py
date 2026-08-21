from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_permission

router = APIRouter(dependencies=[Depends(require_permission('config:manage'))])


@router.put('/users/{user_id}/permissions/{permission_code}')
def reject_direct_permission(user_id: int, permission_code: str):
    raise HTTPException(
        status_code=409,
        detail='Los permisos no se asignan directamente a usuarios. Asigna permisos al rol.',
    )


@router.put('/positions/{position_id}/roles/{role_id}')
def reject_position_role(position_id: int, role_id: int):
    raise HTTPException(
        status_code=409,
        detail='Los cargos pertenecen al organigrama y no otorgan acceso.',
    )


@router.put('/groups/{group_id}/members/{user_id}')
def reject_independent_group_member(group_id: int, user_id: int):
    raise HTTPException(
        status_code=409,
        detail='La membresía de grupo se obtiene al asignar al usuario un rol de ese grupo.',
    )


@router.delete('/groups/{group_id}/members/{user_id}')
def reject_independent_group_member_delete(group_id: int, user_id: int):
    raise HTTPException(
        status_code=409,
        detail='Para sacar al usuario del grupo, elimina su rol dentro de ese grupo.',
    )


@router.put('/users/{user_id}/roles/{role_id}')
def reject_legacy_user_role(user_id: int, role_id: int):
    raise HTTPException(
        status_code=409,
        detail='Los roles agrupados y globales se guardan desde la ficha del usuario en Accesos.',
    )


@router.delete('/users/{user_id}/roles/{role_id}')
def reject_legacy_user_role_delete(user_id: int, role_id: int):
    raise HTTPException(
        status_code=409,
        detail='Los roles agrupados y globales se guardan desde la ficha del usuario en Accesos.',
    )


@router.put('/groups/{group_id}/roles/{role_id}')
def reject_legacy_group_role(group_id: int, role_id: int):
    raise HTTPException(
        status_code=409,
        detail='Los roles del grupo se guardan desde el formulario del grupo.',
    )


@router.delete('/groups/{group_id}/roles/{role_id}')
def reject_legacy_group_role_delete(group_id: int, role_id: int):
    raise HTTPException(
        status_code=409,
        detail='Los roles del grupo se guardan desde el formulario del grupo.',
    )
