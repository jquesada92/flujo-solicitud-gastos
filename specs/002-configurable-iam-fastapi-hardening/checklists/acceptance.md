# Criterios de aceptación — IAM configurable y hardening FastAPI

## Autorización

- [x] Existe un catálogo persistido de permisos atómicos.
- [x] Roles persistidos pueden contener múltiples permisos.
- [x] Grupos persistidos pueden recibir múltiples roles.
- [x] Usuarios pueden pertenecer a múltiples grupos.
- [x] Usuarios pueden recibir roles directos opcionales.
- [x] Usuarios pueden recibir permisos directos opcionales.
- [x] Permisos efectivos de usuarios operativos se calculan como unión de las fuentes anteriores.
- [x] La ausencia de permiso produce 403 en operaciones protegidas.
- [x] `UserRole.ADMIN` no produce acceso automático por sí mismo.
- [x] Nombres de cargos/grupos/roles no son condiciones de autorización canónica.
- [x] Cargos/posiciones no conceden permisos.

## Cuenta técnica por ambiente

- [x] La cuenta técnica está identificada explícitamente en `system_accounts`.
- [x] La política ampliada/restringida depende de `SystemAccount + ENVIRONMENT`, no de email/nombre/cargo/rol legacy.
- [x] `ENVIRONMENT=production` limita sus permisos efectivos a `config:manage` y `requests:read`.
- [x] En producción no puede crear solicitudes.
- [x] En producción no puede aprobar/votar.
- [x] En producción no puede cerrar solicitudes ni subir/reemplazar factura.
- [x] En producción una asignación accidental de `requests:close` no cambia lo anterior.
- [x] En producción no aparece en poblaciones financieras de `requests:approve`.
- [x] En cualquier ambiente distinto de `production` recibe todos los permisos atómicos activos.
- [x] En no-producción puede crear, consultar, aprobar/votar, cerrar y configurar.
- [x] En no-producción puede aparecer en poblaciones de aprobación/votación cuando el permiso está activo.
- [x] `RENDER=true` por sí solo no activa la segregación funcional de producción.
- [x] Los runtimes alojados siguen pudiendo exigir secretos/CORS fuertes independientemente de la política funcional.

## Contrato de usuario autenticado

- [x] `UserOut` expone `permission_codes` efectivos.
- [x] `UserOut` expone `can_close` como alias temporal de `requests:close`.
- [x] Login calcula permisos efectivos antes de serializar al usuario.
- [x] `current_user()` vuelve a derivar aliases legacy desde IAM en cada request autenticado.
- [x] En no-producción el login de la cuenta técnica refleja permisos completos.
- [x] En producción el backend sigue siendo autoridad aunque UI legacy muestre accidentalmente una acción no permitida.

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
- [x] La UI IAM muestra los permisos efectivos del usuario.
- [x] Los permisos atómicos se muestran como catálogo de producto, no como códigos inventables por el cliente.
- [x] La cuenta técnica se muestra identificada/protegida en administración IAM.
- [ ] **Deuda frontend:** retirar el bypass visual `user.role === "ADMIN"` y `canClose={true}` del monolito; migrar visibilidad de acciones a `permission_codes`.

## FastAPI

