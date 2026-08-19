# Criterios de aceptación — Configuración técnica vs gestión de Áreas

**Feature:** 009  
**Constitución:** 2.8.0

## IAM / backend

- [x] existe permiso activo `areas:manage`.
- [x] `config:manage` se trata como permiso system-only.
- [x] un usuario ordinario no obtiene `config:manage` efectivo aunque exista asignación directa/legacy.
- [x] `areas:manage` puede ser efectivo para usuario ordinario.
- [x] producción concede al System Admin `requests:read + areas:manage + config:manage` y excluye permisos financieros.
- [x] `/auth/me`/login exponen `is_system_account` calculado desde persistencia.
- [x] mutaciones de `/api/areas` requieren `areas:manage`.
- [x] registros inactivos de Áreas/Categorías requieren `areas:manage`.
- [x] rutas técnicas siguen detrás de `config:manage` y por tanto son system-only en runtime.

## Neutralidad organizacional

- [x] no existe autorización por nombre de Grupo/Cargo para `areas:manage`.
- [x] migración `0006` no asigna automáticamente acceso a Administración/Junta Directiva u otros nombres.
- [x] existe Rol neutral reutilizable `Gestor de áreas`.
- [ ] validar manualmente asociación del Rol a los grupos reales configurados por la organización.

## Frontend

- [x] el frontend usa `user.is_system_account` para configuración técnica.
- [x] **Usuarios** solo se muestra para System Admin.
- [x] **Organigrama** solo se muestra para System Admin.
- [x] **Accesos** solo se inyecta para System Admin.
- [x] **Áreas** se muestra para System Admin o usuario con `areas:manage`.
- [x] usuario con `areas:manage` no recibe acceso visual a Usuarios/Organigrama/Accesos.
- [x] usuario sin ninguna capacidad de configuración no recibe menú Configuración.
- [ ] validar manualmente menú System Admin.
- [ ] validar manualmente menú de usuario con `areas:manage`.
- [ ] validar manualmente usuario ordinario sin Configuración.

## Migración

- [x] existe Alembic `20260818_0006_area_management_permission.py`.
- [x] `0006` depende de `0005`.
- [x] `0006` crea/upserta `areas:manage`.
- [x] `0006` crea Rol `area-manager` sin asignarlo por nombre organizacional.
- [x] test de topología exige `0006` como único head.
- [ ] smoke `alembic upgrade head` en PostgreSQL local/preview.
- [ ] confirmar en DB después de deploy que `areas:manage.active=true`.

## Pruebas

- [x] `test_iam_api.py` cubre system-only config y `areas:manage` ordinario.
- [x] `test_frontend_configuration_access.py` protege separación de menú.
- [x] `test_migrations.py` protege `0006`.
- [ ] suite backend completa ejecutada localmente en head final.
- [ ] `npm run build` ejecutado localmente en head final.
- [ ] Docker build/smoke ejecutado localmente en head final.
- [ ] CI remoto verde cuando vuelva la cuota de GitHub Actions.

## Documentación

- [x] Constitución actualizada a 2.8.0.
- [x] Feature 009 spec/plan/checklist creados.
- [x] `docs/CONFIGURATION_ACCESS.md` creado.
- [x] `docs/IAM_MODEL.md` actualizado.
- [x] `docs/FASTAPI_ARCHITECTURE.md` actualizado.
- [x] `docs/CLASSIFICATION_MODEL.md` actualizado.
- [x] `docs/TERMINOLOGY.md` actualizado.
- [x] `docs/README.md` actualizado.
- [x] README principal actualizado.
- [x] PROMPT_RECONSTRUCCION actualizado.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [ ] PR #9 actualizado.