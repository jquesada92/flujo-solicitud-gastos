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
- [x] bridge temporal de `injectAccessMenu()` tolera whitespace/LF/CRLF y exige exactamente una coincidencia.
- [x] el bridge de Accesos no usa `replaceRequired()` con un bloque multilinea literal para el guard de inyección.
- [x] la consola de **Accesos** conserva visible la navegación estándar de la aplicación.
- [x] navegar desde la barra estándar fuera de **Accesos** cierra la consola IAM sin requerir un botón **Volver** independiente.
- [x] la acción de refresco se presenta como **Recargar** y se integra con las pestañas internas.
- [x] la consola IAM reutiliza el ancho, espaciado, tarjetas y jerarquía visual del shell principal.
- [x] la columna de navegación IAM reserva ancho suficiente y nombres/correos largos no cortan badges **Activo/SISTEMA**.
- [x] el Maestro de Roles muestra únicamente el nombre del Rol y su estado; el resumen de códigos de permiso queda en el panel de detalle/edición.
- [x] **Guardar cambios** de Roles permanece deshabilitado mientras nombre, descripción y permisos coincidan con persistencia.
- [x] en **Grupos**, cambiar Roles heredados o Miembros modifica un borrador local y no persiste inmediatamente.
- [x] el detalle de Grupo expone un único botón **Guardar cambios** para Roles heredados + Miembros.
- [x] **Guardar cambios** de Grupo permanece gris/deshabilitado sin cambios y usa el acento pendiente cuando existe un diff real.
- [x] cambiar de Grupo con cambios pendientes exige confirmación antes de descartarlos.
- [x] los botones de persistencia deshabilitados usan estado gris de bajo énfasis.
- [x] los botones con cambios pendientes conocidos por el componente usan un brillo/acento leve de la paleta existente.
- [x] la pantalla canónica separa Maestro de Áreas, Maestro de Categorías y **Categorías por área**.
- [x] **Categorías por área** muestra solo categorías activas.
- [x] categorías inactivas siguen visibles en el Maestro de Categorías para poder reactivarlas.
- [x] el contador de **Categorías por área** considera solo categorías activas.
- [x] cambiar el checkbox de asignación no persiste hasta pulsar **Guardar** en la fila.
- [x] si no existen categorías activas, la tarjeta muestra un estado vacío explícito.
- [ ] validar manualmente menú System Admin.
- [ ] validar manualmente menú de usuario con `areas:manage`.
- [ ] validar manualmente usuario ordinario sin Configuración.
- [ ] validar manualmente navegación desde Accesos hacia Inicio/Solicitudes/Facturas/Configuración usando la barra estándar.
- [ ] validar manualmente que emails largos no recorten el estado del usuario en Accesos.
- [ ] validar manualmente que el Maestro de Roles no muestre cadenas de permisos debajo del nombre.
- [ ] validar manualmente estados gris/pendiente de Guardar en Roles, Grupos y Categorías por área.
- [ ] validar manualmente que cambiar Roles/Miembros de Grupo no persista hasta pulsar **Guardar cambios**.
- [ ] validar manualmente que una categoría desactivada desaparece de **Categorías por área** y reaparece al reactivarla conservando su relación previa.

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
- [x] `test_frontend_configuration_access.py` protege separación de menú, robustez del bridge, checkbox IAM, integración de navegación, overflow de listas, presentación compacta de Roles, estado dirty de Roles y guardado explícito de asignaciones de Grupo.
- [x] `test_frontend_classification_admin_contract.py` protege catálogo global, guardado por fila y visibilidad solo de categorías activas en asignación.
- [x] `test_migrations.py` protege `0006`.
- [ ] suite backend completa ejecutada localmente en head final.
- [ ] `npm run build` ejecutado localmente con éxito en head final.
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
- [x] PR #9 actualizado.

## Build hardening observado

- [x] se documentó el fallo local `Legacy main.jsx extraction could not find: system-only access menu injection`.
- [x] se sustituyó la coincidencia multilinea literal por regex estructural tolerante.
- [ ] rerun local de `npm run build` confirma el fix en el entorno Windows/Vite 8.2.1 del desarrollador.