- [x] La app usa `APIRouter` por dominios/capacidades.
- [x] `get_db()` entrega/cierra una sesión por request.
- [x] Configuración está centralizada con `pydantic-settings`.
- [x] Settings distinguen `is_production_environment` de validaciones de runtime alojado.
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
- [x] La cadena Alembic es lineal: `0000 → 0001 → 0002 → 0003`.
- [x] `0003` repara filas MULTI_QUOTE históricas con default `SIMPLE` incorrecto.
- [x] Existe un test que exige un único head y la cadena esperada.
- [x] Existen migraciones Alembic versionadas para IAM y reparaciones posteriores.
- [x] Bootstrap del administrador técnico es idempotente y externo al lifespan.
- [x] Docker ejecuta migraciones y bootstrap antes de iniciar Uvicorn.
- [x] El bootstrap se ejecuta canónicamente como `python -m scripts.bootstrap_admin` desde la raíz del backend.
- [x] `scripts` es importable como paquete y no depende de `PYTHONPATH` implícito.
- [x] El despliegue no depende de `preDeployCommand` de un plan pago de Render.
- [x] Los scripts `.sh` se fuerzan a LF mediante `.gitattributes`.
- [x] El Dockerfile normaliza CRLF defensivamente antes de ejecutar `start.sh`.
- [x] Docker Compose espera el healthcheck del backend antes de iniciar Nginx.
- [x] CI carga la imagen backend y valida entrypoint + bootstrap importable.
- [x] `render.yaml` productivo declara `ENVIRONMENT=production` explícitamente.
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
- [x] Feature 003 protege correcciones SIMPLE/MULTI_QUOTE y aísla el editor del estado previo de pestañas.
- [ ] **Feature futura:** refactorizar fórmula funcional de quorum/mayoría de aprobación para cumplir exactamente la Constitución 2.3.2.
- [ ] **Feature futura:** especificar/refactorizar quorum y empate de cotizaciones.

## Compatibilidad / deuda

- [x] `can_*` legacy no son fuente de autorización; se derivan de IAM cuando código viejo los necesita.
- [x] `can_close` es solo alias de compatibilidad; backend usa `requests:close`.
- [x] Rutas canónicas se registran antes de rutas legacy equivalentes.
- [x] `UserRole` queda documentado como compatibilidad temporal.
- [ ] **Deuda:** retirar `/api/users` legacy cuando el frontend operativo deje de consumirlo.
- [ ] **Deuda:** retirar ramas por `UserRole` del router monolítico de gastos una vez extraídas todas sus rutas.
- [ ] **Deuda:** modularizar `frontend/src/main.jsx` y retirar `domain-normalization.js`/transform Vite temporal.

## Testing de política ambiental

- [x] Test no-producción verifica todos los permisos activos para cuenta técnica.
- [x] Test no-producción verifica `permission_codes` y aliases en login.
- [x] Test no-producción verifica inclusión de cuenta técnica en `users_with_permission('requests:approve')`.
- [x] Test producción verifica solo config/read.
- [x] Test producción verifica que un `requests:close` directo accidental es filtrado.
- [x] Test producción verifica 403 en endpoint de cierre.
- [x] Test producción verifica exclusión de población de aprobación.
- [x] Test Settings verifica que preview alojado puede ser hardened sin activar autorización productiva.
- [x] Test Settings verifica que `ENVIRONMENT=production` sí activa la política productiva.

## Calidad

- [x] Backend tests incluyen escenarios positivos y negativos IAM.
- [x] `npm run build` forma parte de CI.
- [x] Backend compile/tests forman parte de CI.
- [x] Imágenes Docker se construyen en CI.
- [x] El entrypoint backend se valida dentro de la imagen construida por CI.
- [x] Tests de Feature 003 cubren dato legacy SIMPLE con evidencia MULTI_QUOTE.

## Documentación

- [x] Constitución vigente revisada; actualmente 2.3.2.
- [x] Spec funcional actualizada.
- [x] Plan técnico actualizado a la cadena Alembic `0000 → 0001 → 0002 → 0003`.
- [x] Criterios de aceptación actualizados.
- [x] README refleja la política ambiental y Feature 003.
- [x] Prompt maestro refleja la política ambiental y aislamiento de correcciones.
- [x] Documentación IAM/FastAPI refleja la política ambiental y la topología vigente.
- [x] HISTORY registra las decisiones.
- [x] CHANGELOG registra los cambios.
- [x] Índice documental sincronizado.
- [x] Terminología distingue selector de nueva solicitud y corrección.
- [ ] Descripción final del PR debe reflejar Constitución 2.3.2, estado aislado de correcciones y migración 0003.
