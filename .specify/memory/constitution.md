# Constitución del proyecto

**Proyecto:** Flujo de Control de Gastos  
**Versión:** 2.7.0  
**Vigente desde:** 2026-08-18

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
- **Grupo**: conjunto configurable de usuarios que puede heredar uno o más Roles.
- **Rol**: conjunto configurable de permisos.
- **Permiso**: capacidad atómica implementada por el producto.
- **Cargo / Posición**: elemento configurable de la estructura organizacional que puede heredar uno o más Roles. El nombre del Cargo nunca autoriza por sí mismo.
- **Área**: unidad, departamento o función organizacional asociada al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.
- **Delegación de cierre/factura**: asignación explícita y revocable que hace el solicitante para que otro usuario activo pueda gestionar el cierre y la factura de una solicitud concreta.

Área y Categoría son catálogos independientes. Una Categoría puede habilitarse para múltiples Áreas mediante una relación configurable.

## 4. IAM configurable: permisos sobre nombres

La autorización canónica se resuelve mediante permisos efectivos persistidos en PostgreSQL, capacidades base definidas por el producto, reglas explícitas por recurso y las políticas de cuenta técnica definidas por ambiente.

Modelo:

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ Capacidades base del producto
       ↘ Capacidades por recurso/delegación
```

Para usuarios operativos, los permisos efectivos son la unión de:

1. capacidades base del producto aplicables al usuario activo;
2. permisos directos del usuario;
3. permisos de roles asignados directamente;
4. permisos de roles heredados a través de grupos activos;
5. permisos de roles heredados a través de cargos/posiciones activos asignados al usuario.

Un mismo Rol puede reutilizarse simultáneamente en Grupos, Cargos y asignaciones directas. Por ejemplo, un Rol `Aprobador` con `requests:approve` puede asociarse a los Cargos Presidente/Tesorero y también al Grupo Junta Directiva sin duplicar la definición del permiso.

Para capacidades mutables no concedidas explícitamente por una de estas relaciones, el resultado es **DENY**, salvo reglas de recurso explícitas definidas por esta Constitución, como cancelar, corregir o cerrar/gestionar factura de una solicitud cuando el actor sea propietario, cuenta técnica protegida o delegado válido según corresponda.

Permisos funcionales activos iniciales:

- `requests:read`;
- `requests:create`;
- `requests:approve`;
- `config:manage`.

`requests:close` puede permanecer físicamente como **permiso legacy inactivo** para trazabilidad/compatibilidad histórica, pero no autoriza runtime de cierre, factura ni delegación. No debe presentarse como capacidad operativa configurable.

### Baseline universal de seguimiento

`requests:read` es una **capacidad base no revocable** para todo usuario activo y autenticado.

Por tanto, todo usuario activo debe poder:

- entrar a **Inicio / Dashboard**;
- consultar el resumen general de solicitudes de la organización;
- entrar a **Solicitudes**;
- consultar solicitudes creadas por cualquier usuario para dar seguimiento a su estado, independientemente de quién las solicitó;
- consultar la información de seguimiento y evidencia que el producto exponga bajo `requests:read`.

La lectura universal no concede ninguna acción mutable. Un usuario puede tener únicamente `requests:read` y seguir sin poder:

- crear nuevas solicitudes (`requests:create`);
- aprobar o votar (`requests:approve`);
- cerrar/gestionar factura de una solicitud ajena sin delegación;
- administrar configuración (`config:manage`).

**Corregir / reenviar no se concede por `requests:create` sobre solicitudes ajenas.** Es una capacidad por recurso reservada al solicitante original y a la cuenta protegida Administrador del sistema según la sección 12.

**Cerrar / adjuntar o corregir factura tampoco se concede por un permiso global.** Se rige por la sección 14.

Un rol, grupo o cargo puede terminar heredando `requests:read` por claridad, pero quitarlo de esas relaciones **no puede retirar** la capacidad base de un usuario activo. Los usuarios inactivos no pueden autenticarse ni ejercer el baseline.

No autorizar por:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER` o `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure`, `can_close` legacy como fuente de verdad;
- comparar el nombre/código de un rol, grupo, cargo o perfil;
- correo fijo;
- ID mágico;
- listas de cargos como PRESIDENTE/TESORERO/etc.;
- conceptos inmobiliarios.

