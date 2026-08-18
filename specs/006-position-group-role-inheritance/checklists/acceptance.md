# Criterios de aceptación — Herencia de permisos por Cargo y Grupo

**Feature:** 006  
**Constitución:** 2.5.0

## Modelo IAM

- [x] Existe `position_roles` con unicidad `(position_id, role_id)`.
- [x] Cargo/Posición puede asociarse a múltiples Roles.
- [x] Un mismo Rol puede asociarse a múltiples Cargos y Grupos.
- [x] No existe autorización runtime por nombre/código específico de Cargo.

## Resolución efectiva

- [x] Permiso directo sigue siendo fuente válida.
- [x] Rol directo sigue siendo fuente válida.
- [x] Grupo → Rol → Permiso sigue siendo fuente válida.
- [x] Cargo → Rol → Permiso es nueva fuente válida.
- [x] Las fuentes se unen de forma aditiva.
- [x] Cargo inactivo no concede permisos.
- [x] Rol inactivo no concede permisos.
- [x] `requests:read` sigue siendo baseline universal para usuario activo.

## Workflow

- [x] `users_with_permission()` incorpora herencia por Cargo.
- [x] Un usuario con `requests:approve` por Cargo aparece como aprobador/votante elegible.
- [x] Un usuario con `requests:approve` por Grupo aparece como aprobador/votante elegible.
- [x] La cuenta técnica de producción sigue excluida de permisos financieros aunque tenga asignaciones organizacionales accidentales.
- [x] El solicitante sigue pudiendo excluirse de su propia ronda como regla intrínseca del workflow.

## API/UI

- [x] GET de Cargos devuelve `role_ids`.
- [x] Se puede asignar un Rol a un Cargo desde API canónica.
- [x] Se puede quitar un Rol de un Cargo desde API canónica.
- [x] No se puede asignar un Rol técnico `system_managed` a un Cargo.
- [x] Configuración → Accesos → Cargos permite seleccionar Roles heredados.
- [x] Configuración → Accesos → Grupos mantiene Roles + Miembros.
- [x] Usuarios explica que sus Cargos pueden heredar Roles.
- [x] Permisos efectivos muestra el origen `Cargo <nombre> → <rol>`.

## Migración

- [x] Alembic head pasa a `20260818_0004`.
- [x] `0004` crea `position_roles`.
- [x] `0004` importa una sola vez la configuración legacy de `access_profiles/users.title`.
- [x] La importación traduce `can_approve` a `requests:approve` a través de un Rol, no como autoridad runtime.
- [x] La migración reutiliza Cargos/Roles equivalentes si ya existen.
- [x] La migración excluye `system_accounts` de asignaciones organizacionales migradas.
- [ ] Smoke test de `0004` ejecutado contra PostgreSQL/Neon de preview o copia antes de producción.

## Caso productivo reportado

- [ ] Tesorero muestra `requests:approve` como permiso efectivo después del deploy.
- [ ] Vicepresidente muestra `requests:approve` como permiso efectivo después del deploy.
- [ ] Si Tesorero crea MULTI_QUOTE, Vicepresidente queda elegible para votar.
- [ ] Si Vicepresidente crea MULTI_QUOTE, Tesorero queda elegible para votar.
- [ ] Ya no aparece “No existe otro usuario activo con permiso de aprobación” cuando existe al menos otro aprobador efectivo.

## Pruebas automáticas

- [x] Existe `test_position_role_inheritance.py`.
- [x] Prueba positiva de Cargo → Rol → Permiso.
- [x] Prueba positiva simultánea de Grupo y Cargo.
- [x] Prueba negativa de Cargo inactivo.
- [x] Test de topología exige `0004` como único head.
- [ ] CI del head final verde.

## Documentación

- [x] Constitución actualizada a 2.5.0.
- [x] Spec 006 creada.
- [x] Plan 006 creado.
- [x] Acceptance 006 creado.
- [ ] README actualizado.
- [ ] PROMPT_RECONSTRUCCION actualizado.
- [ ] IAM_MODEL actualizado.
- [ ] FASTAPI_ARCHITECTURE actualizado.
- [ ] docs/README actualizado.
- [ ] HISTORY actualizado.
- [ ] CHANGELOG actualizado.
- [ ] PR #9 actualizado con el contrato final.
