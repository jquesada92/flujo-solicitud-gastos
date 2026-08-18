# Prompt maestro de reconstrucción

> Constitución vigente: **2.4.0**.

Reconstruye una aplicación web lista para producción llamada **Flujo de Control de Gastos**, destinada a solicitar, evaluar, aprobar, ejecutar y documentar gastos con evidencia verificable.

## Autoridad documental

Lee y respeta en este orden:

1. `.specify/memory/constitution.md`
2. `specs/**/spec.md`
3. checklists/criterios de aceptación
4. `specs/**/plan.md`
5. este prompt
6. `README.md`
7. `docs/`
8. código existente

Si existe discrepancia, prevalece el artefacto de mayor prioridad.

## 1. Producto neutral

La aplicación debe servir para PH, empresas y otras organizaciones. No introduzcas como dominio canónico apartamentos, propietarios, residentes, arrendatarios ni estructuras exclusivas de un cliente.

Tampoco hardcodees estructuras organizacionales. Nombres como Junta Directiva, Administradora, Presidente, Tesorero, Procurement, Finance, IT o Gerente pueden existir como datos configurados por un cliente, nunca como condiciones de runtime.

## 2. Terminología

Usa:

- **Usuario**: cuenta del sistema.
- **Grupo**: conjunto configurable de usuarios.
- **Rol**: conjunto configurable de permisos.
- **Permiso**: capacidad atómica implementada por el producto.
- **Cargo/Posición**: metadato descriptivo que no concede permisos.
- **Área**: unidad organizacional asociada al gasto.
- **Categoría**: naturaleza del bien/servicio.

No uses Persona/Personas como nombre del módulo de cuentas. No uses Subárea para representar Categoría.

## 3. IAM configurable

Implementa:

```text
Usuario → Grupo → Rol → Permiso
       ↘ Rol directo
       ↘ Permiso directo
       ↘ Cargo/Posición descriptivo
       ↘ Baseline del producto
```

Persistencia:

- `permissions`
- `roles`
- `role_permissions`
- `user_groups`
- `group_members`
- `group_roles`
- `user_role_assignments`
- `user_permissions`
- `positions`
- `user_positions`
- `system_accounts`

Permisos iniciales:

- `requests:read`
- `requests:create`
- `requests:approve`
- `requests:close`
- `config:manage`

`requests:read` es baseline no revocable para todo usuario activo y autenticado. Para las demás capacidades, la organización configura desde la UI grupos, roles, cargos, membresías y asignaciones y aplica default DENY si no existe ALLOW.

### Prohibiciones

