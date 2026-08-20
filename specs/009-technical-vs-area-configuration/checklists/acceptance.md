# Criterios de aceptación — Configuración técnica vs gestión de Áreas

**Feature:** 009  
**Constitución vigente:** 2.9.0  
**Evolución:** la navegación de Usuarios/Organigrama fue supersedida por Feature 011.

## IAM / backend

- [x] existe permiso activo `areas:manage`.
- [x] `config:manage` se trata como permiso system-only.
- [x] usuario ordinario no obtiene `config:manage` efectivo por asignación legacy/directa/heredada.
- [x] `areas:manage` puede ser efectivo para usuario ordinario.
- [x] existe `config:read` como permiso de lectura configurable.
- [x] `config:read` no concede mutaciones.
- [x] `/auth/me`/login exponen `is_system_account` desde persistencia.
- [x] mutaciones de `/api/areas` requieren `areas:manage`.
- [x] rutas técnicas de escritura continúan bajo política system-only.

## Neutralidad organizacional

- [x] no existe autorización por nombre de Grupo/Cargo para `areas:manage`.
- [x] `0006` no asigna acceso a Administración/Junta Directiva por nombre.
- [x] existe Rol neutral `Gestor de áreas`.
- [x] `0007` incorpora `config:read` / Visor de configuración sin autorización runtime por nombres.
- [ ] validar manualmente asociaciones reales configuradas por la organización.

## Frontend vigente

- [x] frontend usa `user.is_system_account` para identidad técnica.
- [x] **Usuarios/Personas** ya no se muestra como entrada independiente.
- [x] **Organigrama** ya no se muestra como entrada independiente.
- [x] **Accesos** es la superficie consolidada de Usuario/IAM.
- [x] `config:read` permite Accesos en modo solo lectura.
- [x] Áreas se muestra según `config:read` / `areas:manage` y mutaciones respetan `areas:manage`.
- [x] usuario con solo `areas:manage` no recibe administración IAM.
- [x] bridge de Accesos/Vite conserva fail-fast estructural.
- [x] consola Accesos conserva navegación estándar.
- [x] navegación completa desde Accesos queda especificada en Feature 011.
- [x] **Recargar** se diferencia de acciones de persistencia.
- [x] listas IAM protegen overflow de badges.
- [x] Guardar en Roles usa estado dirty real.
- [x] Grupos usa borrador local y guardado explícito.
- [x] Maestro de Áreas, Maestro de Categorías y Categorías por área permanecen separados.
- [x] Categorías por área muestra solo categorías activas.
- [x] asignación Área↔Categoría persiste solo al pulsar Guardar.
- [ ] validar manualmente System Admin después del pull final.
- [ ] validar manualmente usuario con `config:read`.
- [ ] validar manualmente usuario con `areas:manage` sin `config:read`.
- [ ] validar manualmente estados dirty/persistencia de Roles/Grupos/Área-Categoría.

## Migraciones

- [x] `0006` crea `areas:manage` y Rol `area-manager`.
- [x] `0007` incorpora `config:read`.
- [x] cadena actual continúa hasta `0008`.
- [ ] ejecutar `alembic heads` en head final.
- [ ] ejecutar `alembic current` en PostgreSQL local final.
- [ ] smoke `alembic upgrade head` si aplica.

## Pruebas

- [x] contratos backend cubren system-only y `areas:manage`.
- [x] `test_frontend_configuration_access.py` protege separación de capacidades e integración de Accesos.
- [x] `test_frontend_classification_admin_contract.py` protege catálogo/asignación.
- [x] Feature 011 agrega `test_access_navigation_bridge.py` para navegación desde Accesos.
- [ ] suite backend completa ejecutada localmente en head final.
- [ ] `npm run build` ejecutado localmente en head final.
- [ ] Docker build/smoke ejecutado localmente en head final.

## Documentación

- [x] Constitución vigente actualizada a 2.9.0.
- [x] Feature 009 actualizada para indicar evolución por Feature 011.
- [x] `docs/CONFIGURATION_ACCESS.md` actualizado.
- [x] `docs/IAM_MODEL.md` actualizado.
- [x] `docs/FASTAPI_ARCHITECTURE.md` actualizado.
- [x] `docs/CLASSIFICATION_MODEL.md` actualizado.
- [x] `docs/TERMINOLOGY.md` actualizado.
- [x] `docs/README.md` actualizado.
- [x] README principal actualizado.
- [x] PROMPT_RECONSTRUCCION actualizado.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.

## Regla de precedencia

Para separación de capacidades, Feature 009 continúa vigente. Para la navegación de Usuarios/Organigrama/Accesos, prevalecen Constitución 2.9.0 y Feature 011.
