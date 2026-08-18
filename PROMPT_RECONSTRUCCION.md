# Prompt maestro de reconstrucción

> Constitución vigente: **2.6.0**.

Reconstruye una aplicación web lista para producción llamada **Flujo de Control de Gastos**, destinada a solicitar, evaluar, aprobar, ejecutar, dar seguimiento, devolver a revisión, corregir, cancelar y documentar gastos con evidencia verificable.

## Autoridad documental

Respeta, en orden:

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

La aplicación sirve para PH, empresas y otras organizaciones.

No introduzcas como dominio canónico:

- apartamentos;
- propietarios/copropietarios;
- residentes/arrendatarios;
- `Apartment`, `UserApartment`, `ApartmentChangeEvent`;
- `OwnershipRole`, `PersonType`, `apartment_number`;
- endpoints inmobiliarios.

Nombres como Junta Directiva, Administradora, Presidente, Vicepresidente, Tesorero, Procurement, Finance, IT o CFO son **datos configurables**, nunca condiciones de autorización runtime.

## 2. Terminología

- **Usuario**: cuenta del sistema.
- **Grupo**: conjunto configurable de usuarios que hereda Roles.
- **Rol**: conjunto reutilizable de Permisos.
- **Permiso**: capacidad atómica implementada por el producto.
- **Cargo/Posición**: estructura organizacional configurable que puede heredar Roles; su nombre no autoriza directamente.
- **Área**: unidad organizacional asociada al gasto.
- **Categoría**: naturaleza del bien/servicio.
- **Enviar a revisión**: decisión de un aprobador para detener el flujo y devolverlo al solicitante con comentarios.
- **Corregir / reenviar**: edición de una solicitud existente por su solicitante original o por el Administrador del sistema.

No uses Persona/Personas como nombre del módulo de cuentas ni Subárea como sinónimo funcional de Categoría.

## 3. IAM configurable

Persistencia canónica:

```text
permissions
roles
role_permissions
user_groups
group_members
group_roles
user_role_assignments
user_permissions
positions
user_positions
position_roles
system_accounts
```

Modelo:

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ capacidades base
```

Permisos atómicos iniciales:

```text
requests:read
requests:create
requests:approve
requests:close
config:manage
```

Para usuario activo:

```text
effective_permissions =
    baseline
  ∪ direct permissions
  ∪ direct-role permissions
  ∪ group-role permissions
  ∪ position-role permissions
```

### Baseline universal

`requests:read` es no revocable para usuarios activos y permite Inicio/Dashboard + Solicitudes + evidencia expuesta bajo lectura.

### Grupo y Cargo

Un mismo Rol puede heredarse por Grupo y Cargo:

```text
Rol Aprobador
  requests:approve

