# Criterios de aceptación — IAM configurable y hardening FastAPI

## Autorización

- [x] Existe un catálogo persistido de permisos atómicos.
- [x] Roles persistidos pueden contener múltiples permisos.
- [x] Grupos persistidos pueden recibir múltiples roles.
- [x] Usuarios pueden pertenecer a múltiples grupos.
- [x] Usuarios pueden recibir roles directos opcionales.
- [x] Usuarios pueden recibir permisos directos opcionales.
- [x] Permisos efectivos se calculan como unión de las fuentes anteriores.
- [x] La ausencia de permiso produce 403 en operaciones protegidas.
- [x] `UserRole.ADMIN` no produce acceso automático.
- [x] Nombres de cargos/grupos/roles no son condiciones de autorización canónica.
- [x] Cargos/posiciones no conceden permisos.

## Cuenta técnica

- [x] La cuenta técnica está identificada explícitamente en `system_accounts`.
- [x] Sus permisos efectivos máximos son `config:manage` y `requests:read`.
- [x] No puede crear solicitudes.
- [x] No puede aprobar/votar.
- [x] No puede cerrar solicitudes ni subir/reemplazar factura.
- [x] Una asignación accidental de `requests:close` no cambia lo anterior.

## Interfaz gráfica

- [x] Existe acceso `Configuración → Accesos`.
- [x] Se pueden crear grupos desde UI.
- [x] Se pueden activar/inactivar y renombrar grupos.
- [x] Se pueden administrar miembros del grupo.
- [x] Se pueden asignar roles al grupo.
- [x] Se pueden crear roles desde UI.
- [x] Se pueden seleccionar permisos del rol.
- [x] Se pueden crear usuarios desde la consola IAM.
- [x] Se pueden asignar grupos, roles directos, permisos directos y cargos a usuarios.
- [x] Se pueden crear/renombrar/activar cargos.
- [x] La UI muestra los permisos efectivos del usuario.
- [x] Los permisos atómicos se muestran como catálogo de producto, no como códigos inventables por el cliente.
- [x] La cuenta técnica se muestra protegida y no es editable como usuario operativo.

## FastAPI

- [x] La app usa `APIRouter` por dominios/capacidades.
- [x] `get_db()` entrega/cierra una sesión por request.
- [x] Configuración está centralizada con `pydantic-settings`.
- [x] `lifespan` no ejecuta DDL, create_all, seed de negocio ni backfill.
- [x] `app/main.py` es un alias mínimo al application factory.
- [x] Modelos nuevos no se declaran dentro de routers.
- [x] Contratos nuevos reutilizables viven en `schemas/`.
- [x] Operaciones canónicas con SQLAlchemy/filesystem síncrono usan path functions `def`.
- [x] Login/activity tienen response models explícitos.
- [x] Existe suite `TestClient` de autorización IAM.

## Passwords

- [x] Nuevas contraseñas usan Argon2 mediante `pwdlib`.
- [x] PBKDF2 legacy se sigue verificando durante transición.
- [x] Login correcto con PBKDF2 devuelve un hash Argon2 nuevo para persistir.
- [x] Cambio de contraseña genera Argon2.

## Migraciones / despliegue

- [x] Existe baseline Alembic property-free para una base PostgreSQL limpia.
- [x] La cadena Alembic es lineal: `0000 → 0001 → 0002`.
- [x] Existe un test que exige un único head y la cadena esperada.
- [x] Existen migraciones Alembic versionadas para IAM.
- [x] Bootstrap del administrador técnico es idempotente y externo al lifespan.
- [x] Docker ejecuta migraciones y bootstrap antes de iniciar Uvicorn.
- [x] El despliegue no depende de `preDeployCommand` de un plan pago de Render.
- [x] Los scripts `.sh` se fuerzan a LF mediante `.gitattributes`.
- [x] El Dockerfile normaliza CRLF defensivamente antes de ejecutar `start.sh`.
- [x] Docker Compose espera el healthcheck del backend antes de iniciar Nginx.
- [ ] Antes del despliegue productivo se crea snapshot/backup de Neon.
- [ ] Se ejecuta smoke test real de `alembic upgrade head` contra PostgreSQL/Neon de preview antes de producción.

## Solicitudes / aprobación

- [x] Crear solicitud requiere `requests:create` en la ruta canónica.
- [x] Población MULTI_QUOTE se obtiene desde `requests:approve`.
- [x] Votar requiere `requests:approve`.
- [x] Invitaciones de votación representan la población congelada de la ronda.
- [x] Cerrar/reemplazar factura requiere `requests:close`.
- [x] Uploads canónicos requieren permisos explícitos.
- [x] Motor de aprobación obtiene participantes desde IAM para políticas canónicas.
- [ ] **Feature futura:** refactorizar fórmula funcional de quorum/mayoría de aprobación para cumplir exactamente la Constitución 2.2.0.
- [ ] **Feature futura:** especificar/refactorizar quorum y empate de cotizaciones.

## Compatibilidad / deuda

- [x] `can_*` legacy no son fuente de autorización; se derivan de IAM cuando código viejo los necesita.
- [x] Rutas canónicas se registran antes de rutas legacy equivalentes.
- [x] `UserRole` queda documentado como compatibilidad temporal.
- [ ] **Deuda:** retirar `/api/users` legacy cuando el frontend operativo deje de consumirlo.
- [ ] **Deuda:** retirar ramas por `UserRole` del router monolítico de gastos una vez extraídas todas sus rutas.
- [ ] **Deuda:** modularizar `frontend/src/main.jsx` y retirar `domain-normalization.js`.

## Calidad

- [x] Backend tests incluyen escenarios positivos y negativos IAM.
- [x] `npm run build` forma parte de CI.
- [x] Backend compile/tests forman parte de CI.
- [x] Imágenes Docker se construyen en CI.
- [x] Todos los jobs del commit final del PR están verdes antes de marcarlo Ready for review.

## Documentación

- [x] Constitución actualizada.
- [x] Spec funcional creada.
- [x] Plan técnico creado.
- [x] Criterios de aceptación creados.
- [x] README actualizado.
- [x] Prompt maestro actualizado.
- [x] Documentación IAM/FastAPI actualizada.
- [x] Terminología actualizada.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [x] Descripción final del PR sincronizada.
