# Criterios de aceptación — Herencia de permisos por Cargo y Grupo

**Feature:** 006  
**Constitución vigente:** 2.9.0

## Modelo IAM

- [x] existe `position_roles` con unicidad `(position_id, role_id)`.
- [x] Cargo/Posición puede asociarse a múltiples Roles.
- [x] un mismo Rol puede asociarse a múltiples Cargos y Grupos.
- [x] no existe autorización runtime por nombre/código específico de Cargo.

## Resolución efectiva

- [x] permiso directo es fuente válida.
- [x] Rol directo es fuente válida.
- [x] Grupo → Rol → Permiso es fuente válida.
- [x] Cargo → Rol → Permiso es fuente válida.
- [x] fuentes se acumulan.
- [x] Cargo/Role inactivo no concede permisos.
- [x] `requests:read` es baseline para usuario activo.
- [x] `config:manage` se filtra para usuarios ordinarios por política system-only.
- [x] `config:read` y `areas:manage` pueden heredarse por las fuentes IAM ordinarias.

## Workflow

- [x] `users_with_permission()` incorpora herencia por Cargo.
- [x] aprobador por Cargo/Grupo es elegible según reglas del workflow.
- [x] cuenta técnica de producción respeta exclusiones financieras.
- [x] solicitante puede excluirse de su propia ronda.

## API / Accesos

- [x] GET de Cargos devuelve `role_ids`.
- [x] se puede asignar/quitar Rol de Cargo desde API canónica.
- [x] no se puede asignar Rol técnico `system_managed` de forma impropia.
- [x] **Accesos → Cargos** permite Roles heredados.
- [x] **Accesos → Grupos** mantiene Roles + Miembros.
- [x] **Accesos → Usuarios** administra Cargos del usuario.
- [x] Usuarios es una pestaña interna de Accesos, no una pantalla independiente de Configuración.
- [x] permisos efectivos muestran origen `Cargo <nombre> → <rol>`.

## Migración

- [x] `0004` crea `position_roles`.
- [x] `0004` importa configuración legacy una sola vez.
- [x] importación traduce flags legacy a Roles/Permisos, no a reglas runtime por nombre.
- [x] migración excluye `system_accounts` de asignaciones organizacionales migradas.
- [x] cadena global del proyecto continúa hasta `0008`.
- [ ] ejecutar smoke Alembic contra PostgreSQL final.

## Pruebas automáticas

- [x] existe `test_position_role_inheritance.py`.
- [x] prueba Cargo → Rol → Permiso.
- [x] prueba Grupo + Cargo simultáneos.
- [x] prueba Cargo inactivo.
- [ ] suite backend completa ejecutada localmente en head final.
- [ ] `npm run build` ejecutado localmente en head final.

## Documentación

- [x] Constitución vigente 2.9.0.
- [x] Spec 006 alineada con Accesos.
- [x] Plan 006 alineado con modelo vigente.
- [x] Acceptance 006 actualizado.
- [x] README actualizado.
- [x] PROMPT_RECONSTRUCCION actualizado.
- [x] IAM_MODEL actualizado.
- [x] FASTAPI_ARCHITECTURE actualizado.
- [x] TERMINOLOGY actualizado.
- [x] docs/README actualizado.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [x] Feature 011 documenta la consolidación de navegación.
