# Plan técnico — Cierre/factura por propiedad o delegación

**Feature:** 008  
**Constitución:** 2.7.0

## 1. Persistencia

Crear `expense_closure_delegations` mediante Alembic `20260818_0005`.

Diseño:

```text
ExpenseClosureDelegation
- id
- expense_id
- delegate_user_id
- delegated_by_user_id
- delegated_by_email
- created_at
- revoked_at
- revoked_by_user_id
- revoked_by_email
```

Mantener historial por revocación, no DELETE físico.

Crear índice único parcial por `expense_id WHERE revoked_at IS NULL`.

Marcar `permissions.code='requests:close'` como inactivo/legacy sin borrar asignaciones históricas.

## 2. Servicio de dominio

Crear `closure_service.py` con:

- `is_requester()`;
- `active_closure_delegation()`;
- `can_manage_closure()`;
- `can_delegate_closure()`;
- `closure_delegation_candidates()`;
- `assign_closure_delegate()`;
- `revoke_closure_delegate()`.

`can_manage_closure()` no debe llamar `has_permission(..., 'requests:close')`.

## 3. API de delegación

Crear `closure_delegation.py`:

```text
GET    /api/expenses/{request_id}/closure-delegation
PUT    /api/expenses/{request_id}/closure-delegation
DELETE /api/expenses/{request_id}/closure-delegation
```

PUT/DELETE: solo solicitante original.

GET: solicitante, Administrador del sistema o delegado vigente pueden consultar el contexto; solo el solicitante recibe candidatos y `can_delegate=true`.

## 4. Cierre/factura

Modificar `financial_actions.py`:

- sustituir `require_permission('requests:close')` por `current_user`;
- cargar/bloquear solicitud;
- validar estado;
- llamar `can_manage_closure()`;
- devolver 403 a terceros;
- conservar validación de archivos y versionado de factura.

## 5. Seguimiento

Extender `ExpenseOut`:

```text
can_close
can_delegate_close
```

`tracking.py` los calcula por solicitud.

## 6. Dashboard

Modificar `pending_action_service.py`:

```text
CLOSE_REQUEST
= APPROVED
+ (requester OR active_delegate)
```

No usar `requests:close`.

No asignar todas las solicitudes aprobadas al Administrador del sistema; su facultad es administrativa desde la lista.

## 7. Frontend

Crear `frontend/src/closure-delegation.jsx`.

Funciones:

- abrir modal;
- cargar delegado/candidatos;
- asignar/cambiar delegado;
- revocar;
- refrescar listado.

Mientras `ExpenseTable` permanezca en `main.jsx`, Vite conecta temporalmente:

- `x.can_close` para cierre/corrección factura;
- `x.can_delegate_close` para modal de delegación;
- acción de tabla basada en capacidades por recurso.

Retirar esta transformación cuando `ExpenseTable` sea modular.

## 8. Pruebas

Agregar:

- `test_closure_delegation.py`;
- regresión de Dashboard para requester/delegate;
- regresión de un usuario con `requests:close` legacy sin autoridad;
- topología Alembic `0005`;
- contrato frontend de `x.can_close`/`x.can_delegate_close`.

Casos mínimos:

```text
requester APPROVED → can_close true
system_admin APPROVED → can_close true
delegate APPROVED → can_close true
legacy requests:close only → can_close false
revoke delegation → delegate can_close false
non-requester PUT delegation → 403
```

## 9. Despliegue

Antes de producción:

1. backup/snapshot Neon;
2. ejecutar `alembic upgrade head` en preview/copia;
3. confirmar `0005` como head;
4. confirmar tabla e índice parcial;
5. confirmar `requests:close` inactivo;
6. smoke requester/delegate/admin;
7. desplegar Render;
8. desplegar/redeploy Vercel si el frontend no se actualiza automáticamente.

## 10. Documentación

Actualizar en el mismo PR:

- Constitución 2.7.0;
- Feature 008 spec/plan/checklist;
- README;
- prompt maestro;
- `docs/FASTAPI_ARCHITECTURE.md`;
- `docs/IAM_MODEL.md`;
- `docs/REQUEST_TRACKING.md`;
- documentación de cierre/delegación;
- `docs/TERMINOLOGY.md`;
- `docs/README.md`;
- HISTORY;
- CHANGELOG;
- PR #9.
