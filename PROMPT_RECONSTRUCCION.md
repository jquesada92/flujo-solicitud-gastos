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

`requests:close` existe únicamente como registro legacy **inactivo**; no autoriza cierre/factura ni debe aparecer como capacidad operativa configurable.

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

`requests:read` es baseline no revocable. `config:manage` nunca se vuelve efectivo para usuario ordinario.

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

`Configuración → Accesos` es la única superficie para Usuarios, Grupos, Roles, Permisos, Cargos/Posiciones, asignaciones y permisos efectivos.

`config:read` permite consultar sin mutar. `areas:manage` protege mutaciones de Área + Categoría. `config:manage` es system-only y requiere identidad persistida en `system_accounts`.

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

Al seleccionar una pantalla distinta de Accesos, retira explícitamente `#access-management` y continúa la navegación en el mismo clic. Abrir/cerrar solamente el dropdown Configuración no cierra Accesos.

Mientras exista el shell legacy, carga `frontend/src/access-navigation-bridge.js` antes de `main.jsx`.

## 6. Área + Categoría

Contrato canónico de solicitud, API, ORM y base de datos:

```text
expense_area
expense_category
```

No reconstruyas `expense_type` / `expense_subcategory` como columnas vigentes. Pueden existir únicamente como aliases internos temporales.

Área y Categoría son catálogos independientes con relación configurable N:M.

La baseline vigente **crea directamente**:

```text
expenses.expense_area
expenses.expense_category
```

No renombres columnas antiguas ni preserves filas de una base anterior.

## 7. Capacidades por recurso

`GET /api/expenses` expone:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

```text
can_cancel
= estado cancelable + (solicitante original OR system_accounts)

can_correct
= estado corregible + (solicitante original OR system_accounts)

can_close
= status ∈ {APPROVED, CLOSED}
  + (solicitante original OR system_accounts OR delegación activa)

can_delegate_close
= solicitante original
```

El backend vuelve a validar todas las mutaciones aunque el frontend muestre botones.

## 8. Cuenta técnica / Administrador del sistema

La cuenta creada con `ADMIN_*` queda persistida como `TECHNICAL_ADMIN` en `system_accounts`.

`/api/auth/login` y `/api/auth/me` exponen `is_system_account` para UX. Nunca derives esa identidad de `UserRole.ADMIN`, Cargo, email o nombre.

En producción, el IAM máximo del System Admin es:

```text
config:manage
config:read
areas:manage
requests:read
```

No participa en aprobación/votación ni recibe permisos empresariales financieros.

En no producción puede recibir todos los permisos IAM activos para testing E2E. `RENDER=true` no sustituye `ENVIRONMENT=production`.

## 9. Usuario autenticado

Expón al menos:

```text
permission_codes
is_system_account
```

Aliases UX legacy pueden existir temporalmente, pero no autorizan backend.

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

## 11. Aprobación y Enviar a revisión

Una aprobación contextual ofrece:

```text
Aprobar
Rechazar
Enviar a revisión
```

`REVISION_REQUESTED` interrumpe la ronda y requiere comentario útil de al menos 3 caracteres:

```text
approval actual       → REVISION_REQUESTED
request                → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester              → CORRECT_REQUEST
```

No concede edición al aprobador.

## 12. Corrección y reenvío

Solo:

```text
solicitante original
OR
Administrador del sistema en system_accounts
```

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

Incluye permiso directo, Rol directo, Grupo→Rol y Cargo→Rol. Excluye solicitante y aplica política de cuenta técnica.

## 14. Cancelación

Solo solicitante original o `system_accounts`. Exige motivo y auditoría.

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

Una sola delegación activa por solicitud; cambiar delegado revoca el anterior; historial no se borra.

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

Al crear usuario activo, la invitación con contraseña temporal incluye Cargo(s) y permisos efectivos. Cuando cambia realmente `position_ids`, recalcula `effective_permission_codes()` y envía **Actualización de cargo y permisos**. Guardar el mismo Cargo no duplica correo.

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

## 19. Persistencia: base `ph_torre_delta`, schema `administracion`

Usa este contrato exacto:

```text
DEV
DATABASE_URL=<URL Neon DEV / database ph_torre_delta>
DATABASE_SCHEMA=administracion

PROD / Render
DATABASE_URL=<URL Neon PROD / database ph_torre_delta>
DATABASE_SCHEMA=administracion
```

Estructura objetivo:

```text
ph_torre_delta
└── administracion
    ├── tablas de aplicación
    ├── índices / constraints / secuencias
    ├── ENUMs y funciones/triggers propios
    └── alembic_version
```

Reglas no negociables:

- `public` no es schema de aplicación ni fallback;
- no uses `flujos_de_aprobacion` ni otro schema anterior como fuente de verdad;
- SQLAlchemy debe resolver el schema desde `DATABASE_SCHEMA` centralmente;
- en PostgreSQL, el metadata ORM debe usar el schema configurado y el `search_path` debe quedar restringido a él;
- Alembic debe crear el schema si falta, limitar discovery a ese schema y guardar ahí `alembic_version`;
- SQLite de unit tests permanece sin schema;
- no muevas, copies, clones ni renombres tablas antiguas;
- no migres datos legacy;
- no hagas backfills históricos;
- no uses `alembic stamp` para adoptar otra estructura.

Feature normativa: `specs/012-neon-schema-isolation/`.

## 20. Alembic: baseline nueva

La única raíz vigente es:

```text
backend/alembic/versions/20260820_0001_initial_schema.py
revision = '20260820_0001'
down_revision = None
```

No reconstruyas ni reutilices las revisiones anteriores `0000 → 0008`.

La baseline debe:

1. exigir un schema de aplicación vacío;
2. permitir únicamente `alembic_version` precreada por Alembic;
3. crear directamente el modelo físico actual;
4. crear `expense_area` / `expense_category` con sus nombres vigentes;
5. sembrar permisos activos:
   - `requests:read`
   - `requests:create`
   - `requests:approve`
   - `areas:manage`
   - `config:read`
   - `config:manage`
6. conservar `requests:close` solamente como registro inactivo;
7. sembrar Roles mínimos:
   - `system-administrator`
   - `area-manager`
   - `configuration-viewer`
8. instalar guards append-only para las tablas de auditoría;
9. no importar usuarios, grupos, cargos, roles organizacionales ni datos previos.

Contrato de arranque:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Una vez desplegada `20260820_0001` en un ambiente persistente, queda congelada. Cualquier cambio físico posterior debe ser una nueva revisión Alembic (`0002`, `0003`, etc.).

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

Pueden permanecer temporalmente `main.jsx`, `domain-normalization.js`, vistas internas `people` / `organization`, `UserRole`, `can_*`, `AccessProfile`, `BOARD_CODES` y bridges Vite, pero no son arquitectura objetivo ni justifican conservar una base anterior.

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
cd backend
alembic heads
# esperado para Feature 012: 20260820_0001
python -m unittest discover -s tests -v

cd ../frontend
npm run build
```

En DEV, después de `alembic upgrade head`, valida mediante `information_schema` que todas las tablas de aplicación y `alembic_version` estén bajo `administracion` y que `public` no contenga tablas nuevas de la aplicación.