No autorices por:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure` como fuente de verdad;
- nombres de grupos/roles/cargos;
- emails fijos;
- IDs mágicos;
- listas como `BOARD_CODES`.

Los campos legacy pueden existir solo como puente de compatibilidad y deben derivarse de IAM, no al revés.

## 4. Cuenta técnica y política por ambiente

La cuenta creada con `ADMIN_*` debe quedar identificada como `TECHNICAL_ADMIN` en `system_accounts`.

La política se decide por `SystemAccount + ENVIRONMENT`, nunca por email/nombre/cargo/rol legacy.

### Producción

Solo cuando:

```env
ENVIRONMENT=production
```

la cuenta técnica queda restringida como permisos IAM a:

```text
config:manage
requests:read
```

En producción debe ser imposible que ejerza:

```text
requests:create
requests:approve
requests:close
```

incluso si alguien intenta asignarlos accidentalmente mediante un grupo, rol o permiso directo. Tampoco debe participar en poblaciones financieras de aprobación o votación.

Como excepción explícita de administración del ciclo de vida, el Administrador del sistema puede cancelar una solicitud abierta. Esa facultad se valida por `system_accounts`, no por un permiso financiero, email, cargo o `UserRole.ADMIN`.

### No producción

Para cualquier `ENVIRONMENT` distinto de `production`, incluidos local, development/dev, test, staging y preview, la cuenta técnica debe recibir **todos los permisos atómicos activos del producto** para probar el sistema end-to-end.

Debe poder:

- crear/corregir solicitudes;
- consultar;
- aprobar y votar;
- entrar en poblaciones de aprobación/votación cuando corresponda;
- subir/reemplazar factura y cerrar;
- cancelar solicitudes abiertas;
- administrar configuración.

No persistas físicamente todos esos permisos solo para testing si puede resolverse como política ambiental; el mismo dataset debe volverse restrictivo al ejecutar con `ENVIRONMENT=production`.

`RENDER=true` puede activar validaciones fuertes de secretos y CORS, pero no debe activar por sí mismo la política funcional de producción. Separa `is_production_environment` de validaciones de runtime alojado.

## 5. Interfaz de Accesos

Dentro de Configuración debe existir una consola gráfica para:

- Usuarios;
- Grupos;
- Roles;
- Permisos;
- Cargos;
- membresías;
- roles de grupo;
- roles directos;
- permisos directos;
- cargos de usuario;
- permisos efectivos y su origen.

La cuenta técnica debe aparecer identificada y la UI IAM debe poder explicar si un permiso proviene de política productiva o de acceso de prueba no-productivo.

No requieras editar archivos o variables para crear una estructura empresarial nueva.

## 6. Contrato del usuario autenticado

Expón los permisos efectivos actuales en:

```text
permission_codes
```

Durante la transición del frontend legacy deriva también:

```text
can_request   <- requests:create
can_approve   <- requests:approve
can_view      <- requests:read
can_configure <- config:manage
can_close     <- requests:close
```

Estos aliases nunca autorizan el backend.

El login debe calcular y serializar los permisos efectivos antes del primer render. `current_user()` debe volver a calcularlos por request para reflejar cambios inmediatos.

Migra progresivamente el frontend a `permission_codes`; retira bypasses visuales como `user.role === "ADMIN"` y `canClose={true}`.

Para acciones dependientes de una solicitud concreta, el backend puede exponer capacidades por recurso, por ejemplo `can_cancel`. La UI debe consumirlas en vez de reconstruir reglas de propiedad localmente.

## 7. Clasificación Área + Categoría

Área y Categoría son catálogos independientes con relación N:M configurable.

```text
Área: Administración, Operaciones, IT, Marketing
Categoría: Equipos, Servicios/Consultoría, Insumos, Licencias
```

Una categoría `Equipos` puede habilitarse para múltiples áreas sin duplicarse.

## 8. Solicitudes

Cada solicitud conserva como mínimo:

- `request_id` inmutable;
- `flow_id`;
- `display_id`;
- solicitante;
- Área;
- Categoría;
- título;
- descripción/justificación;
- urgencia;
- tipo SIMPLE/MULTI_QUOTE;
- estado;
- documentos;
- historial;
- decisiones;
- timestamps.

Crear/corregir/cargar soporte requiere `requests:create`.

### Seguimiento universal

Todo usuario activo debe poder abrir:

```text
Inicio / Dashboard
Solicitudes
```

y consultar solicitudes de otros usuarios para dar seguimiento. `GET /api/expenses` y `GET /api/expenses/dashboard` deben depender de `requests:read`, cuyo resultado efectivo incluye el baseline.

La lectura universal no concede creación, aprobación, cierre, configuración ni cancelación ajena.

### Cancelación

Una solicitud abierta solo puede ser cancelada por:

```text
solicitante original
OR
Administrador del sistema persistido en system_accounts
```

No uses `requests:create`, `requests:approve`, `config:manage`, cargo, grupo o rol como sustituto de esta regla.

Estados cancelables:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
```

Estados no cancelables:

```text
CLOSED
CANCELLED
REJECTED
```

La cancelación exige motivo, registra `cancelled_at`, `cancelled_by` y `cancellation_reason`, y expira aprobaciones abiertas.

El listado canónico debe devolver `can_cancel` por solicitud. El endpoint de cancelación vuelve a validar siempre la regla aunque la UI haya ocultado/mostrado correctamente el botón.

### Formulario canónico

El formulario de solicitudes debe vivir en un módulo mantenible, actualmente:

```text
frontend/src/expense-form.jsx
```

No uses el estado de una pestaña de creación como fuente de verdad de una corrección.

El componente debe calcular:

```text
effectiveRequestType = draft ? resolveRequestType(draft) : requestType
```

Y ese valor MUST gobernar conjuntamente:

- layout/renderizado;
- validaciones;
- `request_type` del payload;
- campos SIMPLE;
- `quotation_options` MULTI_QUOTE;
- carga posterior de soportes.

### Correcciones

`Corregir / reenviar` debe preservar siempre el tipo canónico:

```text
SIMPLE      -> SIMPLE
MULTI_QUOTE -> MULTI_QUOTE
```

