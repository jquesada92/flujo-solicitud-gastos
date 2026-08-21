# Historia funcional

Este archivo resume decisiones ya incorporadas sin redefinir el contrato vigente. Para implementación actual usar Constitución, `CURRENT_PRODUCT_CONTRACT.md` y Specs.

## 2026-08-21 — Roles globales y Grupos opcionales

- Grupo puede existir con cero Roles.
- Rol puede pertenecer a cero o un Grupo; sin Grupo es global.
- Usuario mantiene máximo un Rol por Grupo y puede acumular Roles globales ordinarios.
- Roles globales conceden sus Permisos sin crear membresía de Grupo.
- mover un Rol Global↔Grupo conserva asignaciones y reconstruye membresía derivada.
- Administrador del sistema se representa como Rol global técnico protegido, con `SystemAccount` como autoridad privilegiada.
- Constitución evoluciona a 2.12.0 y Alembic agrega `20260821_0004_allow_global_roles`.

## 2026-08-21 — Contrato organizacional consolidado

- Rol pertenece como máximo a un Grupo.
- Usuario tiene máximo un Rol por Grupo.
- membresía de Grupo se deriva del Rol agrupado del Usuario.
- Permisos se asignan a Roles, no a Usuarios.
- Cargo queda como metadato organizacional sin autoridad y con cardinalidad máxima de uno por Usuario.
- documentación normativa se consolidó inicialmente en Constitución 2.11.0.

## 2026-08-20 — UX de acceso y seguimiento

- Accesos pasó a edición staged con Guardar cambios.
- se eliminó la edición de permisos individuales.
- se agregó Acceso por grupo en la ficha del Usuario.
- nombres de Rol se sincronizan localmente después de guardar.
- Inicio quedó orientado al trabajo personal.
- Seguimiento quedó como vista separada de carga del equipo.
- rutas privadas redirigen a Login sin sesión.
- se eliminó polling sub-segundo y se agregó deduplicación/caché corta de GET.

## 2026-08-20 — Persistencia y despliegue

- base objetivo `ph_torre_delta`, schema `administracion`.
- baseline limpia `20260820_0001_initial_schema`.
- Neon pooled quedó compatible al retirar startup options de `search_path` y usar schema explícito.
- `expense_area` / `expense_category` quedaron como contrato nuevo del formulario/persistencia.

## 2026-08-20 — Solicitudes

- formulario Nueva solicitud depende de `requests:create`.
- corrección conserva SIMPLE/MULTI_QUOTE.
- Enviar a revisión interrumpe la ronda y devuelve al solicitante.
- cierre/factura se maneja por autoridad de recurso y puede delegarse por solicitud.

## 2026-08-18 — Hardening

- FastAPI modularizado por routers/capacidades.
- Settings centralizados, Argon2, JWT revocable/inactivo, CORS y rate limiting.
- correo configurable por ambiente.
- documentación pasa a formar parte del Definition of Done.
