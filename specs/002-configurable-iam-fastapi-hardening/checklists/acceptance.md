# Criterios de aceptación — IAM configurable y hardening FastAPI

**Constitución vigente:** 2.9.0  
**Nota:** Feature 002 fue evolucionada por Features 003–011. Este checklist refleja el contrato actual.

## Autorización

- [x] existe catálogo persistido de permisos atómicos.
- [x] Roles contienen permisos.
- [x] Grupos reciben Roles.
- [x] Usuarios pertenecen a múltiples Grupos.
- [x] Usuarios reciben Roles/permisos directos opcionales.
- [x] Cargos/Posiciones pueden heredar Roles mediante `position_roles`.
- [x] permisos efectivos acumulan directos + Rol + Grupo→Rol + Cargo→Rol + baseline.
- [x] `requests:read` es baseline para usuarios activos.
- [x] ausencia de permiso mutable produce DENY.
- [x] `UserRole.ADMIN` no autoriza por sí mismo.
- [x] nombres de Cargo/Grupo/Rol no son condiciones de autorización.
- [x] `config:manage` es system-only.
- [x] `config:read` es lectura configurable.
- [x] `areas:manage` es escritura organizacional configurable.
- [x] `requests:close` es legacy inactivo.

## Cuenta técnica por ambiente

- [x] cuenta técnica se identifica mediante `system_accounts`.
- [x] política depende de `SystemAccount + ENVIRONMENT`.
- [x] producción limita IAM a `requests:read + areas:manage + config:read + config:manage`.
- [x] producción no permite crear solicitudes por política IAM.
- [x] producción no permite aprobar/votar.
- [x] producción excluye cuenta técnica de poblaciones financieras.
- [x] producción conserva excepciones por recurso para cancelar/corregir/cierre-factura.
- [x] no-producción puede recibir todos los permisos atómicos activos para testing E2E.
- [x] `RENDER=true` no activa por sí solo segregación funcional.

## Contrato autenticado

- [x] `UserOut` expone `permission_codes`.
- [x] `UserOut` expone `is_system_account`.
- [x] aliases `can_*` legacy no son autoridad backend.
- [x] `current_user()`/backend vuelven a validar permisos/capacidades.

## Interfaz gráfica / Accesos

- [x] existe `Configuración → Accesos`.
- [x] Accesos permite crear Usuarios.
- [x] Accesos administra Grupos y miembros.
- [x] Accesos administra Roles y Permisos.
- [x] Accesos administra Cargos/Posiciones.
- [x] Accesos administra Roles de Grupo/Cargo y asignaciones directas.
- [x] Accesos muestra permisos efectivos/fuentes.
- [x] `config:read` reutiliza Accesos en modo solo lectura.
- [x] Usuarios/Personas ya no es una pantalla independiente.
- [x] Organigrama ya no es una pantalla independiente.
- [x] cuenta técnica se identifica/protege en IAM.
- [x] navegación desde Accesos está cubierta por Feature 011 y `access-navigation-bridge.js`.
- [ ] validar manualmente creación/edición de Usuario en head final.
- [ ] validar manualmente navegación completa desde Accesos en Docker.

## FastAPI

- [x] app usa `APIRouter` por dominios/capacidades.
- [x] `get_db()` entrega/cierra sesión por request.
- [x] configuración usa `pydantic-settings`.
- [x] `lifespan` no ejecuta migraciones/backfills.
- [x] `app/main.py` es alias al application factory.
- [x] modelos/schemas/servicios están separados.
- [x] operaciones síncronas pueden usar threadpool mediante path functions `def`.
- [x] existen tests `TestClient` de autorización.

## Passwords

- [x] nuevas contraseñas usan Argon2.
- [x] PBKDF2 legacy se verifica temporalmente.
- [x] login/cambio de contraseña pueden migrar/generar Argon2.

## Migraciones / despliegue

- [x] existe baseline Alembic.
- [x] cadena vigente es lineal hasta `0008`.
- [x] `0003` repara MULTI_QUOTE.
- [x] `0004` incorpora `position_roles`.
- [x] `0005` incorpora delegación y retira autoridad de `requests:close`.
- [x] `0006` incorpora `areas:manage`.
- [x] `0007` incorpora `config:read`.
- [x] `0008` renombra físicamente `expense_area` / `expense_category`.
- [x] bootstrap admin es externo al lifespan e idempotente.
- [x] Docker ejecuta Alembic + bootstrap antes de Uvicorn.
- [x] bootstrap canónico: `python -m scripts.bootstrap_admin`.
- [x] scripts `.sh` usan política LF/CRLF defensiva.
- [x] frontend local espera healthcheck backend.
- [x] no se recomienda `stamp` para ocultar esquema incompatible.
- [ ] ejecutar `alembic heads` en head final.
- [ ] ejecutar `alembic current` contra PostgreSQL final.
- [ ] smoke `alembic upgrade head` si aplica.

## Solicitudes / aprobación / recursos

- [x] nueva solicitud requiere `requests:create`.
- [x] población MULTI_QUOTE usa `requests:approve` efectivo.
- [x] votación/aprobación requieren permiso/asignación contextual.
- [x] corrección de solicitud ajena no se concede por `requests:create`.
- [x] cierre/factura se autoriza por `can_manage_closure()`, no `requests:close`.
- [x] `can_cancel`, `can_correct`, `can_close`, `can_delegate_close` son capacidades por recurso.
- [x] Feature 003 protege SIMPLE/MULTI_QUOTE.
- [x] Feature 007 protege Enviar a revisión/propiedad de corrección.
- [x] Feature 008 protege cierre/delegación.

## Clasificación

- [x] nuevo contrato usa `expense_area`.
- [x] nuevo contrato usa `expense_category`.
- [x] `expense_type` / `expense_subcategory` son aliases legacy únicamente.
- [x] `areas:manage` gobierna mutaciones de catálogos.

## Compatibilidad / deuda

- [x] `can_*`, `UserRole`, `AccessProfile`, `BOARD_CODES` están documentados como legacy.
- [x] `/api/users` legacy puede permanecer sin ser arquitectura objetivo.
- [x] vistas `people` / `organization` pueden permanecer internamente sin navegación.
- [x] `main.jsx` / `domain-normalization.js` / bridges Vite son deuda explícita.
- [ ] retirar deuda legacy gradualmente en features posteriores.

## Testing / calidad

- [x] existen tests IAM, migraciones, contenedores y contratos frontend relevantes.
- [x] Feature 011 agrega `test_access_navigation_bridge.py`.
- [ ] ejecutar suite backend completa en head final.
- [ ] ejecutar `npm run build` en head final.
- [ ] ejecutar Docker build/smoke en head final.

## Documentación

- [x] Constitución vigente 2.9.0.
- [x] Feature 002 spec actualizada al modelo vigente.
- [x] Feature 002 plan actualizado a cadena `0000 → ... → 0008`.
- [x] checklist actualizado sin marcar gates no ejecutados.
- [x] README actualizado.
- [x] Prompt maestro actualizado.
- [x] IAM_MODEL y FASTAPI_ARCHITECTURE actualizados.
- [x] Feature 009/011 reflejan fronteras/configuración actuales.
- [x] HISTORY y CHANGELOG actualizados.
