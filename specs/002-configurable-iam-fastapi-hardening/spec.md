# Especificación funcional — IAM configurable y hardening FastAPI

**Feature:** 002-configurable-iam-fastapi-hardening  
**Constitución vigente:** 2.9.0  
**Estado:** Implementada y evolucionada por Features 005–011.

## Objetivo

Mantener autorización configurable desde base de datos, sin roles/cargos/nombres hardcodeados, y un backend FastAPI modular, seguro, testeable y portable.

## Modelo IAM vigente

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ baseline requests:read
       ↘ capacidades/delegaciones por recurso
```

Persistencia:

```text
permissions
roles
role_permissions
user_groups
group_members
group_roles
user_role_assignments
user_permissions
positions
user_positions
position_roles
system_accounts
```

## Permisos vigentes

| Código | Capacidad |
| --- | --- |
| `requests:read` | Seguimiento universal; baseline para usuarios activos |
| `requests:create` | Crear nuevas solicitudes |
| `requests:approve` | Aprobar, rechazar, votar y enviar a revisión cuando corresponda |
| `areas:manage` | Administrar Área + Categoría |
| `config:read` | Consultar Configuración en modo solo lectura |
| `config:manage` | Administración técnica system-only |

`requests:close` es un registro legacy inactivo. **No** autoriza cierre/factura.

## Resolución de acceso

Para usuario activo ordinario:

```text
effective_permissions =
    {requests:read}
  ∪ direct_user_permissions
  ∪ direct_role_permissions
  ∪ group_role_permissions
  ∪ position_role_permissions
  - {config:manage}
```

La ausencia de un permiso mutable produce DENY.

`config:manage` solo es efectivo para cuentas persistidas en `system_accounts`.

## Cargo/Posición

La afirmación inicial de Feature 002 de que Cargo era solo metadata fue evolucionada por Feature 006.

Estado vigente:

```text
Cargo/Posición → Rol → Permiso
```

El nombre del Cargo nunca autoriza. Solo importan relaciones persistidas.

## Configuración gráfica

La consola canónica es:

```text
Configuración → Accesos
```

Feature 011 consolidó Usuarios/Personas y Organigrama dentro de Accesos.

Accesos permite:

- crear/activar/inactivar Usuarios;
- crear/editar Grupos;
- administrar miembros;
- crear/editar Roles;
- asignar Permisos a Roles;
- crear/editar Cargos/Posiciones;
- asignar Roles a Grupos y Cargos;
- asignar Grupos/Cargos/Roles/Permisos a Usuarios;
- visualizar permisos efectivos y fuentes.

Un actor con `config:read` reutiliza esta experiencia en modo solo lectura.

## Política de cuenta técnica por ambiente

Una cuenta `TECHNICAL_ADMIN` se identifica por `system_accounts`.

### Producción

Permisos IAM máximos actuales:

```text
requests:read
areas:manage
config:read
config:manage
```

No puede crear solicitudes ni participar en aprobación/votación.

Sí conserva excepciones administrativas **por recurso** para:

```text
cancelar
corregir / reenviar
gestionar cierre/factura
```

Estas excepciones no son permisos financieros globales.

### No producción

Puede recibir todos los permisos atómicos activos para pruebas E2E, además de las capacidades administrativas por recurso.

`RENDER=true` no sustituye `ENVIRONMENT=production`.

## Capacidades por recurso

Features posteriores retiraron ciertas mutaciones del IAM global:

```text
can_cancel
= estado cancelable AND (requester OR system_accounts)

can_correct
= estado corregible AND (requester OR system_accounts)

can_close
= APPROVED/CLOSED AND (requester OR system_accounts OR delegado activo)

can_delegate_close
= requester original
```

Por tanto:

- `requests:create` no permite corregir solicitudes ajenas;
- `requests:approve` no permite editarlas;
- `requests:close` no concede cierre;
- `config:manage` no reemplaza reglas de propiedad ordinarias.

## Solicitudes / workflow

### Creación

Nueva solicitud requiere `requests:create`.

### Aprobación / votación

Participantes se resuelven mediante:

```text
users_with_permission('requests:approve')
```

incluyendo permiso directo, Rol directo, Grupo→Rol y Cargo→Rol.

### Corrección

Solo solicitante original o Administrador del sistema. Mantiene invariant:

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

### Cierre/factura

Autorización por solicitud según `can_close`; no por `requests:close`.

## Contrato de sesión/UI

`UserOut` expone:

```text
permission_codes
is_system_account
```

Aliases `can_*` de sesión pueden permanecer temporalmente por compatibilidad, pero no autorizan backend.

## FastAPI

- configuración con `pydantic-settings`;
- `get_db()` por request;
- `APIRouter` por dominio/capacidad;
- modelos SQLAlchemy en `models/`;
- schemas reutilizables en `schemas/`;
- lógica reusable en `services/`;
- Argon2 para nuevos hashes y compatibilidad PBKDF2;
- Alembic antes de iniciar ASGI;
- lifespan sin DDL/backfills;
- response models explícitos;
- tests `TestClient` para autorización crítica.

## Portabilidad Docker

- scripts Linux en LF;
- `.gitattributes` protege `*.sh`;
- Docker normaliza CRLF defensivamente;
- bootstrap canónico: `python -m scripts.bootstrap_admin`;
- frontend espera healthcheck del backend.

## Migraciones vigentes

La cadena original de Feature 002 evolucionó. Estado actual:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

Puntos principales:

```text
0000 baseline
0001 IAM foundation
0002 system_accounts
0003 repair MULTI_QUOTE
0004 position_roles
0005 closure delegation / requests:close legacy
0006 areas:manage
0007 config:read
0008 expense_area / expense_category
```

## Clasificación actual

Nuevo código usa:

```text
expense_area
expense_category
```

No usar `expense_type` / `expense_subcategory` como contrato nuevo.

## Compatibilidad temporal

Pueden permanecer:

- `UserRole`;
- `can_*` legacy;
- `title`;
- `/api/users` legacy;
- `AccessProfile`;
- `BOARD_CODES`;
- `main.jsx` y bridges de compatibilidad.

No son autoridad de autorización ni arquitectura objetivo.

## Relación con features posteriores

- Feature 003: invariant de corrección.
- Feature 005: seguimiento universal/tareas contextuales.
- Feature 006: Cargo→Rol→Permiso.
- Feature 007: propiedad de corrección / Enviar a revisión.
- Feature 008: cierre por propiedad/delegación.
- Feature 009: `areas:manage`, `config:read`, `config:manage` system-only.
- Feature 010: notificaciones de Cargo/permisos.
- Feature 011: Accesos como única superficie y navegación del shell.

Ante discrepancia, prevalecen Constitución 2.9.0 y la feature posterior más específica.