**Sí está permitido** autorizar por permisos heredados desde relaciones persistidas `Cargo → Rol → Permiso`; lo prohibido es que el código pregunte si el cargo se llama Presidente, Tesorero, CFO o cualquier otro nombre concreto.

Los campos legacy pueden existir temporalmente durante una migración, pero no pueden ser autoridad de autorización ni limitar el baseline universal de seguimiento.

## 5. Política de la cuenta técnica por ambiente

El administrador técnico de bootstrap es una **cuenta de sistema protegida** identificada mediante `system_accounts`. No se identifica por email, nombre, cargo ni enum legacy.

La política depende exclusivamente del ambiente declarado por `ENVIRONMENT`.

### Producción

Cuando `ENVIRONMENT=production`, la cuenta técnica mantiene segregación estricta de funciones. Sus permisos efectivos máximos son:

- `config:manage`;
- `requests:read`.

En producción no puede obtener ni ejercer:

- `requests:create`;
- `requests:approve`.

`requests:close` ya no es una capacidad operativa del modelo vigente.

Esta restricción prevalece incluso si una configuración posterior intenta otorgarle permisos financieros mediante grupo, cargo, rol o permiso directo. Tampoco participa en poblaciones financieras de aprobación o votación.

La cuenta técnica puede cancelar, corregir/reenviar y gestionar cierre/factura de una solicitud como **acciones administrativas del ciclo de vida**, no como permisos financieros. Estas excepciones se identifican por `system_accounts` y no amplían el IAM empresarial.

### No producción

En cualquier ambiente distinto de `production` —por ejemplo `local`, `development`, `dev`, `test`, `staging` o `preview`— la cuenta técnica debe poder ejercer todos los permisos atómicos activos del producto para realizar pruebas end-to-end, además de sus capacidades administrativas por recurso.

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
- roles de cargos/posiciones;
- cargos/posiciones asignados a usuarios;
- roles directos de usuario;
- permisos directos de usuario;
- visualización de permisos efectivos y su origen;
- Áreas y Categorías;
- políticas de aprobación y demás configuración organizacional cuando corresponda;
- delegación/revocación del cierre y factura de una solicitud por parte de su solicitante.

La interfaz IAM debe distinguir las capacidades configurables de las capacidades base y por recurso. No debe presentar `requests:read` como revocable ni `requests:close` como permiso operativo vigente.

La vista de permisos efectivos debe explicar el origen, por ejemplo:

```text
Cargo Tesorero → Aprobador
Grupo Junta Directiva → Aprobador
Rol directo: Comprador
Asignación directa
```

La delegación de cierre pertenece al expediente de la solicitud, no al IAM organizacional global.

Una organización futura puede tener estructuras completamente distintas a la configuración inicial del PH.

## 7. Backend como autoridad

El frontend puede ocultar o mostrar acciones por UX, pero el backend es la autoridad final para:

- autorización;
- capacidades base;
- herencia Grupo → Rol → Permiso;
- herencia Cargo → Rol → Permiso;
- transiciones;
- población de participantes;
- acceso a documentos;
- decisiones;
- configuración IAM;
- política ambiental de cuentas técnicas;
- propiedad/capacidades por recurso como cancelación, corrección y cierre/factura;
- delegaciones de cierre/factura y su revocación;
- invariantes del tipo de solicitud durante una corrección;
- interrupción del flujo cuando un aprobador envía una solicitud a revisión.

Una operación sensible debe declarar una dependencia de permiso explícita o pasar por un servicio que aplique su regla de recurso. Las rutas de lectura del dashboard y seguimiento deben depender de `requests:read`, cuya resolución efectiva incluye el baseline para usuarios activos.

Las poblaciones de workflow (`users_with_permission`) deben utilizar la misma resolución de permisos efectivos que los endpoints. Un aprobador heredado por Cargo o Grupo debe ser tan elegible como uno con Rol directo, salvo exclusiones intrínsecas del flujo como el propio solicitante o la cuenta técnica en producción.

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

### Entrega de correo por ambiente

La selección del transporte de correo pertenece al backend y se centraliza en Settings. Los secretos de correo nunca pertenecen al frontend.

Política operativa vigente:

```text
Producción
Frontend: Vercel
Backend:  Render
Correo:   Brevo HTTPS API

Local / development
Frontend: localhost
Backend:  FastAPI/Docker local
Correo:   Gmail/Google Workspace SMTP
```

