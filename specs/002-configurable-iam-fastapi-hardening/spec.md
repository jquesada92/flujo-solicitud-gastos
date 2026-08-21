# Spec 002 — IAM configurable y hardening FastAPI

**Estado:** Implementada y evolucionada por Spec 006/011  
**Constitución:** 2.13.0

## Objetivo

Autorizar desde capacidades persistidas y proteger la API independientemente de la presentación del frontend.

## IAM vigente

```text
Permission → Role ── 0..1 Group
               ↑
            User
```

Un usuario activo recibe `requests:read` como baseline. Los demás permisos ordinarios pueden llegar por Roles globales activos o por el Rol que ocupa dentro de un Grupo activo. `config:manage` es system-only.

Permisos:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

No forman parte del modelo operativo permisos directos a Usuario ni autorización por Cargo. Un Rol sin Grupo es válido y se considera global; un Rol pertenece como máximo a un Grupo.

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
