# Constitución del proyecto

**Proyecto:** Flujo de Control de Gastos  
**Versión:** 2.3.1  
**Vigente desde:** 2026-08-17

## 1. Evolucionar, no reconstruir sin necesidad

El producto existente debe evolucionar sobre el repositorio actual. Se reutiliza el código correcto y se migra o reemplaza únicamente lo que contradiga esta constitución, las especificaciones vigentes o los criterios de aceptación.

## 2. Producto neutral respecto al tipo de organización

El sistema debe poder utilizarse en empresas, PH y otras organizaciones sin introducir en el núcleo conceptos exclusivos de un dominio particular.

No forman parte del modelo canónico:

- apartamentos;
- propietarios o copropietarios;
- residentes o arrendatarios;
- `PersonType`;
- `OwnershipRole`;
- relaciones usuario-apartamento.

La estructura organizacional tampoco puede quedar codificada mediante nombres como Junta Directiva, Administradora, Presidente, Tesorero, Finanzas, IT u otros. Esos nombres pueden existir como **datos configurados por cada organización**, nunca como condiciones de autorización en runtime.

## 3. Terminología canónica

- **Usuario**: cuenta que interactúa con el sistema.
- **Grupo**: conjunto configurable de usuarios.
- **Rol**: conjunto configurable de permisos.
- **Permiso**: capacidad atómica implementada por el producto.
- **Cargo / Posición**: metadato organizacional descriptivo; no concede permisos.
- **Área**: unidad, departamento o función organizacional asociada al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.

Área y Categoría son catálogos independientes. Una Categoría puede habilitarse para múltiples Áreas mediante una relación configurable.

## 4. IAM configurable: permisos sobre nombres

La autorización canónica se resuelve mediante permisos efectivos persistidos en PostgreSQL y las políticas explícitas de cuenta técnica definidas por ambiente.

Modelo:

```text
Usuario → Grupo → Rol → Permiso
       ↘ Rol directo
       ↘ Permiso directo
       ↘ Cargo/Posición (descriptivo solamente)
```

Para usuarios operativos, los permisos efectivos son la unión de:

1. permisos directos del usuario;
2. permisos de roles asignados directamente;
3. permisos de roles heredados a través de grupos activos.

Si una capacidad no está permitida explícitamente, el resultado es **DENY**.

El producto define las capacidades atómicas disponibles. Cada organización configura desde la interfaz sus grupos, roles, cargos, membresías y asignaciones.

Permisos funcionales iniciales:

- `requests:read`;
- `requests:create`;
- `requests:approve`;
- `requests:close`;
- `config:manage`.

