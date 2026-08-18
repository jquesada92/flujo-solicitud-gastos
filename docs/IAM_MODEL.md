# Modelo IAM configurable

## Objetivo

Permitir que cada organización configure su estructura de acceso desde la interfaz gráfica sin hardcodear nombres, cargos o correos en el backend.

## Conceptos

### Usuario

Cuenta autenticable del sistema.

### Grupo

Conjunto de usuarios con una responsabilidad común. Ejemplos como `Junta Directiva`, `Finance` o `Procurement` son datos del cliente, no conceptos del código.

### Rol

Conjunto reutilizable de permisos.

### Permiso

Capacidad atómica implementada por el producto. El permiso autoriza; el nombre de rol/grupo/cargo no.

### Cargo / Posición

Metadato descriptivo de estructura organizacional. Puede representar Presidente, Gerente, Analista, Director, etc. **No concede permisos.**

### Cuenta de sistema

Identidad técnica registrada en `system_accounts`. Su política puede diferir por ambiente sin depender de email, cargo ni `UserRole` legacy.

## Modelo

```text
permissions
   ↑
role_permissions ← roles ← group_roles ← user_groups ← group_members ← users
                         ↖ user_role_assignments ← users
permissions ← user_permissions ← users
positions ← user_positions ← users
system_accounts ← users
```

## Permisos iniciales

- `requests:read`
- `requests:create`
- `requests:approve`
- `requests:close`
- `config:manage`

## Fórmula para usuarios operativos

```text
effective_permissions(user) =
    direct permissions
  ∪ permissions from direct roles
  ∪ permissions from group roles
```

No hay DENY explícito en esta versión. La ausencia de ALLOW produce DENY.

## Política de `TECHNICAL_ADMIN`

La cuenta técnica no usa la fórmula normal como autoridad final. `iam_service.py` aplica una política ambiental explícita sobre el catálogo de permisos activos.

### Producción

Cuando:

```env
ENVIRONMENT=production
```

la cuenta técnica obtiene únicamente:

```text
config:manage
requests:read
```

La política filtra cualquier asignación accidental de:

```text
requests:create
requests:approve
requests:close
```

y la excluye de poblaciones financieras para esos permisos.

### No producción

Para cualquier `ENVIRONMENT` distinto de `production`, incluidos `local`, `development`, `dev`, `test`, `staging` y `preview`:

```text
TECHNICAL_ADMIN effective permissions = todos los permisos activos
```

La cuenta puede probar end-to-end:

- creación/corrección;
- consulta;
- aprobación;
- votación de cotizaciones;
- carga/reemplazo de factura;
- cierre;
- configuración.

También puede aparecer en `users_with_permission('requests:approve')` fuera de producción.

Esta elevación no se persiste como permisos financieros en el rol system-managed. Cambiar el runtime a `ENVIRONMENT=production` restablece la segregación sin migración de datos.

## Ambiente vs hosting

`Settings` mantiene dos conceptos separados:

```text
is_production_environment
→ solo ENVIRONMENT=production
→ gobierna autorización de cuenta técnica

is_production
→ production o runtime alojado como Render
→ gobierna validaciones estrictas de secretos/CORS
```

Por tanto un preview alojado puede exigir secretos fuertes y, a la vez, permitir pruebas funcionales completas si `ENVIRONMENT` no es `production`.

## Contrato de permisos del usuario actual

El backend expone:

```text
permission_codes
```

como lista canónica de permisos efectivos.

Compatibilidad temporal:

```text
can_request   = requests:create
can_approve   = requests:approve
can_view      = requests:read
can_configure = config:manage
can_close     = requests:close
```

`apply_effective_permissions_to_user()` deriva estos valores. No se usan como fuente de autorización.

## Administración gráfica

`Configuración → Accesos` expone:

- Usuarios;
- Grupos;
- Roles;
- Permisos;
- Cargos;
- asignaciones;
- permisos efectivos y su origen.

Los permisos del producto son lectura/configuración de capacidades disponibles. La organización configura roles y asignaciones.

Para cuentas técnicas, `permission_sources()` identifica si el acceso proviene de:

```text
Política de cuenta técnica (producción)
```

o:

```text
Acceso de prueba de cuenta técnica (no producción)
```

## APIs

Base `/api/iam`:

```text
GET  /me/permissions
GET  /permissions
GET  /roles
POST /roles
PATCH /roles/{id}
GET  /groups
POST /groups
PATCH /groups/{id}
PUT/DELETE /groups/{group_id}/roles/{role_id}
PUT/DELETE /groups/{group_id}/members/{user_id}
PUT/DELETE /users/{user_id}/roles/{role_id}
PUT/DELETE /users/{user_id}/permissions/{code}
GET /users/{user_id}/effective-permissions
GET/POST/PATCH /positions...
```

Base `/api/iam/users` ofrece administración neutral de usuarios y sus asignaciones.

## Participación en workflows

Aprobadores/votantes se descubren por `requests:approve` usando `users_with_permission()`.

No se consulta:

- `UserRole.APPROVER`;
- `can_approve` persistido;
- cargo Presidente/Tesorero/etc.;
- grupo con nombre particular.

Comportamiento de cuenta técnica:

- producción: excluida de poblaciones financieras;
- no producción: puede participar para pruebas si el flujo no la excluye por otra razón, por ejemplo ser el solicitante.

Las invitaciones de una votación representan el snapshot de participantes de esa ronda.

## Compatibilidad legacy

Los campos `role`, `title` y `can_*` aún existen en `users` por compatibilidad. En requests autenticados, `current_user()` deriva los `can_*` desde IAM.

`UserOut.permission_codes` y `UserOut.can_close` permiten migrar el frontend hacia capacidades reales.

El frontend monolítico todavía contiene bypasses visuales legacy como `user.role === "ADMIN"` y un `canClose={true}`. No son autoridad y deben retirarse en la modularización del frontend.

## Evolución futura

Posibles extensiones:

- scopes por organización;
- scopes por Área/recurso;
- DENY explícito con precedencia;
- SSO/OIDC;
- SCIM;
- grupos jerárquicos;
- permisos temporales;
- aprobaciones de cambios IAM;
- auditoría IAM completa append-only.
