# Spec 002 — IAM configurable y hardening FastAPI

**Estado:** Implementada y evolucionada por Spec 006/011  
**Constitución:** 2.16.0

## Objetivo

Autorizar desde capacidades persistidas y proteger la API independientemente de la presentación del frontend.

## IAM vigente

```text
Permission propia    → Role ── 0..1 Group ← Permission heredable
                          ↑
                         User
```

Un usuario activo recibe `requests:read` como baseline. Los demás permisos ordinarios pueden llegar como Permisos propios de Roles globales activos o, para cada Rol agrupado activo dentro de un Grupo activo, como la unión `RolePermission ∪ GroupPermission`. `config:manage` es system-only.

Permisos:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

No forman parte del modelo operativo permisos directos a Usuario ni autorización por Cargo o por `GroupMember`. Un Rol sin Grupo es válido y se considera global; un Rol pertenece como máximo a un Grupo.

La herencia es exclusivamente aditiva: un Rol conserva sus Permisos propios y suma los de su Grupo. Un checkbox propio ausente no niega un Permiso heredado y no existe estado `DENY`. Editar el Grupo o desvincular el Rol no elimina `RolePermission`; al quedar global, el Rol pierde solo la herencia del Grupo.

## Seguridad FastAPI

- Settings centralizados.
- Argon2 para contraseñas nuevas; verificación compatible con hashes anteriores cuando aplique.
- JWT con `session_version`, expiración e inactividad.
- `must_change_password` restringe operación normal.
- CORS explícito.
- rate limiting por usuario autenticado.
- respuestas API con headers de no-cache y seguridad.
- backend revalida toda mutación.
- migraciones fuera de lifespan.

## Cuenta técnica

Se identifica mediante `system_accounts`. El Rol técnico `system-administrator` es global y `system_managed`, pero no sustituye la política protegida. En producción la política IAM efectiva es `requests:read + areas:manage + config:manage` y la cuenta técnica no participa en aprobación/votación.