En producción se usa `EMAIL_MODE=brevo`. En desarrollo local se usa `EMAIL_MODE=smtp` con `smtp.gmail.com`, preferiblemente `465 + SSL` o alternativamente `587 + STARTTLS`, y una App Password cuando la cuenta Google lo requiera.

`EMAIL_MODE=console` es únicamente un modo de simulación/log y **no significa que un correo haya sido entregado**.

Las credenciales (`BREVO_API_KEY`, `SMTP_PASSWORD`) deben existir solo en secretos/configuración backend y nunca en Vercel, bundles Vite, repositorio o logs.

Debe existir una forma de probar el transporte de correo independientemente del workflow para diferenciar errores del proveedor de errores de negocio. El diagnóstico no debe imprimir secretos.

## 9. Contraseñas y sesiones

- nuevos hashes: Argon2 mediante `pwdlib` recomendado;
- hashes PBKDF2 legacy pueden verificarse temporalmente y deben migrar transparentemente a Argon2 después de un login correcto;
- JWT con expiración absoluta;
- timeout de inactividad;
- revocación por versión de sesión;
- fallos de autenticación no revelan si el usuario existe.

## 10. Historial y trazabilidad

Toda acción significativa debe poder reconstruirse con actor, fecha/hora, entidad, cambios, estado anterior/nuevo y motivo cuando aplique. Los eventos históricos relevantes son append-only.

Los cambios futuros de membresías, roles, cargos con herencia y permisos deben incorporarse al modelo de auditoría de acceso; una asignación de autorización no debe cambiar silenciosamente.

Una acción **Enviar a revisión** debe conservar el aprobador que la ejecutó, timestamp y comentario obligatorio; la corrección posterior debe conservar actor/fecha y generar una nueva versión/ronda del flujo según corresponda.

Cada delegación de cierre/factura debe conservar al solicitante que la creó, usuario delegado y timestamp. Cambiar o revocar una delegación debe conservar la fila histórica anterior mediante `revoked_at` y actor de revocación; no se reemplaza silenciosamente.

## 11. Evidencia documental

Los documentos son evidencia privada. Deben validarse por contenido real, almacenarse fuera del acceso público directo, descargarse con autorización backend, conservar versiones al sustituirse y registrar actor/fecha/motivo.

Una corrección no debe obligar a descartar o volver a cargar evidencia válida ya asociada a la solicitud únicamente porque el navegador no pueda prellenar un control de archivo.

La factura final y sus reemplazos forman parte del expediente. Solo un actor autorizado para el cierre/factura de esa solicitud puede cargarlos o sustituirlos.

## 12. Solicitudes, clasificación, seguimiento, cancelación y correcciones

Cada solicitud se clasifica por **Área + Categoría**. La clasificación histórica no cambia retroactivamente porque un catálogo se renombre, desactive o cambie.

El seguimiento de solicitudes es compartido: la identidad del solicitante no restringe la visibilidad de la solicitud para otros usuarios activos. Los permisos de acción continúan siendo independientes.

### Cancelación

Una solicitud abierta puede cancelarse únicamente por:

- su solicitante original; o
- la cuenta protegida Administrador del sistema identificada mediante `system_accounts`.

Tener `requests:create`, `requests:approve`, `config:manage`, un Rol, Grupo o Cargo concreto no autoriza por sí solo a cancelar una solicitud ajena.

Estados cancelables:

- `QUOTATION_VOTING`;
- `SUBMITTED`;
- `PENDING_APPROVAL`;
- `NEEDS_REVISION`;
- `APPROVED`.

`CLOSED`, `CANCELLED` y `REJECTED` no son cancelables. La cancelación exige motivo y conserva actor/timestamp/razón.

### Correcciones

La solicitud simple contiene una opción/cotización. `MULTI_QUOTE` mantiene la selección de cotización separada conceptualmente del proceso de aprobación.

**Corregir / reenviar es una capacidad por recurso.** Solo pueden ejecutarla:

- el solicitante original de la solicitud; o
- la cuenta protegida Administrador del sistema identificada mediante `system_accounts`.

`requests:create`, `requests:approve`, `config:manage`, un Grupo, Rol o Cargo concreto **no** autorizan a corregir una solicitud ajena. Los aprobadores/revisores que detecten un problema deben utilizar **Enviar a revisión** con comentario obligatorio; no deben editar la solicitud directamente.

