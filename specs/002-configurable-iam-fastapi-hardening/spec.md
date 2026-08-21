# Spec 002 — IAM configurable y hardening FastAPI

**Estado:** Implementada y evolucionada por Spec 006/011  
**Constitución:** 2.11.0

## Objetivo

Autorizar desde capacidades persistidas y proteger la API independientemente de la presentación del frontend.

## IAM vigente

```text
Permission → Role → Group
               ↑
            User
```

Un usuario activo recibe `requests:read` como baseline. Los demás permisos ordinarios llegan por el Rol que ocupa dentro de un Grupo activo. `config:manage` es system-only.

Permisos:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

No forman parte del modelo operativo permisos directos a Usuario, Roles sin Grupo ni autorización por Cargo.

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

Se identifica mediante `system_accounts`. En producción su política IAM es `requests:read + areas:manage + config:manage` y no participa en aprobación/votación.
