# Prompt maestro de reconstrucción

> Constitución vigente: **2.10.0**.

Reconstruye una aplicación web lista para producción llamada **Flujo de Control de Gastos**, destinada a solicitar, evaluar, aprobar, votar, dar seguimiento, devolver a revisión, corregir, cancelar, cerrar y documentar gastos con trazabilidad y evidencia verificable.

## Autoridad documental

Respeta, en orden:

1. `.specify/memory/constitution.md`
2. `specs/**/spec.md`
3. checklists/criterios de aceptación
4. `specs/**/plan.md`
5. este prompt
6. `README.md`
7. `docs/`
8. código legacy existente

Si existe discrepancia, prevalece el artefacto de mayor prioridad.

## 1. Producto neutral

Debe servir para PH, empresas y otras organizaciones. No reconstruyas como dominio canónico apartamentos, propietarios/copropietarios, residentes/arrendatarios, `Apartment`, `UserApartment`, `OwnershipRole`, `PersonType`, `apartment_number` ni endpoints inmobiliarios.

Nombres como Junta Directiva, Administración, Presidente, Vicepresidente, Tesorero, Procurement, Finance, IT o CFO son **datos configurables**, nunca condiciones runtime.

## 2. Terminología

Usa:

- Usuario
- Grupo
- Rol
- Permiso
- Cargo/Posición
- Área
- Categoría
- Accesos
- Enviar a revisión
- Corregir / reenviar
- Delegación de cierre/factura

No uses **Persona/Personas** como módulo de cuentas ni **Subárea/Subcategoría** como equivalente de Categoría.

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
       ↘ capacidades/delegaciones por recurso
```

Permisos vigentes:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage  # system-only
```

`requests:close` puede existir como registro legacy inactivo, pero no autoriza cierre/factura ni debe aparecer como capacidad operativa configurable.

Para usuario activo ordinario:

```text
effective_permissions =
    {requests:read}
  ∪ direct permissions
  ∪ direct-role permissions
  ∪ group-role permissions
  ∪ position-role permissions
  - {config:manage}
```

`requests:read` es baseline no revocable. `config:manage` nunca se vuelve efectivo para usuario ordinario aunque exista una asignación legacy.

Nunca autorices por `UserRole`, `can_*` legacy, `BOARD_CODES`, emails fijos, IDs mágicos o nombres/códigos de Cargo, Grupo o Rol.

## 4. Configuración y Accesos

**No reconstruyas Usuarios/Personas ni Organigrama como pantallas independientes.**

Navegación canónica:

```text
System Admin
→ Accesos
→ Áreas
→ Reglas
→ Auditoría / demás configuración técnica

Usuario con config:read
→ Accesos (solo lectura)
→ Áreas (solo lectura salvo areas:manage)
→ Reglas (solo lectura)
→ Auditoría (solo lectura)

Usuario con areas:manage sin config:read
→ Áreas solamente
```

### Accesos

`Configuración → Accesos` es la única superficie para:

- crear/activar/inactivar usuarios;
- datos básicos de acceso;
- Grupos y miembros;
- Roles;
- Permisos;
- Cargos/Posiciones;
- asignación de Cargos a Usuarios;
- Roles heredados por Grupo/Cargo;
- Roles directos;
- Permisos directos;
- permisos efectivos y fuentes.

Código legacy de `people` / `organization` puede existir internamente durante la migración, pero no aparece en navegación normal ni vuelve a ser fuente de verdad.

### Lectura de configuración

`config:read` permite consultar configuración sin mutarla. No concede `config:manage`, no concede `areas:manage` y no permite POST/PUT/PATCH/DELETE por sí solo.

### Gestión de Áreas

`areas:manage` es configurable por Rol/Grupo/Cargo/usuario y protege mutaciones de `/api/areas`.

### Administración técnica

`config:manage` es system-only y requiere identidad persistida en `system_accounts`.

## 5. Navegación global desde Accesos

La consola IAM se monta actualmente mediante `#access-management`, pero no puede bloquear la navegación global.

Desde Accesos deben responder normalmente:

```text
Inicio
Solicitudes
Facturas
Auditoría
Configuración
Salir
```

Al seleccionar una pantalla distinta de Accesos, retira explícitamente `#access-management` y continúa la navegación **en el mismo clic**.

La regla también aplica cuando el destino ya era la pestaña React subyacente. Por ejemplo, Accesos se abrió desde Inicio y el usuario vuelve a pulsar Inicio.

Abrir/cerrar solamente el dropdown **Configuración** no cierra Accesos; seleccionar una opción navegable dentro de ese menú sí.

Mientras exista el shell legacy, carga `frontend/src/access-navigation-bridge.js` antes de `main.jsx`.

## 6. Área + Categoría

Contrato canónico de solicitud, API, ORM y base de datos:

```text
expense_area
expense_category
```

No reconstruyas `expense_type` / `expense_subcategory` como nombres vigentes. Solo pueden existir como aliases de compatibilidad temporal.

