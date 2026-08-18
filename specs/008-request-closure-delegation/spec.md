# Especificación funcional — Cierre/factura por propiedad o delegación

**Feature:** 008  
**Constitución:** 2.7.0

## Objetivo

Separar el cierre y la factura de los permisos globales IAM. La responsabilidad pertenece a cada solicitud y puede delegarse explícitamente por su solicitante.

Modelo:

```text
Solicitud APPROVED/CLOSED
        ↓
solicitante original
OR Administrador del sistema
OR delegado activo de esa solicitud
        ↓
registrar factura / cerrar / corregir factura
```

## F-008-01 — Autoridad de cierre/factura

Solo pueden registrar la factura final, cerrar o reemplazar/corregir la factura:

1. solicitante original;
2. Administrador del sistema identificado mediante `system_accounts`;
3. usuario activo con delegación vigente creada por el solicitante para esa solicitud.

No autorizan por sí mismos:

- `requests:close`;
- `requests:create`;
- `requests:approve`;
- `config:manage`;
- Grupo;
- Rol;
- Cargo/Posición;
- `UserRole`/`can_*` legacy.

## F-008-02 — Capacidad `can_close`

`GET /api/expenses` devuelve `can_close` por solicitud y usuario.

Para `APPROVED` o `CLOSED`:

```text
can_close = requester OR system_account OR active_delegate
```

Fuera de esos estados, `can_close=false`.

La UI consume esa capacidad; los endpoints vuelven a validar siempre.

## F-008-03 — Delegación

Solo el solicitante original puede:

- crear delegación;
- cambiar delegado;
- revocar delegación.

Una delegación:

- pertenece a una sola solicitud;
- apunta a un usuario activo;
- no puede apuntar al propio solicitante;
- no puede apuntar a una cuenta protegida `system_accounts`;
- no concede autoridad sobre otras solicitudes;
- no convierte al delegado en aprobador ni administrador.

## F-008-04 — Una sola delegación activa

Solo puede existir una delegación activa por solicitud.

Cambiar de delegado:

1. marca la delegación anterior con `revoked_at`, `revoked_by_user_id`, `revoked_by_email`;
2. persiste el cambio antes de crear la nueva fila activa;
3. conserva ambas filas como historial.

No se borra una delegación histórica.

## F-008-05 — Candidatos

El selector de delegación muestra usuarios:

- activos;
- distintos del solicitante;
- que no sean cuentas de sistema protegidas.

El delegado no necesita un permiso IAM adicional para ejercer la responsabilidad delegada.

## F-008-06 — Tarea contextual

Cuando la solicitud está `APPROVED`, `CLOSE_REQUEST` pertenece a:

- solicitante original;
- delegado activo, si existe.

El Administrador del sistema conserva la capacidad administrativa desde Solicitudes, pero no recibe automáticamente todas las solicitudes aprobadas en su Dashboard.

Un usuario que solo posee `requests:close` legacy no recibe `CLOSE_REQUEST`.

## F-008-07 — Factura y cierre

### APPROVED

Un actor con `can_close=true` puede:

- cargar PDF/JPEG/PNG/WEBP como factura;
- agregar notas de cierre;
- cambiar la solicitud a `CLOSED`;
- registrar `closed_at` y `closed_by`.

### CLOSED

Un actor con `can_close=true` puede reemplazar la factura vigente.

El reemplazo:

- exige motivo de al menos 3 caracteres;
- conserva la factura anterior como `INVOICE_REPLACED`;
- crea la nueva `INVOICE`;
- registra `InvoiceChangeEvent` con actor y motivo.

## F-008-08 — UI

En Solicitudes:

- **Registrar factura y cerrar** aparece solo con `x.can_close` y estado `APPROVED`;
- **Corregir factura** aparece solo con `x.can_close`, estado `CLOSED` y factura vigente;
- **Delegar cierre/factura** aparece solo con `x.can_delegate_close`;
- para solicitudes cerradas la etiqueta puede ser **Delegar factura**.

La delegación abre un modal con:

- delegado actual;
- selector de candidatos;
- **Delegar/Cambiar delegado**;
- **Revocar delegación**.

## F-008-09 — `requests:close` legacy

La migración `0005` conserva el registro histórico `requests:close`, pero lo marca `active=false` y lo renombra como legacy.

Runtime de cierre/factura no consulta `requests:close`.

## F-008-10 — Migración

Alembic:

```text
20260818_0005_closure_delegation.py
```

crea `expense_closure_delegations` con:

- `expense_id`;
- `delegate_user_id`;
- `delegated_by_user_id`;
- `delegated_by_email`;
- `created_at`;
- `revoked_at`;
- `revoked_by_user_id`;
- `revoked_by_email`.

Un índice único parcial garantiza una sola fila con `revoked_at IS NULL` por solicitud.

## Seguridad

- backend authoritative;
- delegar no usa Cargo/Grupo/Rol como atajo;
- el solicitante es identificado por `requested_by`;
- la cuenta técnica por `system_accounts`;
- un delegado inactivo no puede ejercer autoridad;
- la UI no reconstruye la autorización desde `canClose` de sesión.

## Fuera de alcance

- delegar a varios usuarios simultáneamente;
- delegación por Grupo/Cargo en lugar de usuario concreto;
- delegación global para todas las solicitudes futuras;
- transferir la propiedad original de la solicitud;
- modificar fórmula de aprobación/votación;
- enviar notificaciones específicas de delegación (puede añadirse después sin cambiar la regla de autorización).
