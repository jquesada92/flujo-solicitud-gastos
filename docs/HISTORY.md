# Historia funcional

## 2026-08-25 — instructivo para usuarios finales

- Se incorpora una guía operativa separada de la documentación técnica para
  Solicitantes y miembros de Junta Directiva.
- El instructivo cubre primer ingreso, solicitudes sencillas y múltiples,
  aprobación, votación, revisión, corrección, cierre, factura, delegación y
  problemas frecuentes sin redefinir permisos ni estados.

## 2026-08-25 — guardrails de IA sincronizados

- La política operativa explicita que las divergencias de código no pueden
  rebajar Constitución, Specs ni contrato.
- Los cupos de Rol, herencia aditiva, asignaciones múltiples y enlaces de
  restablecimiento quedan protegidos en `AGENTS.md` con sus excepciones y gates.
- La política documental agrega una matriz de impacto y la prueba contractual
  detecta expectativas Alembic obsoletas aunque el head nuevo figure en otra
  sección.

## 2026-08-25 — cupo opcional de Usuarios activos por Rol

- La Constitución evoluciona a 2.18.0.
- Un Rol puede permanecer ilimitado o definir un máximo entero positivo de
  Usuarios activos asignados.
- Usuarios inactivos conservan su asignación sin ocupar cupo; asignación y
  reactivación se rechazan cuando el Rol está lleno.
- FastAPI bloquea los Roles antes de contar y no permite reducir el máximo por
  debajo de la ocupación activa.
- Accesos incorpora el control staged, ocupación visible y opciones “sin cupo”.
- Alembic agrega `20260825_0011_role_user_limit` y conserva ilimitados los Roles
  existentes.

## 2026-08-24 — restablecimiento seguro de contraseña

- La Constitución evoluciona a 2.17.0.
- El Administrador del sistema puede enviar desde Accesos un enlace confirmado a
  un Usuario activo no técnico sin generar ni conocer su contraseña.
- Cada emisión reemplaza las anteriores, dura 30 minutos por defecto y no cambia
  contraseña, `must_change_password` o sesiones mientras no se consuma.
- El consumo público almacena Argon2, revoca sesiones, invalida enlaces y vuelve
  al Login sin auto-login.
- El correo usa un template sin contraseña; un fallo de entrega revierte la
  emisión y la auditoría no conserva token, contraseña ni hash.
- Alembic agrega `20260824_0010_password_reset_links` para persistir la versión
  vigente de los enlaces.

## 2026-08-24 — Roles visibles en tarjetas de Usuario

- La lista de Usuarios en Accesos muestra debajo del correo todos los Roles persistidos, omite la línea sin asignaciones y distingue los Roles inactivos conservados.

## 2026-08-24 — documentación operativa verificable

- Se agregó una política raíz para que agentes automatizados trabajen solo dentro del alcance autorizado y preserven ramas, cambios locales, secretos, respaldos y datos.
- Los runbooks distinguen tests SQLite, PostgreSQL local y validación productiva no mutante; un health check ya no se presenta como prueba de identidad del release.
- La guía Neon distingue pool de runtime y conexión directa de migración, incluida la limitación actual de una sola `DATABASE_URL`.
- Los ejemplos locales dejaron de recomendar SMTP real y variables que el runtime ignora.
- La UI de Accesos conserva un contrato responsive desde 320 px.
- La regresión del selector único de Rol y los dumps ya versionados quedaron como bloqueos visibles que requieren remediación independiente.

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
