# Changelog

## 2.15.0 — 2026-08-21

- listas GUI activas para Usuario, Área, Rol y Grupo;
- recuperación backend de entidades inactivas por llave de negocio;
- autocompletado confirmado y reactivación con el mismo ID;
- preservación integral del historial de auditoría.

## 2.14.0 — 2026-08-21

- historial temporal de actividad para Usuarios, Áreas, Roles y Grupos;
- migración `20260821_0005_activity_periods` con backfill y restricciones;
- migración `20260821_0006_period_snapshot_values` con instantáneas JSON;
- migración `20260821_0007_period_audit_metadata` con actor, timestamp y diferencias;
- migración `20260821_0008_normalize_period_timestamps` para vigencias UTC;
- registro transaccional de altas y toda modificación relevante, incluidas relaciones IAM;
- pruebas unitarias y PostgreSQL local para integridad y períodos múltiples.

## 2026-08-21 — validación PostgreSQL y escenarios locales

- Constitución 2.13.0 formaliza población, voto y resolución de MULTI_QUOTE;
- se corrige generación de identificadores para calificar `category_counters` con el schema de aplicación;
- los Enum ORM heredan `administracion`, evitando casts PostgreSQL contra tipos inexistentes en `public`;
- Docker local fuerza correo `console` por defecto;
- `demo_monitoring` se alinea con Roles IAM explícitos y correos válidos;
- el sembrador crea escenarios persistentes SIMPLE y MULTI_QUOTE, incluida votación abierta y voto parcial;
- se documentan pruebas adversas, límites, credenciales demo y diferencia entre fixtures unitarios y datos visibles;
- suite local: 161 pruebas exitosas y build frontend exitoso.

## 2026-08-21

### IAM / contrato 2.12.0

- un Grupo puede existir con cero Roles;
- un Rol puede pertenecer a cero o un Grupo; un Rol sin Grupo es global;
- un Usuario mantiene máximo un Rol por Grupo y puede tener varios Roles globales ordinarios;
- los Roles globales participan en permisos efectivos sin crear `GroupMember`;
- quitar un Rol de un Grupo lo convierte en global sin borrar asignaciones de Usuario;
- agrupar Roles se rechaza si produciría dos Roles del mismo Grupo para un Usuario;
- `Administrador del sistema` se representa como Rol global técnico protegido, mientras `SystemAccount` conserva la autoridad de privilegios;
- nueva revisión Alembic `20260821_0004_allow_global_roles`;
- Accesos separa **Acceso por grupo** y **Roles globales**;
- se corrige la prueba obsoleta de Seguimiento para usar `_group_role_names`.

### Documentación / contrato 2.11.0 → 2.12.0

- se actualiza Constitución, README y prompt maestro al modelo vigente;
- se reescriben reglas IAM en Specs 006/011 y documentación de Accesos;
- se mantienen `docs/CURRENT_PRODUCT_CONTRACT.md` y `docs/FRONTEND_RUNTIME.md` como mapas de contrato/runtime;
- se alinean IAM, Configuración, Terminología, Seguimiento, Neon, FastAPI, Correo, Clasificación, Correcciones y Cierre;
- se eliminan de documentación normativa modelos, ramas y cadenas de migración ya sustituidos.

### Cargo

- contrato funcional: máximo un Cargo por Usuario;
- Cargo es metadato organizacional y no concede acceso;
- revisión Alembic `20260821_0003_single_user_position`.

## 2026-08-20

### IAM

- un Rol puede pertenecer como máximo a un Grupo;
- un Usuario tiene máximo un Rol por Grupo;
- membresía de Grupo derivada;
- permisos solo en Roles;
- edición de acceso staged con Guardar cambios;
- actualización inmediata del nombre del Rol después de guardar.

### UX

- Inicio personal;
- nueva pantalla Seguimiento de usuarios;
- Nueva solicitud visible con `requests:create`;
- redirect a Login para rutas privadas sin sesión;
- eliminación de polling agresivo y gobernador global de GET.

### Datos / despliegue

- `expense_area` y `expense_category` como contrato canónico;
- Neon pooled compatible sin startup `search_path`;
- `DATABASE_SCHEMA=administracion` explícito;
- baseline limpia y revisiones incrementales.

## 2026-08-18/19

- hardening FastAPI/IAM;
- seguimiento y acciones pendientes;
- revisión/corrección con ownership por recurso;
- delegación de cierre/factura;
- gestión Área/Categoría y lectura de Configuración;
- notificaciones de creación/cambio de Cargo con permisos efectivos.