La tarea personal `CORRECT_REQUEST` después de una revisión pertenece al **solicitante original**. El Administrador del sistema conserva la capacidad administrativa de corregir desde la solicitud, pero no sustituye al solicitante como responsable normal de la tarea de revisión.

**Corregir / reenviar MUST conservar el `request_type` original.** Un valor por defecto del frontend, un campo legacy o un payload incorrecto no puede convertir silenciosamente una solicitud entre `SIMPLE` y `MULTI_QUOTE`.

La pestaña SIMPLE/MULTI_QUOTE usada para crear una solicitud nueva es **solo estado de creación**. Al entrar en modo corrección, ese estado previo MUST descartarse: el editor debe derivar y fijar su tipo desde la solicitud que se está corrigiendo. La pestaña que estaba seleccionada antes de pulsar **Corregir / reenviar** no puede influir en el editor.

Reglas mínimas de corrección:

- `SIMPLE → corrección → SIMPLE`;
- `MULTI_QUOTE → corrección → MULTI_QUOTE`;
- cambiar deliberadamente entre tipos requiere una operación funcional explícita distinta;
- una corrección MULTI_QUOTE genera un `flow_id` nuevo;
- los votos e invitaciones vigentes de la ronda anterior dejan de ser estado activo;
- al reconstruir una ronda MULTI_QUOTE siempre se excluye al solicitante original de la población elegible, incluso si el Administrador del sistema fue quien ejecutó la corrección;
- los eventos históricos previos se conservan;
- los soportes existentes se conservan;
- mientras no exista una especificación de edición estructural de rondas, la corrección MULTI_QUOTE conserva la cantidad de opciones existente y permite editar su contenido.

La persistencia también debe mantener este invariant. Si un registro legacy conserva `request_type=SIMPLE` pero existe evidencia durable inequívoca de flujo múltiple —por ejemplo dos o más `quotation_options` o estado `QUOTATION_VOTING`— el sistema debe tratarlo como `MULTI_QUOTE` y reparar el dato mediante migración versionada/compatibilidad segura.

El backend debe hacer cumplir estas reglas incluso si la UI falla al hidratar el formulario.

## 13. Participantes y decisiones

La población elegible de una ronda debe congelarse/versionarse. Para votación de cotizaciones, las invitaciones de la ronda representan el snapshot de participantes hasta que exista un modelo explícito de rondas.

La población inicial debe resolverse por permisos efectivos, incluyendo herencia por Grupo y Cargo. Ningún título concreto es requisito del motor.

Para una ronda de aprobación:

- `response_rate = valid_responses / eligible_participants`;
- solo se resuelve aprobación/rechazo cuando `response_rate > 0.50`;
- `approval_rate = approvals / valid_decision_responses`;
- `rejection_rate = rejections / valid_decision_responses`;
- aprobar si `approval_rate > 0.50`;
- rechazar si `rejection_rate > 0.50`;
- empate o falta de mayoría permanece pendiente.

### Enviar a revisión

**Enviar a revisión es una interrupción del flujo, no una decisión sometida a mayoría.**

Cualquier aprobador que tenga un paso `PENDING` asignado puede detectar un problema y ejecutar `REVISION_REQUESTED` siempre que incluya un comentario de al menos tres caracteres indicando qué debe revisar/corregir el solicitante.

Al registrarse una sola solicitud válida de revisión:

1. la solicitud pasa inmediatamente a `NEEDS_REVISION`;
2. el paso del aprobador queda en `REVISION_REQUESTED` con su comentario;
3. las demás aprobaciones `PENDING/WAITING` de la ronda quedan `EXPIRED`;
4. el solicitante recibe la notificación con el comentario;
5. la tarea `CORRECT_REQUEST` se asigna al solicitante original;
6. ningún otro aprobador obtiene facultad para editar la solicitud por haber solicitado la revisión.

Aprobar/rechazar continúan sujetos a sus reglas de respuesta/mayoría. Las reglas de selección de cotización no se presumen iguales a las reglas de aprobación. Si el código legacy aún difiere de la fórmula de mayoría anterior, debe documentarse como deuda funcional y no presentarse como resuelto por un refactor de arquitectura.

## 14. Aprobado no significa cerrado: propiedad y delegación de cierre/factura

Una solicitud aprobada permanece en proceso hasta que se registre su factura y se cierre el expediente.