Cargo Presidente     → Aprobador
Cargo Tesorero       → Aprobador
Grupo Comité Compras → Aprobador
```

No autorices por `if title == ...`.

### Prohibiciones IAM

No autorices por:

- `UserRole.ADMIN/REQUESTER/APPROVER/VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure` persistidos;
- nombres de Grupos/Roles/Cargos;
- `BOARD_CODES`;
- emails fijos;
- IDs mágicos;
- conceptos inmobiliarios.

Los elementos legacy pueden existir como compatibilidad/migración, pero no son autoridad runtime.

## 4. Capacidades por recurso

No toda acción mutable se modela como permiso global.

### `can_cancel`

Solo solicitante original o Administrador del sistema, en estados cancelables.

### `can_correct`

Solo solicitante original o Administrador del sistema, en estados corregibles.

**`requests:create` no permite corregir ni cancelar una solicitud ajena.**

El backend debe devolver estas capacidades por solicitud y volver a validarlas al mutar.

## 5. Administrador del sistema por ambiente

La cuenta creada con `ADMIN_*` queda registrada como `TECHNICAL_ADMIN` en `system_accounts`.

### Producción

Solo cuando:

```env
ENVIRONMENT=production
```

sus permisos IAM máximos son:

```text
config:manage
requests:read
```

No puede ejercer:

```text
requests:create
requests:approve
requests:close
```

ni participar en aprobación/votación.

Excepciones administrativas por recurso:

```text
cancelar solicitud abierta
corregir / reenviar solicitud corregible
```

Estas facultades se identifican por `system_accounts`; no son permisos financieros.

### No producción

Para `ENVIRONMENT != production`, recibe todos los permisos atómicos activos para pruebas E2E y puede participar en workflows salvo reglas intrínsecas.

`RENDER=true` no sustituye `ENVIRONMENT=production` para autorización funcional.

## 6. Consola de Accesos

**Configuración → Accesos** administra:

- Usuarios;
- Grupos;
- Roles;
- Permisos;
- Cargos/Posiciones;
- miembros de Grupo;
- Roles heredados por Grupo;
- Roles heredados por Cargo;
- Cargos de Usuario;
- Roles directos;
- permisos directos;
- permisos efectivos y sus fuentes.

La pantalla legacy `AccessProfile/can_*` no es fuente autoritativa.

## 7. Usuario autenticado

Expón:

```text
permission_codes
```

Durante transición puedes derivar aliases UX:

```text
can_request   <- requests:create
can_approve   <- requests:approve
can_view      <- requests:read
can_configure <- config:manage
can_close     <- requests:close
```

Pero backend nunca autoriza con esos aliases.

`current_user()` debe recalcular permisos efectivos por request.

## 8. Dashboard y seguimiento universal

Todo usuario activo puede:

- abrir Inicio/Dashboard;
- ver métricas generales;
- abrir Solicitudes;
- consultar solicitudes de otros usuarios.

No filtres por `UserRole.REQUESTER` ni `requested_by == current_user.email`.

### KPIs superiores

Son informativos solamente:

```text
Acciones que requieren mi atención
Solicitudes en proceso
Cerradas en 24 horas
```

Renderízalos como contenido no interactivo; no como botones ni con `onClick`.

### Tareas personales

`pending_action_service.py` combina:

```text
permiso efectivo
+
asignación concreta
+
estado vigente
```

Códigos actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

No son permisos IAM.

Reglas:

```text
APPROVAL_DECISION
= requests:approve + Approval.PENDING asignado + PENDING_APPROVAL

QUOTATION_VOTE
= requests:approve + invitación vigente + QUOTATION_VOTING + sin voto

CORRECT_REQUEST
= solicitud propia NEEDS_REVISION

CLOSE_REQUEST
= requests:close + APPROVED
```

`CORRECT_REQUEST` no depende de `requests:create`; la propiedad de la solicitud determina la tarea.

### Interacción

```text
KPI superior          → información
fila pendiente        → modal contextual
Ver todas             → Solicitudes
```

Al abrir una fila consulta:

```text
GET /api/expenses/{request_id}/my-actions
```

y revalida tareas.

## 9. Aprobación y Enviar a revisión

Una aprobación contextual puede ofrecer:

```text
Aprobar
Rechazar
Enviar a revisión
```

### Enviar a revisión

`REVISION_REQUESTED` es una **interrupción inmediata**, no una respuesta que espere mayoría.

Requiere comentario de al menos 3 caracteres explicando qué debe revisar/corregir el solicitante.

Al registrar una sola revisión válida:

```text
approval actual      → REVISION_REQUESTED
request               → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester             → CORRECT_REQUEST
```

Persistir actor, timestamp y comentario.

Notificar al solicitante con ese comentario.

No conceder a ningún aprobador capacidad de editar la solicitud por haber pedido revisión.

Aprobar/Rechazar conservan su lógica de mayoría vigente; la fórmula constitucional completa sigue siendo deuda si el código todavía no la cumple.

La ruta autenticada del modal puede ser:

```text
POST /api/expenses/{request_id}/approval-decision
```

No expongas tokens bearer de links de correo al frontend autenticado.

## 10. Corrección y reenvío

**Solo** pueden corregir una solicitud existente:

```text
solicitante original
OR
Administrador del sistema registrado en system_accounts
```

Un tercero con `requests:create`, `requests:approve` o `config:manage` debe recibir 403.

Estados corregibles:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
REJECTED
```