**La pestaña SIMPLE/MULTI_QUOTE seleccionada antes del clic solo pertenece al modo de creación y MUST descartarse al entrar en corrección.** El editor debe derivar su tipo desde la solicitud seleccionada. Si SIMPLE estaba activa y el usuario corrige una MULTI_QUOTE, debe abrir directamente el editor múltiple sin que el usuario seleccione antes esa pestaña.

Mientras exista compatibilidad con datos legacy, considera MULTI_QUOTE si existe cualquiera de estas señales durables:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options.length >= 2
```

El backend debe rechazar con `409 Conflict` un intento real de convertir el tipo canónico durante `resubmit`, aunque el frontend envíe un valor por defecto incorrecto.

Para una corrección MULTI_QUOTE:

- el layout visible MUST ser **Opciones para votación**, no el formulario SIMPLE;
- muestra `Tipo de solicitud: Múltiples cotizaciones` como dato de solo lectura;
- restaura en UI las opciones existentes;
- conserva los attachments existentes como evidencia y representa esa evidencia con metadata, no intentando prellenar `input[type=file]`;
- permite editar proveedor, monto, URL y observaciones dentro de cada opción;
- conserva por ahora la cantidad de opciones;
- genera un `flow_id` nuevo;
- invalida/elimina votos e invitaciones vigentes de la ronda anterior;
- conserva eventos históricos append-only;
- crea nuevas invitaciones desde `requests:approve`;
- vuelve a `QUOTATION_VOTING`.

Una corrección MULTI_QUOTE NO debe mostrar como estructura principal:

- un único `Monto (USD)` de solicitud;
- un único `Proveedor`;
- un único `URL del producto o servicio`;
- un único input de cotización.

No conviertas SIMPLE ↔ MULTI_QUOTE como efecto colateral de una corrección. Si el producto requiere esa conversión, especifícala como una operación distinta.

### Integración temporal del monolito

Mientras `main.jsx` conserve una definición histórica de `ExpenseForm`, `vite.config.js` puede realizar una extracción estructural temporal:

1. importar `ExpenseForm` desde `./expense-form.jsx`;
2. eliminar del bundle la función legacy completa.

No inyectes una `key` o parches de montaje por coincidencias exactas de whitespace; el componente modular ya rehidrata desde `draft.request_id`/`flow_id`.

Mientras la tabla legacy siga infiriendo cancelación mediante estados y `can_request`, el build puede sustituir ese guard por `x.can_cancel` usando un patrón semántico tolerante a whitespace y validado para que falle si no encuentra exactamente la frontera esperada.

Estas transformaciones son deuda temporal y deben retirarse cuando `main.jsx` importe directamente componentes modulares.

## 9. Cotizaciones

SIMPLE exige proveedor, monto y soporte.

MULTI_QUOTE mantiene varias opciones. La población de votación se obtiene desde usuarios efectivos con `requests:approve`, excluyendo al solicitante.

- Producción: cuenta técnica excluida de permisos financieros.
- No producción: cuenta técnica puede participar para pruebas si no queda excluida por otra regla del flujo.

Congela/versiona los participantes de cada ronda. No inventes reglas de quorum/empate no especificadas.

## 10. Aprobaciones

Los participantes se seleccionan por permisos/políticas persistidas, nunca por cargo hardcodeado.

La Constitución vigente define la regla funcional objetivo de quorum y mayoría. Si el motor legacy todavía difiere, documenta la deuda y no afirmes que está resuelta por cambios IAM.

## 11. Cierre y factura

`APPROVED` no significa `CLOSED`.

Subir/reemplazar factura y cerrar requiere `requests:close`.

- Producción: cuenta técnica debe recibir 403.
- No producción: cuenta técnica puede cerrar para pruebas end-to-end.

Conserva versiones anteriores de facturas y registra motivo/actor/timestamp al sustituir.

## 12. Arquitectura FastAPI

Usa:

```text
app/
├── api/
├── core/
├── models/
├── schemas/
├── services/
├── application.py
└── main.py
```

Reglas:

- Pydantic Settings centralizado.
- `get_db()` entrega una sesión por request y siempre la cierra.
- modelos SQLAlchemy fuera de routers.
- schemas reutilizables fuera de routers.
- response models explícitos para respuestas sensibles.
- dependencias FastAPI para autorización.
- `lifespan` nunca ejecuta DDL/backfills/seeds de negocio.
- Alembic para migraciones versionadas.
- SQLAlchemy síncrono: rutas con DB/filesystem bloqueante deben ser `def` o hacer offload explícito.
- invariantes de negocio como preservar `request_type` y autorizar cancelación por propiedad deben vivir también en backend, no solo en estado React.

## 13. Passwords y JWT

- Argon2 mediante `pwdlib.PasswordHash.recommended()` para hashes nuevos.
- Compatibilidad temporal con PBKDF2 legacy.
- Login PBKDF2 exitoso migra el hash a Argon2.
- JWT con `sub`, versión de sesión, `iat`, `exp`.
- timeout de inactividad.
- cambios sensibles pueden revocar sesiones.

## 14. Documentos

Admite PDF/JPEG/PNG/WEBP. Valida MIME, firma real, tamaño, cuota total y nombre interno impredecible. El disco es privado y la descarga pasa por autorización backend.

Una corrección debe reconocer soportes existentes sin exigir que un `<input type="file">` del navegador pueda prellenarse.

## 15. Correo

Centraliza toda la configuración en `Settings` y conserva un único servicio de plantillas/entrega con transporte seleccionable por `EMAIL_MODE`.

### Producción

La arquitectura productiva es:

```text
Frontend: Vercel
Backend:  Render
Correo:   Brevo HTTPS API
```

Usa en Render/backend:

```env
ENVIRONMENT=production
EMAIL_MODE=brevo
EMAIL_FROM=<REMITENTE_VERIFICADO>
BREVO_API_KEY=<SECRET>
BREVO_SENDER_NAME=Gestión de Solicitudes
```

Nunca expongas `BREVO_API_KEY` en Vite/Vercel.

### Local / development

La aplicación local debe poder enviar correo real mediante Gmail/Google Workspace SMTP:

```env
ENVIRONMENT=development
EMAIL_MODE=smtp
EMAIL_FROM=<CUENTA_GOOGLE>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=<CUENTA_GOOGLE>
SMTP_PASSWORD=<APP_PASSWORD_GOOGLE>
```

También puede usarse `587 + starttls`.

No uses ni versionees la contraseña normal de Google. Usa App Password cuando la cuenta Google lo requiera y mantenla únicamente en `backend/.env`.

`EMAIL_MODE=console` es solo un fallback de desarrollo/test sin entrega real; nunca debe interpretarse como correo enviado.

Debe existir un diagnóstico independiente del workflow que use exactamente el mismo `Settings` y servicio de correo:

```bash
python -m scripts.test_email --to destino@example.com
```

Así se valida primero el transporte y luego las notificaciones SIMPLE/MULTI_QUOTE. Un fallo de entrega puede registrarse sin revertir el workflow, por lo que la observabilidad de correo y el estado de aprobación deben poder investigarse por separado.

## 16. Migraciones, Docker y despliegue

No uses `Base.metadata.create_all()` ni `migrate_schema()` en lifespan productivo.

Secuencia canónica:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Cadena Alembic vigente:

```text
0000 application baseline
→ 0001 IAM foundation
→ 0002 system accounts
→ 0003 backfill MULTI_QUOTE request_type
```

`0003` repara filas históricas con evidencia múltiple y default `SIMPLE` incorrecto. Feature 005 de seguimiento/cancelación no agrega migración de esquema ni debe crear un backfill basado en flags legacy.

No ejecutes el bootstrap como `python scripts/bootstrap_admin.py`.

Portabilidad:

- `*.sh text eol=lf` en `.gitattributes`;
- normalización defensiva CRLF dentro de imagen;
- healthcheck real antes de Nginx;
- CI valida entrypoint e import de `scripts.bootstrap_admin`.

Producción debe declarar explícitamente:

```env
ENVIRONMENT=production
```

No uses ese valor en un entorno donde se pretenda probar todas las funciones con la cuenta técnica.

## 17. Testing

Usa tests unitarios y `FastAPI TestClient`.

Matriz IAM mínima:

- usuario activo obtiene baseline `requests:read` aunque no tenga asignaciones;
- no-producción: admin técnico obtiene todos los permisos activos;
- no-producción: login expone `permission_codes` completos y `can_close=true` si el permiso está activo;
- no-producción: admin técnico puede entrar en población `requests:approve`;
- producción: admin técnico obtiene solo config/read;
- producción: asignarle close accidentalmente sigue resultando DENY;
- producción: endpoint de cierre devuelve 403;
- producción: admin técnico queda fuera de población de aprobación;
- usuario sin config obtiene 403 en IAM;
- Grupo→Rol→Permiso cambia acceso inmediatamente;
- permiso directo es aditivo;
- rol técnico no se edita desde UI.

Matriz de seguimiento/cancelación mínima:

- usuario activo sin roles puede cargar dashboard;
- usuario activo puede ver solicitud creada por otro usuario;
- lectura baseline no concede cierre ni otras mutaciones;
- solicitante recibe `can_cancel=true` para su solicitud abierta;
- usuario ajeno recibe `can_cancel=false`;
- usuario ajeno con `requests:create` recibe 403 al cancelar;
- solicitante puede cancelar durante `QUOTATION_VOTING`;
- cuenta técnica puede cancelar cualquier solicitud abierta;
- `CLOSED`, `CANCELLED` y `REJECTED` no pueden cancelarse;
- frontend build sustituye el guard legacy de cancelación por `x.can_cancel`.

Matriz de correcciones mínima:

- MULTI_QUOTE corregida permanece MULTI_QUOTE;
- con la pestaña SIMPLE activa antes de corregir, una MULTI_QUOTE abre como múltiple;
- un `draft` en `QUOTATION_VOTING` renderiza `Opciones para votación`;
- un registro legacy `request_type=SIMPLE` con evidencia múltiple se trata/repara como MULTI_QUOTE;
- `effectiveRequestType` gobierna render y payload en el formulario modular;
- opciones y soportes existentes se restauran;
- `flow_id` cambia;
- votos vigentes se limpian;
- invitaciones se reemplazan;
- MULTI_QUOTE → SIMPLE por `resubmit` devuelve 409;
- frontend build falla si la extracción del ExpenseForm legacy no puede aplicarse;
- topología Alembic exige `0003` como único head.

Matriz de correo mínima:

- `EMAIL_MODE=smtp` requiere credenciales SMTP;
- local documenta Google SMTP 465/SSL y App Password;
- producción documenta Brevo en Render;
- secretos de correo no aparecen en frontend/Vercel;
- `scripts.test_email` usa el transporte real configurado sin imprimir secretos.

CI ejecuta Python compile, backend tests, frontend build y builds/smoke tests Docker.

## 18. Seguridad

- backend authoritative;
- secretos fuera del frontend/logs/repositorio;
- CORS explícito;
- rate limiting diferenciado;
- ORM/consultas parametrizadas;
- archivos privados;
- default deny para capacidades mutables de usuarios operativos;
- `requests:read` baseline para usuarios activos;
- no bypass por `UserRole.ADMIN`;
- no autorización por cargo;
- cancelación ajena no se concede por `requests:create`;
- Administrador del sistema para cancelación se identifica por `system_accounts`;
- política ampliada de cuenta técnica únicamente fuera de producción y basada en ambiente, salvo la excepción explícita de cancelación administrativa.

## 19. Auditoría

Eventos significativos deben conservar actor, tiempo, entidad, cambios y motivo. La evolución del IAM debe incorporarse a auditoría para que cambios de roles/grupos/permisos no sean silenciosos.

Una corrección debe conservar el historial de rondas anteriores aunque limpie el estado vigente de votos/invitaciones.

Una cancelación debe conservar `cancelled_at`, `cancelled_by` y `cancellation_reason` y expirar decisiones abiertas sin borrar evidencia histórica.

## 20. Documentación obligatoria

Un cambio no está terminado hasta revisar y actualizar cuando aplique Constitución, spec, plan, criterios de aceptación, README, este prompt, documentación técnica/funcional, terminología, HISTORY, CHANGELOG y PR.

## 21. Deuda permitida solo si está explícita

Durante la transición pueden existir `UserRole`, `can_*`, router legacy `/api/users`, `main.jsx` monolítico, `domain-normalization.js` y `modularExpenseFormPlugin`.

`frontend/src/expense-form.jsx` ya es la implementación canónica del formulario; no reconstruyas el esquema anterior de parchear granularmente el ExpenseForm legacy. El plugin temporal retira la definición histórica del bundle y, mientras la tabla siga legacy, adapta el guard de cancelación para consumir `can_cancel`.

No presentes ninguna deuda legacy como arquitectura objetivo. No debe ser fuente de autorización ni de invariantes críticos sin defensa backend.

No reconstruyas funcionalidad inmobiliaria ni vuelvas a introducir roles/cargos organizacionales hardcodeados.