**Cerrar, adjuntar la factura final o corregir/reemplazar esa factura son capacidades por recurso.** Solo pueden ejecutarlas:

1. el solicitante original;
2. la cuenta protegida Administrador del sistema identificada mediante `system_accounts`; o
3. un usuario activo con una delegación vigente creada explícitamente por el solicitante para esa solicitud.

`requests:close`, `requests:create`, `requests:approve`, `config:manage`, Grupo, Rol o Cargo **no** autorizan por sí solos el cierre/factura de una solicitud ajena.

### Delegación

- únicamente el solicitante original puede crear, cambiar o revocar la delegación;
- el Administrador del sistema no necesita ser delegado y no puede convertirse en sustituto del solicitante para crear delegaciones ordinarias;
- solo puede existir **una delegación activa por solicitud**;
- cambiar de delegado revoca primero la delegación anterior y conserva su historial;
- el delegado debe ser un usuario activo y no una cuenta protegida de sistema;
- la delegación pertenece a una solicitud concreta y no concede autoridad sobre otras solicitudes;
- revocar una delegación elimina inmediatamente la autoridad futura del delegado;
- el solicitante conserva su autoridad aunque haya delegado;
- el Administrador del sistema conserva su excepción administrativa aunque exista o no delegación.

### Tarea personal de cierre

Cuando una solicitud está `APPROVED`, `CLOSE_REQUEST` aparece para:

- el solicitante original; y
- el delegado activo, si existe.

El Administrador del sistema puede cerrar desde la lista por excepción administrativa, pero no recibe todas las solicitudes aprobadas como tareas personales de Dashboard.

Una solicitud `CLOSED` permite reemplazar/corregir la factura únicamente a los mismos actores autorizados. La sustitución conserva versiones y exige motivo.

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

Las migraciones de compatibilidad pueden leer estructuras legacy una sola vez para convertirlas a relaciones IAM canónicas. Después del upgrade, el runtime no puede depender de esos nombres/flags legacy.

## 16. Seguridad y rendimiento

Como mínimo:

- default deny para capacidades mutables; `requests:read` es la excepción base explícita para usuarios activos;
- reglas de recurso explícitas para corrección, cancelación y cierre/factura en lugar de ampliar permisos globales;
- delegaciones por solicitud con un solo registro activo y trazabilidad de revocación;
- backend authoritative;
- rate limiting diferenciado;
- CORS restrictivo;
- secretos fuera del frontend/logs;
- ORM/consultas parametrizadas;
- validación real de archivos;
- paginación backend para colecciones crecientes, default 25 y máximo 100;
- evitar N+1;
- pool y query timeout configurables antes de escalar;
- una futura capa de scope puede limitar recursos si el producto incorpora organizaciones/tenancy, pero dentro de una misma organización el baseline actual permite seguimiento compartido de solicitudes;
- la elevación de la cuenta técnica fuera de producción debe depender de `ENVIRONMENT`, nunca de email/nombre/cargo;
- secretos de correo deben permanecer exclusivamente en configuración backend y no exponerse a Vite/Vercel.

## 17. Calidad y pruebas

Los cambios incluyen pruebas proporcionales al riesgo. Para IAM son obligatorias pruebas positivas y negativas de:

- permiso base `requests:read` para cualquier usuario activo sin rol/grupo/permisos asignados;
- un usuario con solo lectura puede abrir dashboard y consultar solicitudes de otros usuarios;
- la lectura base no concede crear, aprobar, cerrar una solicitud ajena ni configurar;
- `users_with_permission('requests:read')` incluye a todos los usuarios activos;
- permisos directos;
- herencia Grupo → Rol → Permiso;
- herencia Cargo/Posición → Rol → Permiso;
- origen de permisos efectivo distinguible entre Grupo, Cargo, Rol directo y asignación directa;
- cargo inactivo no concede permisos;
- cuenta técnica con todos los permisos atómicos activos en no producción;
- cuenta técnica incluida en poblaciones de aprobación/votación fuera de producción;
- cuenta técnica restringida a `config:manage` + `requests:read` en producción;
- endpoints `config:manage`;
- cambios de permisos efectivos sin reiniciar la app;
- login/respuesta de usuario exponiendo permisos efectivos coherentes con el ambiente.

