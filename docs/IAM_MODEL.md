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

## Modelo

```text
permissions
   ↑
role_permissions ← roles ← group_roles ← user_groups ← group_members ← users
                         ↖ user_role_assignments ← users
permissions ← user_permissions ← users
positions ← user_positions ← users
```

## Permisos iniciales

- `requests:read`
- `requests:create`
- `requests:approve`
- `requests:close`
- `config:manage`

## Fórmula

```text
effective_permissions(user) =
    direct permissions
  ∪ permissions from direct roles
  ∪ permissions from group roles
```

No hay DENY explícito en esta versión. La ausencia de ALLOW produce DENY.

## Cuenta técnica

`system_accounts` marca cuentas técnicas. `TECHNICAL_ADMIN` aplica una restricción defensiva adicional:

```text
{config:manage, requests:read}
```

Aunque la cuenta sea añadida a un grupo financiero o reciba un permiso directo por error, el servicio de IAM filtra esos permisos.

## Administración gráfica

`Configuración → Accesos` expone:

- Usuarios;
- Grupos;
- Roles;
- Permisos;
- Cargos.

Los permisos del producto son lectura/configuración de capacidades disponibles. La organización configura roles y asignaciones.

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

Las invitaciones de una votación representan el snapshot de participantes de esa ronda.

## Compatibilidad legacy

Los campos `role`, `title` y `can_*` aún existen en `users` por compatibilidad. En requests autenticados, `current_user()` deriva los `can_*` desde IAM para que código legacy no lea privilegios obsoletos.

Esta compatibilidad debe retirarse a medida que se extraigan las rutas del router monolítico y se migre el frontend.

## Evolución futura

Posibles extensiones, no incluidas actualmente:

- scopes por organización;
- scopes por Área/recurso;
- DENY explícito con precedencia;
- SSO/OIDC;
- SCIM;
- grupos jerárquicos;
- permisos temporales;
- aprobaciones de cambios IAM;
- auditoría IAM completa append-only.