No corregibles:

```text
CLOSED
CANCELLED
```

El endpoint:

```text
PUT /api/expenses/{request_id}/resubmit
```

debe autenticar al usuario y aplicar una regla por recurso (`can_correct_expense` o equivalente), no `require_permission('requests:create')`.

### Invariant SIMPLE/MULTI_QUOTE

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

La pestaña de creación no puede decidir el tipo de una corrección.

Reconoce MULTI_QUOTE si:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options.length >= 2
```

El backend devuelve 409 ante conversión real.

### MULTI_QUOTE corregida

- restaura opciones/evidencia;
- conserva cantidad de opciones por ahora;
- permite editar contenido;
- nuevo `flow_id`;
- invalida votos/invitaciones vigentes;
- conserva historial;
- genera nueva ronda con `requests:approve`;
- **excluye siempre al solicitante original**, aunque el Administrador del sistema ejecute la corrección.

`frontend/src/expense-form.jsx` es el formulario canónico.

## 11. Votación MULTI_QUOTE

Población:

```text
users_with_permission('requests:approve')
```

Incluye permisos por:

```text
permiso directo
rol directo
Grupo → Rol
Cargo → Rol
```

Excluye solicitante y aplica política productiva de cuenta técnica.

Las invitaciones persistidas representan snapshot de la ronda.

## 12. Cancelación

Solo:

```text
solicitante original
OR
system_accounts
```

Estados cancelables:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
```

No cancelables:

```text
CLOSED
CANCELLED
REJECTED
```

Exige motivo y persiste actor/fecha/razón.

## 13. Aprobado no significa cerrado

Cerrar/reemplazar factura requiere `requests:close` y evidencia.

Producción: cuenta técnica recibe DENY para cierre.

Conserva versiones de factura y auditoría de sustitución.

## 14. Área + Categoría

Son catálogos independientes con relación N:M configurable.

No reconstruyas Subárea como segundo nivel funcional.

## 15. Documentos

Admite PDF/JPEG/PNG/WEBP.

Valida MIME, firma real, tamaño y cuota. Usa nombres internos impredecibles y almacenamiento privado. Descarga mediante backend autorizado.

Una corrección reconoce soportes existentes sin prellenar `input[type=file]`.

## 16. Correo por ambiente

Producción:

```text
Frontend: Vercel
Backend: Render
Correo: Brevo HTTPS API
EMAIL_MODE=brevo
```

Local:

```text
Frontend: localhost
Backend: FastAPI/Docker
Correo: Gmail/Google Workspace SMTP
EMAIL_MODE=smtp
```

Nunca expongas `BREVO_API_KEY` ni `SMTP_PASSWORD` en frontend/Vercel/repositorio/logs.

Correo de aprobación debe decir:

```text
Aprobar
Rechazar
Enviar a revisión
```

El link `REVISION_REQUESTED` debe exigir comentario antes de confirmar y la notificación al solicitante debe incluirlo.

Mantén:

```bash
python -m scripts.test_email --to destino@example.com
```

## 17. Arquitectura FastAPI

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

- Pydantic Settings centralizado;
- `get_db()` por request;
- modelos/schemas fuera de routers cuando reutilizables;
- servicios para negocio;
- response models explícitos;
- SQLAlchemy síncrono en `def` o con offload;
- lifespan sin DDL/backfills;
- rutas canónicas antes de legacy;
- backend authoritative.

Rutas/capacidades canónicas relevantes:

```text
request_actions.py
revision_actions.py
cancellation_actions.py
quotation_actions.py
document_actions.py
financial_actions.py
my_actions.py
tracking.py
position_access.py
iam.py
iam_users.py
```

Servicios:

```text
iam_service.py
pending_action_service.py
approval_engine.py
quotation_service.py
```

Mientras `ExpenseTable` siga dentro de `main.jsx`, Vite puede mantener bridges mínimos para `can_cancel`, `can_correct` y montaje de componentes modulares. No uses transforms para wording/handlers internos del Dashboard: **Enviar a revisión** vive directamente en `home-dashboard.jsx`.

## 18. Passwords y sesiones

- Argon2 recomendado para hashes nuevos;
- PBKDF2 legacy compatible temporalmente y upgrade al login;
- JWT con expiración absoluta;
- timeout de inactividad;
- `session_version` para revocación;
- login no revela existencia del usuario.

## 19. Alembic / Docker / despliegue

Cadena vigente:

```text
20260817_0000 application baseline
→ 20260817_0001 IAM foundation
→ 20260817_0002 system accounts
→ 20260817_0003 MULTI_QUOTE request_type repair
→ 20260818_0004 position role inheritance
```

Feature 007 no agrega migración.

Inicio del contenedor:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Portabilidad:

- `*.sh text eol=lf`;
- Docker normaliza CRLF defensivamente;
- healthcheck backend antes de Nginx;
- bootstrap como módulo Python.

Antes de migraciones de producción: backup/snapshot + smoke en PostgreSQL/Neon preview/copia + plan de recuperación.

## 20. Testing obligatorio

### IAM

- baseline `requests:read`;
- permiso directo;
- Rol directo;
- Grupo → Rol;
- Cargo → Rol;
- Cargo inactivo no concede;
- `permission_sources()` explica origen;
- `users_with_permission()` reconoce Grupo/Cargo;
- política técnica producción/no-producción.

### Seguimiento

- usuario de solo lectura ve dashboard/solicitudes ajenas;
- KPIs superiores no interactivos;
- fila pendiente abre modal;
- `my-actions` revalida.

### Enviar a revisión

- comentario obligatorio;
- una sola `REVISION_REQUESTED` interrumpe MAJORITY;
- request → `NEEDS_REVISION`;
- otros pasos → `EXPIRED`;
- solicitante recibe `CORRECT_REQUEST`;
- otros aprobadores pierden acción vigente;
- frontend usa **Enviar a revisión** y deshabilita sin comentario válido.

### Corrección

- tercero con create/approve/config no puede corregir ajena;
- solicitante puede corregir propia por propiedad;
- Admin del sistema puede corregir;
- `can_correct` coherente;
- tipo no cambia;
- MULTI_QUOTE reinicia ronda/evidencia;
- solicitante original queda excluido de nueva votación.

### Cancelación

- requester sí;
- tercero no;
- system admin sí;
- cerrada no.

### CI

Normalmente CI ejecuta backend, frontend y Docker. Si GitHub Actions no tiene cuota, los mismos gates son obligatorios localmente y el run bloqueado **no se marca verde**.

## 21. Deuda legacy permitida explícitamente

Puede permanecer temporalmente:

```text
UserRole
users.title
can_*
AccessProfile
BOARD_CODES
/api/users legacy
main.jsx monolítico
domain-normalization.js
bridges Vite temporales
```

Ninguno puede convertirse en autoridad nueva.

Deuda funcional separada:

- fórmula completa de quorum/mayoría APPROVED/REJECTED;
- regla de empate de cotizaciones;
- edición estructural de opciones MULTI_QUOTE;
- outbox/retry persistente de correo.

`REVISION_REQUESTED` **sí** está definido: interrupción inmediata con comentario y handoff al solicitante.

## 22. Documentación obligatoria

Un cambio no está terminado hasta revisar/actualizar cuando aplique:

- Constitución;
- spec;
- plan;
- criterios;
- README;
- este prompt;
- docs técnicos/funcionales;
- terminología;
- HISTORY;
- CHANGELOG;
- PR.

No reconstruyas dominio inmobiliario retirado ni presentes deuda legacy como arquitectura objetivo.