Para cancelación son obligatorias pruebas que demuestren que el solicitante puede cancelar su solicitud abierta, otro usuario no puede hacerlo por tener permisos mutables, la cuenta técnica puede ejecutar la excepción administrativa y una solicitud cerrada no puede cancelarse.

Para correcciones son obligatorias pruebas que demuestren que:

- solo el solicitante original o el Administrador del sistema pueden corregir/reenviar;
- un tercero con `requests:create`, `requests:approve` o `config:manage` no puede corregir una solicitud ajena;
- el solicitante conserva la capacidad de corregir su propia solicitud aunque la autorización no dependa de un permiso global de edición;
- `request_type` no cambia;
- una MULTI_QUOTE reinicia su ronda;
- al reiniciar MULTI_QUOTE se excluye al solicitante original y no simplemente al actor que ejecutó la corrección;
- evidencia existente no se pierde por la hidratación del formulario;
- el tipo del editor no depende de la pestaña seleccionada previamente;
- un registro legacy con evidencia MULTI_QUOTE no se degrada por un default `SIMPLE` incorrecto.

Para **Enviar a revisión** son obligatorias pruebas que demuestren que:

- el comentario es obligatorio;
- una sola `REVISION_REQUESTED` válida interrumpe una ronda `MAJORITY` y lleva la solicitud a `NEEDS_REVISION`;
- las demás aprobaciones de la ronda quedan expiradas;
- el comentario queda persistido/auditado;
- la tarea de corrección aparece para el solicitante y no para los demás aprobadores;
- ningún aprobador adquiere `can_correct` por enviar una solicitud a revisión.

Para **cierre/factura y delegación** son obligatorias pruebas que demuestren que:

- el solicitante puede cerrar su solicitud aprobada sin depender de `requests:close`;
- el Administrador del sistema puede ejecutar la excepción administrativa;
- un tercero con `requests:close` legacy no puede cerrar una solicitud ajena;
- solo el solicitante puede crear/cambiar/revocar una delegación;
- un delegado activo puede cerrar y gestionar la factura de esa solicitud;
- la delegación no autoriza otras solicitudes;
- revocar la delegación retira inmediatamente `can_close` y la tarea `CLOSE_REQUEST`;
- solo existe una delegación activa por solicitud;
- el solicitante y el delegado reciben `CLOSE_REQUEST` cuando corresponde, pero el Administrador del sistema no recibe todas las solicitudes como tareas personales;
- reemplazar factura conserva evidencia anterior y exige motivo;
- `requests:close` queda inactivo/legacy y no es autoridad runtime.

Para correo/configuración son obligatorias comprobaciones que demuestren que:

- `EMAIL_MODE=smtp` requiere credenciales SMTP;
- `EMAIL_MODE=brevo` requiere su API key;
- el diagnóstico de correo usa el mismo transporte de la aplicación sin imprimir secretos;
- la documentación distingue claramente Google SMTP local de Brevo productivo;
- `console` no se presenta como entrega real.

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
- herencia de permisos por Grupo y Cargo utiliza relaciones configurables, no comparaciones de nombres;
- `requests:read` permanece disponible para todo usuario activo y no se filtra por identidad del solicitante;
- dashboard y seguimiento compartido están protegidos por pruebas cuando se modifica acceso/solicitudes;
- la política de cuenta técnica está probada en producción y no producción;
- invariantes de cancelación/corrección están protegidos en backend y probados;
- solo solicitante/Admin del sistema pueden corregir solicitudes y los aprobadores usan **Enviar a revisión** con comentario;
- una solicitud válida de revisión interrumpe la ronda y devuelve la tarea al solicitante;
- cierre/factura se autoriza únicamente por solicitante, Administrador del sistema o delegación activa por solicitud;
- solo el solicitante puede administrar la delegación de cierre/factura y su historial es trazable;
- `requests:close` no vuelve a convertirse en autoridad global de cierre;
- el editor de corrección deriva su tipo de la solicitud y no conserva la pestaña de creación previa;
- la configuración de correo por ambiente está documentada y puede diagnosticarse sin exponer secretos;
- migraciones son versionadas y desplegables;
- términos visibles coinciden con `docs/TERMINOLOGY.md`;
- README/prompt no reconstruyen conceptos retirados;
- HISTORY explica decisiones relevantes;
- CHANGELOG registra el entregable;
- CI y pruebas mencionadas realmente existen y pasan;
- deuda temporal queda explícita, con ruta de retiro.