No autorizar por:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER` o `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure` como fuente de verdad;
- nombre de rol, grupo, cargo o perfil;
- correo fijo;
- ID mágico;
- listas de cargos como PRESIDENTE/TESORERO/etc.;
- conceptos inmobiliarios.

Los campos legacy pueden existir temporalmente durante una migración, pero no pueden ser autoridad de autorización.

## 5. Política de la cuenta técnica por ambiente

El administrador técnico de bootstrap es una **cuenta de sistema protegida** identificada mediante `system_accounts`. No se identifica por email, nombre, cargo ni enum legacy.

La política depende exclusivamente del ambiente declarado por `ENVIRONMENT`:

### Producción

Cuando `ENVIRONMENT=production`, la cuenta técnica mantiene segregación estricta de funciones. Sus permisos efectivos máximos son:

- `config:manage`;
- `requests:read`.

En producción no puede obtener ni ejercer:

- `requests:create`;
- `requests:approve`;
- `requests:close`.

Esta restricción prevalece incluso si una configuración posterior intenta otorgarle permisos financieros mediante grupo, rol o permiso directo. Tampoco participa en poblaciones financieras de aprobación o votación.

### No producción

En cualquier ambiente distinto de `production` —por ejemplo `local`, `development`, `dev`, `test`, `staging` o `preview`— la cuenta técnica debe poder ejercer **todos los permisos atómicos activos del producto** para realizar pruebas end-to-end.

En no producción también puede participar en poblaciones de aprobación/votación cuando el permiso correspondiente esté activo, de forma que un único administrador técnico pueda validar todas las funcionalidades sin crear cuentas auxiliares obligatorias.

Este acceso ampliado es una política de prueba del sistema, no un rol empresarial ni una excepción por nombre de usuario.

El hecho de ejecutar la aplicación en Render u otro hosting puede exigir secretos fuertes y CORS restrictivo, pero **no convierte automáticamente el ambiente en producción para autorización**. La segregación financiera de producción se activa únicamente con `ENVIRONMENT=production`.

El bootstrap puede usar variables `ADMIN_*` únicamente para crear o recuperar la cuenta técnica inicial. Después del bootstrap, la identidad de cuenta técnica se representa mediante datos persistidos.

## 6. Configuración gráfica sobre código

La interfaz debe permitir administrar, sin despliegue de código:

- usuarios;
- grupos;
- roles;
- cargos/posiciones;
- membresías de grupos;
- roles de grupos;
- roles directos de usuario;
- permisos directos de usuario;
- visualización de permisos efectivos y su origen;
- Áreas y Categorías;
- políticas de aprobación y demás configuración organizacional cuando corresponda.

Una organización futura puede tener estructuras completamente distintas a la configuración inicial del PH.

## 7. Backend como autoridad

El frontend puede ocultar o mostrar acciones por UX, pero el backend es la autoridad final para:

- autorización;
- transiciones;
- población de participantes;
- acceso a documentos;
- decisiones;
- configuración IAM;
- política ambiental de cuentas técnicas;
- invariantes del tipo de solicitud durante una corrección.

Una operación sensible debe declarar una dependencia de permiso explícita o pasar por un servicio que la aplique.

## 8. Arquitectura FastAPI

El backend sigue estas reglas:

- `APIRouter` por dominio/capacidad;
- modelos SQLAlchemy fuera de routers;
- esquemas Pydantic fuera de routers cuando son contratos reutilizables;
- servicios para lógica de negocio reutilizable;
- dependencia `get_db()` con `yield`/contexto por request;
- configuración centralizada mediante Pydantic Settings;
- `lifespan` reservado a recursos de ciclo de vida, no a migraciones de esquema;
- migraciones versionadas con Alembic antes de levantar el proceso ASGI;
- response models explícitos para contratos sensibles;
- SQLAlchemy síncrono se usa desde path operations `def` para que FastAPI ejecute I/O bloqueante en su threadpool;
- pruebas HTTP con `TestClient` para autorización y contratos críticos.

`app/main.py` no debe volver a convertirse en un archivo de migraciones, seeds o lógica de dominio.

## 9. Contraseñas y sesiones

- nuevos hashes: Argon2 mediante `pwdlib` recomendado;
- hashes PBKDF2 legacy pueden verificarse temporalmente y deben migrar transparentemente a Argon2 después de un login correcto;
- JWT con expiración absoluta;
- timeout de inactividad;
- revocación por versión de sesión;
- fallos de autenticación no revelan si el usuario existe.

## 10. Historial y trazabilidad

Toda acción significativa debe poder reconstruirse con actor, fecha/hora, entidad, cambios, estado anterior/nuevo y motivo cuando aplique. Los eventos históricos relevantes son append-only.

Los cambios futuros de membresías, roles y permisos deben incorporarse al modelo de auditoría de acceso; una asignación de autorización no debe cambiar silenciosamente.

## 11. Evidencia documental

Los documentos son evidencia privada. Deben validarse por contenido real, almacenarse fuera del acceso público directo, descargarse con autorización backend, conservar versiones al sustituirse y registrar actor/fecha/motivo.

Una corrección no debe obligar a descartar o volver a cargar evidencia válida ya asociada a la solicitud únicamente porque el navegador no pueda prellenar un control de archivo.

## 12. Solicitudes, clasificación y correcciones

Cada solicitud se clasifica por **Área + Categoría**. La clasificación histórica no cambia retroactivamente porque un catálogo se renombre, desactive o cambie.

La solicitud simple contiene una opción/cotización. `MULTI_QUOTE` mantiene la selección de cotización separada conceptualmente del proceso de aprobación.

**Corregir / reenviar MUST conservar el `request_type` original.** Un valor por defecto del frontend, un campo legacy o un payload incorrecto no puede convertir silenciosamente una solicitud entre `SIMPLE` y `MULTI_QUOTE`.

Reglas mínimas de corrección:

- `SIMPLE → corrección → SIMPLE`;
- `MULTI_QUOTE → corrección → MULTI_QUOTE`;
- cambiar deliberadamente entre tipos requiere una operación funcional explícita distinta;
- una corrección MULTI_QUOTE genera un `flow_id` nuevo;
- los votos e invitaciones vigentes de la ronda anterior dejan de ser estado activo;
- los eventos históricos previos se conservan;
- los soportes existentes se conservan;
- mientras no exista una especificación de edición estructural de rondas, la corrección MULTI_QUOTE conserva la cantidad de opciones existente y permite editar su contenido.

El backend debe hacer cumplir estas reglas incluso si la UI falla al hidratar el formulario.

## 13. Participantes y decisiones

La población elegible de una ronda debe congelarse/versionarse. Para votación de cotizaciones, las invitaciones de la ronda representan el snapshot de participantes hasta que exista un modelo explícito de rondas.

Para una ronda de aprobación:

- `response_rate = valid_responses / eligible_participants`;
- solo se resuelve cuando `response_rate > 0.50`;
- `approval_rate = approvals / valid_decision_responses`;
- `rejection_rate = rejections / valid_decision_responses`;
- aprobar si `approval_rate > 0.50`;
- rechazar si `rejection_rate > 0.50`;
- empate o falta de mayoría permanece pendiente;
- solicitar corrección es una transición separada.

Las reglas de selección de cotización no se presumen iguales a las reglas de aprobación. Si el código legacy aún difiere de esta regla, debe documentarse como deuda funcional y no presentarse como resuelto por un refactor de arquitectura.

## 14. Aprobado no significa cerrado

Una solicitud aprobada permanece en proceso hasta cumplir el cierre. El cierre requiere factura y `requests:close`.

- En producción, una cuenta técnica nunca puede cerrar solicitudes.
- En no producción, una cuenta técnica puede cerrar solicitudes para pruebas end-to-end conforme a la política de la sección 5.

## 15. Migraciones, despliegue y portabilidad de contenedores

Los cambios estructurales utilizan migraciones versionadas. No se permiten nuevas migraciones destructivas ad-hoc en FastAPI startup.

Orden de despliegue:

1. construir artefacto;
2. ejecutar `alembic upgrade head`;
3. ejecutar el bootstrap idempotente como módulo desde la raíz del backend: `python -m scripts.bootstrap_admin`;
4. iniciar `uvicorn`;
5. ejecutar health checks.

El bootstrap no debe depender de ejecutar un archivo por ruta si ese modo altera `sys.path` e impide importar `app`. Los scripts operativos Python deben ejecutarse como módulos o mediante un entrypoint equivalente con raíz de imports explícita.

En Render económico, estos pasos pueden ejecutarse en el entrypoint Docker antes de `uvicorn`; en plataformas con pre-deploy separado, se prefiere ese mecanismo para múltiples réplicas.

Los scripts shell ejecutados dentro de contenedores Linux deben conservar finales de línea LF independientemente del sistema operativo del desarrollador. El repositorio debe forzar `*.sh` a LF y la imagen puede normalizar defensivamente CRLF durante el build.

La dependencia entre servicios locales debe basarse en health checks cuando el consumidor requiere que el servicio proveedor esté realmente disponible; un simple orden de creación de contenedores no sustituye disponibilidad.

Antes de retirar datos: respaldo, inventario, migración versionada, validación y recuperación real.

## 16. Seguridad y rendimiento

Como mínimo:

- default deny para usuarios operativos;
- backend authoritative;
- rate limiting diferenciado;
- CORS restrictivo;
- secretos fuera del frontend/logs;
- ORM/consultas parametrizadas;
- validación real de archivos;
- paginación backend para colecciones crecientes, default 25 y máximo 100;
- evitar N+1;
- pool y query timeout configurables antes de escalar;
- una futura capa de scope debe limitar permisos por organización/área/recurso sin reutilizar cargos como autorización;
- la elevación de la cuenta técnica fuera de producción debe depender de `ENVIRONMENT`, nunca de email/nombre/cargo.

## 17. Calidad y pruebas

Los cambios incluyen pruebas proporcionales al riesgo. Para IAM son obligatorias pruebas positivas y negativas de:

- permisos directos;
- herencia Grupo → Rol → Permiso;
- cuenta técnica con todos los permisos activos en no producción;
- cuenta técnica incluida en poblaciones de aprobación/votación fuera de producción;
- cuenta técnica restringida a `config:manage` + `requests:read` en producción;
- operaciones financieras negadas a la cuenta técnica en producción incluso con asignación accidental;
- endpoints `config:manage`;
- cambios de permisos efectivos sin reiniciar la app;
- login/respuesta de usuario exponiendo permisos efectivos coherentes con el ambiente.

Para correcciones son obligatorias pruebas que demuestren que `request_type` no cambia, que una MULTI_QUOTE reinicia su ronda y que evidencia existente no se pierde por la hidratación del formulario.

Para portabilidad de contenedores deben existir controles de regresión que verifiquen la política LF de scripts, el mecanismo defensivo de normalización y que el módulo de bootstrap sea importable desde la imagen construida.

CI debe ejecutar backend tests, compilación frontend, construcción de imágenes Docker y smoke tests del entrypoint/bootstrap backend.

## 18. Documentación es parte del código

Ningún cambio funcional, de dominio, UX, API, modelo de datos, seguridad, migración o arquitectura se considera terminado si la documentación afectada no queda actualizada en el mismo PR.

Revisar cuando aplique:

- `.specify/memory/constitution.md`;
- `specs/<feature>/spec.md`;
- `specs/<feature>/plan.md`;
- criterios de aceptación;
- `README.md`;
- `PROMPT_RECONSTRUCCION.md`;
- `docs/` funcionales/técnicos;
- `docs/TERMINOLOGY.md`;
- `docs/HISTORY.md`;
- `CHANGELOG.md`;
- contratos/API y comentarios técnicos.

## 19. Consistencia entre artefactos

Prioridad:

1. Constitución vigente.
2. Especificación funcional.
3. Aclaraciones/criterios de aceptación.
4. Plan técnico.
5. Tareas y código.
6. README, prompts y documentación derivada.

Una discrepancia código-documentación es un defecto salvo que esté expresamente marcada como deuda/transición.

## 20. Definition of Done

Una feature está terminada cuando:

- comportamiento implementado coincide con requisitos y criterios;
- autorización no depende de nombres organizacionales hardcodeados;
- la política de cuenta técnica está probada en producción y no producción;
- invariantes de corrección están protegidos en backend y probados;
- migraciones son versionadas y desplegables;
- términos visibles coinciden con `docs/TERMINOLOGY.md`;
- README/prompt no reconstruyen conceptos retirados;
- HISTORY explica decisiones relevantes;
- CHANGELOG registra el entregable;
- CI y pruebas mencionadas realmente existen y pasan;
- deuda temporal queda explícita, con ruta de retiro.
