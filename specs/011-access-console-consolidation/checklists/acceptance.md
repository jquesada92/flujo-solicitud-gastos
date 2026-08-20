# Criterios de aceptación — Consolidación de Usuarios y Organigrama en Accesos

**Feature:** 011  
**Constitución:** 2.9.0

> Los ítems de documentación/código se marcan según el estado de la rama. Los gates que requieren ejecución local/manual permanecen sin marcar hasta ejecutarse realmente.

## Navegación

- [x] **Usuarios/Personas** deja de aparecer como entrada independiente de Configuración.
- [x] **Organigrama** deja de aparecer como entrada independiente de Configuración.
- [x] **Accesos** permanece como punto único de administración IAM.
- [x] existe `frontend/src/access-navigation-bridge.js` para cerrar `#access-management` al navegar desde la topbar.
- [x] el bridge se carga antes de `main.jsx`.
- [x] abrir/cerrar solamente el dropdown **Configuración** no fuerza salida de Accesos.
- [x] seleccionar una opción navegable de Configuración sí sale de Accesos.
- [x] el caso de destino igual a la pestaña React subyacente queda cubierto por limpieza explícita del hash.
- [x] existe test de contrato `test_access_navigation_bridge.py`.
- [ ] validar manualmente Inicio desde Accesos en Docker.
- [ ] validar manualmente Solicitudes desde Accesos en Docker.
- [ ] validar manualmente Facturas desde Accesos en Docker.
- [ ] validar manualmente Auditoría desde Accesos en Docker.
- [ ] validar manualmente Configuración → otra pantalla desde Accesos en Docker.
- [ ] validar manualmente Salir desde Accesos en Docker.

## Accesos

- [x] creación de Usuarios permanece dentro de Accesos.
- [x] Grupos permanecen dentro de Accesos.
- [x] Roles y Permisos permanecen dentro de Accesos.
- [x] Cargos/Posiciones permanecen dentro de Accesos.
- [x] asignaciones y permisos efectivos permanecen dentro de Accesos.
- [x] `config:read` reutiliza Accesos en modo solo lectura.
- [ ] validar manualmente creación de un usuario en head final.
- [ ] validar manualmente edición de un usuario existente en head final.

## Seguridad

- [x] `config:manage` continúa siendo system-only.
- [x] `config:read` no concede mutaciones.
- [x] `areas:manage` no concede administración IAM.
- [x] ocultar UI no reemplaza autorización backend.
- [x] ninguna regla nueva autoriza por nombre de Cargo, Grupo o Rol.
- [x] cuentas técnicas se identifican mediante `system_accounts`.

## Clasificación canónica

- [x] `expense_area` es el nombre canónico de Área en solicitudes.
- [x] `expense_category` es el nombre canónico de Categoría en solicitudes.
- [x] Alembic `20260819_0008` está presente en la rama después de sincronizar `main`.
- [x] documentación deja claro que `expense_type` / `expense_subcategory` son aliases legacy únicamente.
- [x] CLASSIFICATION_MODEL documenta que las columnas físicas canónicas son `expense_area` / `expense_category`.

## Integración con main

- [x] cambios faltantes de `main` integrados en `agent/consolidate-users-organigram-in-access`.
- [x] la sincronización incorporó `0008` y cambios frontend/backend de Área/Categoría.
- [x] la rama quedó 0 commits detrás de `main` inmediatamente después de la sincronización.
- [ ] volver a comprobar `behind_by=0` antes del merge final por si `main` avanzó después.

## Alembic / base local

- [x] cadena documental vigente: `0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008`.
- [x] no se recomienda `alembic stamp` para ocultar una revisión ausente.
- [ ] ejecutar `alembic heads` en head final.
- [ ] ejecutar `alembic current` contra la base local final.
- [ ] ejecutar `alembic upgrade head` si `current` no está en head.

## Pruebas automatizadas / build

- [x] test de contrato `test_access_navigation_bridge.py` agregado.
- [x] contratos existentes de Configuración/Accesos permanecen documentados en el plan.
- [ ] ejecutar `python -m unittest tests.test_access_navigation_bridge -v`.
- [ ] ejecutar `python -m unittest discover -s tests -v`.
- [ ] ejecutar `npm run build` en frontend.
- [ ] levantar `docker compose up -d --build` y comprobar servicios healthy.

## Documentación y Spec-Kit

- [x] Constitución actualizada a **2.9.0**.
- [x] `spec.md` Feature 011 actualizado con navegación, seguridad, migración y escenarios.
- [x] `plan.md` Feature 011 actualizado con fases, gates y estado.
- [x] checklist Feature 011 actualizado sin falsear gates locales.
- [x] README principal actualizado.
- [x] `PROMPT_RECONSTRUCCION.md` actualizado.
- [x] `docs/CONFIGURATION_ACCESS.md` actualizado.
- [x] `docs/IAM_MODEL.md` actualizado.
- [x] `docs/CLASSIFICATION_MODEL.md` actualizado.
- [x] `docs/TERMINOLOGY.md` actualizado.
- [x] `docs/FASTAPI_ARCHITECTURE.md` actualizado.
- [x] `docs/README.md` actualizado e incluye Feature 011.
- [x] `docs/DOCUMENTATION_POLICY.md` actualizado.
- [x] `docs/HISTORY.md` actualizado.
- [x] `CHANGELOG.md` actualizado.
- [x] documentación canónica usa `expense_area` / `expense_category` como contrato vigente.
- [x] documentación canónica no presenta Usuarios/Personas u Organigrama como pantallas independientes.

## Cierre de Feature 011

La feature puede marcarse completa únicamente cuando todos estos gates estén verificados:

- [ ] migraciones locales compatibles;
- [ ] suite backend verde;
- [ ] build frontend verde;
- [ ] Docker healthy;
- [ ] navegación manual desde Accesos verde;
- [ ] creación/edición manual de Usuario desde Accesos verde.
