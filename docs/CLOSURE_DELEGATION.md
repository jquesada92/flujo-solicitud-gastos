# Cierre, factura y delegación por solicitud

## Regla canónica

Cerrar una solicitud, registrar su factura final o reemplazar/corregir esa factura no es un permiso global.

```text
actor autorizado =
    solicitante original
 OR Administrador del sistema (system_accounts)
 OR delegado activo de ESA solicitud
```

`requests:close` queda como compatibilidad histórica inactiva y no es autoridad runtime.

## Estados

### `APPROVED`

Un actor autorizado puede:

- adjuntar factura;
- agregar notas de cierre;
- cerrar la solicitud.

### `CLOSED`

Un actor autorizado puede reemplazar/corregir la factura vigente con motivo obligatorio.

En otros estados `can_close=false`.

## Capacidades devueltas por seguimiento

`GET /api/expenses` expone:

```json
{
  "can_close": true,
  "can_delegate_close": true
}
```

### `can_close`

```text
status ∈ {APPROVED, CLOSED}
AND
(requester OR system_account OR active_delegate)
```

### `can_delegate_close`

Solo el solicitante original y únicamente en estados donde la delegación todavía tiene sentido operativo.

La UI nunca debe reconstruir estas reglas con `user.can_close`, `UserRole`, Cargo o Rol.

## Delegación

Persistencia:

```text
expense_closure_delegations
```

Campos principales:

```text
expense_id
delegate_user_id
delegated_by_user_id
delegated_by_email
created_at
revoked_at
revoked_by_user_id
revoked_by_email
```

Solo una fila puede estar activa (`revoked_at IS NULL`) por solicitud.

Cambiar delegado:

```text
fila activa anterior
→ revoked_at + revoked_by
→ flush
→ nueva fila activa
```

No se elimina el historial.

## Quién puede delegar

Únicamente el solicitante original.

El Administrador del sistema:

- puede cerrar/gestionar factura por excepción administrativa;
- no necesita delegación;
- no crea delegaciones ordinarias en nombre del solicitante.

El delegado:

- debe estar activo;
- no puede ser el propio solicitante;
- no puede ser una cuenta protegida de sistema;
- solo recibe autoridad sobre la solicitud delegada.

## API

```text
GET    /api/expenses/{request_id}/closure-delegation
PUT    /api/expenses/{request_id}/closure-delegation
DELETE /api/expenses/{request_id}/closure-delegation
```

### PUT

```json
{
  "delegate_user_id": 123
}
```

Solo solicitante original.

### DELETE

Revoca la delegación activa y conserva la fila histórica.

## Endpoints financieros

```text
POST /api/expenses/{request_id}/close
PUT  /api/expenses/{request_id}/invoice
```

Ambos autentican con `current_user` y llaman al resolver de recurso `can_manage_closure()`.

No usan `require_permission('requests:close')`.

## Dashboard

`CLOSE_REQUEST` aparece cuando la solicitud está `APPROVED` para:

```text
solicitante original
delegado activo
```

No aparece para un tercero solo porque tenga un permiso legacy.

El Administrador del sistema conserva la acción desde Solicitudes, pero no recibe todos los cierres como bandeja personal.

## Frontend

Mientras `ExpenseTable` siga en `main.jsx`, Vite conecta temporalmente las capacidades backend:

```text
x.can_close
x.can_delegate_close
```

Botones:

```text
APPROVED + can_close
→ Registrar factura y cerrar

CLOSED + can_close + factura
→ Corregir factura

can_delegate_close
→ Delegar cierre/factura
```

`frontend/src/closure-delegation.jsx` contiene el modal de selección/revocación.

## Migración 0005

```text
20260818_0005_closure_delegation.py
```

Cadena:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005
```

Además:

```text
permissions.code = requests:close
→ active = false
→ nombre legacy
```

El registro no se borra para conservar trazabilidad de asignaciones históricas.

## Pruebas manuales

1. Entrar como solicitante de una solicitud `APPROVED`.
2. Confirmar **Registrar factura y cerrar** y **Delegar cierre/factura**.
3. Delegar a otro usuario.
4. Entrar como delegado y confirmar **Registrar factura y cerrar**.
5. Confirmar que el delegado no puede cambiar/revocar la delegación.
6. Entrar como un tercero no delegado y confirmar que no tiene acción de cierre.
7. Revocar como solicitante y confirmar que el delegado pierde inmediatamente la acción.
8. Cerrar como solicitante/delegado/Admin del sistema.
9. En `CLOSED`, confirmar que solo esos actores pueden **Corregir factura**.
10. Verificar que reemplazar factura exige motivo y conserva la versión anterior.