Área y Categoría son catálogos independientes con relación configurable N:M.

Migración vigente:

```text
20260819_0008_expense_area_category_columns.py
```

Debe renombrar físicamente:

```text
expense_type        → expense_area
expense_subcategory → expense_category
```

sin perder datos.

## 7. Capacidades por recurso

`GET /api/expenses` expone:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

### `can_cancel`

```text
estado cancelable
AND (solicitante original OR system_accounts)
```

### `can_correct`

```text
estado corregible
AND (solicitante original OR system_accounts)
```

### `can_close`

```text
status ∈ {APPROVED, CLOSED}
AND (
  solicitante original
  OR system_accounts
  OR delegación activa de esa solicitud
)
```

### `can_delegate_close`

Solo el solicitante original administra la delegación ordinaria.

El backend vuelve a validar todas las mutaciones aunque el frontend muestre botones.

## 8. Cuenta técnica / Administrador del sistema

La cuenta creada con `ADMIN_*` queda persistida como `TECHNICAL_ADMIN` en `system_accounts`.

`/api/auth/login` y `/api/auth/me` exponen `is_system_account` para UX. Nunca derives esa identidad de `UserRole.ADMIN`, Cargo, email o nombre.

### Producción

Solo `ENVIRONMENT=production` activa segregación funcional.

IAM máximo:

```text
config:manage
config:read
areas:manage
requests:read
```

No participa en aprobación/votación ni recibe permisos empresariales financieros.

Excepciones administrativas por recurso:

```text
cancelar solicitud abierta
corregir / reenviar solicitud corregible
gestionar cierre/factura cuando el estado lo permita
```

### No producción

`ENVIRONMENT != production` puede conceder todos los permisos IAM activos al System Admin para testing E2E.

`RENDER=true` no sustituye `ENVIRONMENT=production`.

## 9. Usuario autenticado

Expón al menos:

```text
permission_codes
is_system_account
```

Los aliases UX legacy (`can_request`, `can_approve`, `can_view`, `can_configure`, `can_close`) pueden existir temporalmente, pero no autorizan backend.

## 10. Dashboard y seguimiento universal

Todo usuario activo puede abrir Inicio/Dashboard y Solicitudes mediante `requests:read`.

Tareas contextuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

No son permisos IAM.

```text
APPROVAL_DECISION
= requests:approve + Approval.PENDING asignado + PENDING_APPROVAL

QUOTATION_VOTE
= requests:approve + invitación vigente + QUOTATION_VOTING + sin voto

CORRECT_REQUEST
= solicitud propia NEEDS_REVISION

CLOSE_REQUEST
= solicitud APPROVED + (solicitante original OR delegado activo)
```

## 11. Aprobación y Enviar a revisión

Una aprobación contextual ofrece:

```text
Aprobar
Rechazar
Enviar a revisión
```

`REVISION_REQUESTED` interrumpe la ronda y requiere comentario útil de al menos 3 caracteres.

```text
approval actual       → REVISION_REQUESTED
request                → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester              → CORRECT_REQUEST
```

Persiste actor/timestamp/comentario y notifica al solicitante. No concede edición al aprobador.

## 12. Corrección y reenvío

Solo:

```text
solicitante original
OR
Administrador del sistema en system_accounts
```

Un tercero con `requests:create`, `requests:approve`, `config:read` o `config:manage` recibe 403.

Estados corregibles:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
REJECTED
```

No corregibles: `CLOSED`, `CANCELLED`.

Invariant:

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

`frontend/src/expense-form.jsx` es el formulario canónico.

## 13. Votación MULTI_QUOTE

Población:

```text
users_with_permission('requests:approve')
```

Incluye permiso directo, Rol directo, Grupo→Rol y Cargo→Rol. Excluye solicitante y aplica la política de cuenta técnica.

Las invitaciones persistidas representan el snapshot vigente.

## 14. Cancelación

Solo solicitante original o `system_accounts`.

Estados cancelables:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
NEEDS_REVISION
APPROVED
```

No cancelables: `CLOSED`, `CANCELLED`, `REJECTED`.

Exige motivo y auditoría.

## 15. Cierre, factura y delegación

`APPROVED` no equivale a `CLOSED`.

Cerrar, adjuntar factura o reemplazar/corregir factura es una capacidad por recurso:

```text
solicitante original
OR
Administrador del sistema
OR
delegado activo creado por el solicitante para ESA solicitud
```

`requests:close` no participa.

Persistencia:

```text
expense_closure_delegations
```

Reglas:

- solo solicitante original crea/cambia/revoca;
- una sola delegación activa por solicitud;
- delegado activo, distinto del solicitante y no `system_accounts`;
- cambiar delegado revoca primero el anterior;
- historial no se borra;
- revocar elimina inmediatamente autoridad futura.

## 16. Documentos

Permite PDF/JPEG/PNG/WEBP con validación MIME+firma+tamaño+cuota, almacenamiento privado y descarga autorizada por backend.

