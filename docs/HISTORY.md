# Historia funcional

## 2026-08-24 — herencia aditiva de Permisos por Grupo

- La Constitución evoluciona a 2.16.0.
- Los Grupos pueden aportar Permisos heredables a todos sus Roles activos.
- Un Rol agrupado conserva sus Permisos propios y suma los del Grupo; la ausencia a nivel de Rol hereda y no existe `DENY`.
- Editar o desvincular el Grupo conserva `RolePermission`; `GroupMember` continúa siendo una proyección sin autoridad propia.
- `config:manage` permanece reservado a `system_accounts`.
- Alembic agrega `20260824_0009_group_permission_inheritance` sin backfill de grants para no cambiar accesos existentes y normaliza `permission_codes` en las instantáneas temporales abiertas.

## 2026-08-21 — recuperación segura de entidades inactivas

- La Constitución evoluciona a 2.15.0.
- Usuario, Área, Rol y Grupo desaparecen de la GUI al inactivarse.
- Los formularios recuperan ID y datos por cédula, código o nombre y reactivan sin duplicar.
- La reactivación conserva y extiende el historial temporal auditado.

## 2026-08-21 — períodos temporales de actividad

- La Constitución evoluciona a 2.14.0.
- Usuario, Área, Rol y Grupo obtienen historial de períodos activos con llave propia.
- Crear abre el período desde `created_at`; desactivar cierra y reactivar abre una nueva fila.
- La migración `20260821_0005_activity_periods` rellena entidades existentes y evita dos períodos abiertos.
- `20260821_0006_period_snapshot_values` agrega instantáneas JSON y versiona cada cambio, incluidos Usuario→Rol y Rol→Grupo.
- `20260821_0007_period_audit_metadata` identifica actor, timestamp y diferencias anterior/nuevo de cada versión.
- `20260821_0008_normalize_period_timestamps` normaliza vigencias y eventos a timestamps UTC con zona horaria.

## 2026-08-21 — validación local contra PostgreSQL real

- La Constitución evoluciona a 2.13.0 para formalizar votaciones MULTI_QUOTE y persistencia PostgreSQL runtime.
- La validación Docker reveló y corrigió dos diferencias que SQLite no detectaba: SQL crudo sin schema y Enum ORM sin herencia de schema.
- El entorno local quedó protegido con correo en modo console.
- El sembrador persistente se actualizó al IAM por Roles y agrega solicitudes SIMPLE y MULTI_QUOTE visibles.
- Las votaciones demo cubren ronda abierta, múltiples opciones y voto parcial.

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
- En esa consolidación se eliminaron los Permisos directos a Usuarios; desde 2.16.0 los grants se configuran como propios de Rol o heredables de Grupo.
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