Reemplazar factura conserva la anterior y registra actor/motivo.

## 17. Correo por ambiente

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
Correo: Gmail/Workspace SMTP
EMAIL_MODE=smtp
```

Nunca expongas secretos en frontend, Vercel, repositorio o logs.

Mantén `python -m scripts.test_email --to destino@example.com` para diagnóstico.

### Notificaciones IAM obligatorias

Al crear usuario activo, la invitación con contraseña temporal incluye:

```text
Cargo(s) activos
Permisos efectivos actuales
```

Cuando cambia realmente `position_ids`, recalcula `effective_permission_codes()` y envía **Actualización de cargo y permisos**. Guardar el mismo Cargo no duplica correo.

## 18. Arquitectura FastAPI

- `APIRouter` por dominio/capacidad;
- modelos SQLAlchemy fuera de routers;
- schemas Pydantic reutilizables;
- servicios para lógica de negocio;
- `get_db()` por request;
- Settings centralizados;
- `lifespan` sin migraciones;
- Alembic antes del proceso ASGI;
- response models explícitos;
- tests HTTP para autorización y contratos críticos.

## 19. Persistencia Neon y schema obligatorio

Usa esta topología exacta:

```text
Neon project: ph_torre_delta
├─ main  → PROD
│  └─ database: ph_torre_delta
│     └─ schema: ph_torre_delta
└─ dev   → DEV
   └─ database: ph_torre_delta
      └─ schema: ph_torre_delta
```

Configuración central:

```text
DATABASE_URL=<connection string del branch correspondiente>
DATABASE_SCHEMA=ph_torre_delta
```

Reglas no negociables:

- **todas** las tablas de aplicación, secuencias, índices, constraints y `alembic_version` deben vivir en `ph_torre_delta`;
- `public` no es schema de aplicación;
- `flujos_de_aprobacion` es legacy y nunca es fallback de runtime;
- DEV y PROD se crean desde cero ejecutando Alembic sobre el schema objetivo vacío;
- no muevas, copies, clones ni renombres tablas desde `public`, `flujos_de_aprobacion` u otro schema;
- no migres datos legacy como parte de esta reconstrucción;
- no uses `alembic stamp` para reutilizar el estado de un schema anterior;
- SQLAlchemy debe resolver el schema desde configuración central, no con prefijos dispersos por el código;
- Alembic debe crear/verificar el schema, usarlo como schema efectivo y almacenar allí su tabla de versión;
- DEV y PROD deben tener la misma estructura física; solo cambia `DATABASE_URL`/branch.

Si coexisten `ph_torre_delta`, `public` y `flujos_de_aprobacion`, la aplicación debe operar exclusivamente sobre `ph_torre_delta`.

Feature normativa: `specs/012-neon-schema-isolation/`.

## 20. Alembic

Cadena vigente:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

Puntos clave:

```text
0006 → areas:manage
0007 → config:read
0008 → expense_area / expense_category físicos
```

Contrato de arranque:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Una instalación limpia debe poder ejecutar la cadena completa sobre `ph_torre_delta` vacío y terminar con `ph_torre_delta.alembic_version == head`.

Si PostgreSQL contiene una revisión que la rama no conoce, sincroniza la rama/migración correcta. No uses `stamp` para esconder una incompatibilidad física del esquema.

## 21. Frontend modular y deuda legacy

Componentes relevantes:

```text
frontend/src/expense-form.jsx
frontend/src/home-dashboard.jsx
frontend/src/closure-delegation.jsx
frontend/src/iam-admin.jsx
frontend/src/access-navigation-bridge.js
frontend/src/config-readonly.js
frontend/src/classification-admin.js
```

Pueden permanecer temporalmente `main.jsx`, `domain-normalization.js`, vistas internas `people` / `organization` y bridges Vite, pero no son arquitectura objetivo.

Los bridges deben ser fail-fast y tolerantes a whitespace/LF/CRLF cuando transformen código legacy.

## 22. Definition of Done

Todo cambio funcional/técnico relevante debe sincronizar:

```text
.specify/memory/constitution.md
specs/<feature>/spec.md
specs/<feature>/plan.md
specs/<feature>/checklists/acceptance.md
README.md
PROMPT_RECONSTRUCCION.md
docs/ afectados
docs/HISTORY.md
CHANGELOG.md
```

Gates mínimos:

```text
alembic heads
alembic current
python -m unittest discover -s tests -v
npm run build
```

Para Feature 012 valida además:

```text
main = PROD
dev = DEV
database = ph_torre_delta
schema = ph_torre_delta
ph_torre_delta.alembic_version = head
cero tablas de aplicación nuevas en public
cero dependencia runtime de flujos_de_aprobacion
```

Para Feature 011 valida manualmente:

```text
Accesos → Inicio
Accesos → Solicitudes
Accesos → Facturas
Accesos → Auditoría
Accesos → Configuración → otra pantalla
Accesos → Salir
```
