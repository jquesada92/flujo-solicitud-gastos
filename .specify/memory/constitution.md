# Constitución del proyecto

**Proyecto:** Flujo de Control de Gastos  
**Versión:** 2.9.0  
**Vigente desde:** 2026-08-19

## 1. Evolucionar el producto existente

El producto debe evolucionar sobre el repositorio actual. Se reutiliza código correcto y se migra o reemplaza únicamente lo que contradiga esta Constitución, las especificaciones vigentes o los criterios de aceptación.

La documentación es parte del entregable. Un cambio funcional, técnico o de seguridad no está completo si deja Constitución, Spec-Kit, README, prompt maestro, documentación funcional, HISTORY o CHANGELOG desalineados.

## 2. Producto neutral respecto al tipo de organización

El sistema debe servir para empresas, PH y otras organizaciones sin introducir en el núcleo conceptos exclusivos de un dominio particular.

No forman parte del modelo canónico:

- apartamentos;
- propietarios/copropietarios;
- residentes/arrendatarios;
- `PersonType`;
- `OwnershipRole`;
- relaciones usuario-apartamento.

Nombres como Junta Directiva, Administración, Presidente, Tesorero, Finanzas, IT, Procurement o CFO son **datos configurables**. Nunca son condiciones de autorización en runtime.

## 3. Terminología canónica

- **Usuario**: cuenta que interactúa con el sistema.
- **Grupo**: conjunto configurable de usuarios que puede heredar Roles.
- **Rol**: conjunto reutilizable de Permisos.
- **Permiso**: capacidad IAM atómica implementada por el producto.
- **Cargo / Posición**: elemento configurable de estructura organizacional que puede heredar Roles; su nombre no autoriza.
- **Área**: unidad, departamento o función organizacional asociada al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.
- **Accesos**: consola única para Usuarios, Grupos, Roles, Permisos, Cargos/Posiciones y permisos efectivos.
- **Enviar a revisión**: decisión del aprobador que interrumpe la ronda y devuelve la solicitud al solicitante con comentario.
- **Corregir / reenviar**: edición por el solicitante original o el Administrador del sistema cuando el estado lo permita.
- **Delegación de cierre/factura**: responsabilidad por solicitud que el solicitante concede de forma explícita y revocable a otro usuario activo.

No usar **Persona/Personas** como módulo de cuentas. No usar **Subárea/Subcategoría** como equivalente de Categoría.

## 4. Clasificación canónica: Área + Categoría

Área y Categoría son dimensiones independientes con relación configurable N:M.

El contrato canónico de solicitud, API, ORM y base de datos es:

```text
expense_area
expense_category
```

`expense_type` y `expense_subcategory` son nombres legacy de compatibilidad y no deben reintroducirse como contrato nuevo.

Alembic `20260819_0008_expense_area_category_columns.py` renombra físicamente las columnas de `expenses` a `expense_area` y `expense_category`, preservando los datos existentes.

La cadena vigente debe contener una revisión disponible para la versión almacenada por PostgreSQL. No se debe hacer `stamp` para ocultar una discrepancia de esquema.

## 5. IAM configurable: permisos sobre nombres

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
config:manage   # system-only
```

`requests:close` puede permanecer físicamente como registro legacy inactivo, pero no autoriza cierre, factura ni delegación.

Para un usuario activo ordinario:

```text
effective_permissions =
    {requests:read}
  ∪ direct permissions
  ∪ direct-role permissions
  ∪ group-role permissions
  ∪ position-role permissions
  - {config:manage}
```

`requests:read` es baseline no revocable. `config:manage` nunca se vuelve efectivo para un usuario ordinario aunque exista una asignación legacy/directa/heredada.

### 5.1 `config:read`

`config:read` permite **consultar** configuración sin mutarla. Puede heredarse por Usuario, Rol, Grupo o Cargo.

Un actor con `config:read` puede inspeccionar Accesos, Áreas, Reglas y Auditoría en modo solo lectura, pero cualquier mutación sigue requiriendo el permiso de escritura correspondiente.

### 5.2 `config:manage`

`config:manage` es **system-only** y se valida junto con identidad persistida en `system_accounts`. No es un permiso empresarial general.

### 5.3 `areas:manage`

`areas:manage` sí es configurable por Rol/Grupo/Cargo/usuario y gobierna mutaciones del catálogo Área + Categoría.

Alembic `0006` crea el Rol neutral `Gestor de áreas`; no debe asignarse automáticamente por nombre de Grupo/Cargo.

### 5.4 Prohibiciones

No autorizar por:

- `UserRole`;
- `can_*` legacy;
- `BOARD_CODES`;
- email fijo;
- ID mágico;
- comparación del nombre/código de Cargo, Grupo o Rol;
- conceptos inmobiliarios.

## 6. Accesos es la única superficie administrativa de identidades

**Usuarios/Personas y Organigrama dejan de ser pantallas independientes de Configuración.**

La navegación objetivo del Administrador del sistema es:

```text
Configuración
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría / demás configuración técnica
```

`Configuración → Accesos` administra:

- crear, activar e inactivar Usuarios;
- datos básicos necesarios para acceso;
- Grupos y membresías;
- Roles y Permisos;
- Cargos/Posiciones;
- asignación de Cargos a Usuarios;
- Roles directos;
- Permisos directos;
- Roles heredados por Grupo/Cargo;
- permisos efectivos y sus fuentes.

No se debe exigir una pantalla separada de Usuarios u Organigrama para completar ninguna de esas operaciones.

Código legacy de `people` / `organization` puede permanecer temporalmente como deuda de migración, pero no aparece en navegación normal ni vuelve a ser fuente de verdad.

## 7. Fronteras de Configuración

### Administrador del sistema

Identificado por `system_accounts`:

```text
Accesos        → lectura + escritura
Áreas          → lectura + escritura
Reglas         → lectura + escritura
Auditoría      → lectura técnica
```

### Usuario con `config:read`

```text
Accesos        → solo lectura
Áreas          → solo lectura, salvo que además tenga areas:manage
Reglas         → solo lectura
Auditoría      → solo lectura
```

No aparecen Usuarios/Personas ni Organigrama como pantallas independientes.

### Usuario con `areas:manage` sin `config:read`

```text
Configuración
└─ Áreas → lectura + escritura
```

`areas:manage` no concede administración IAM.

## 8. Navegación global desde Accesos

Accesos se monta actualmente mediante `#access-management`, pero no puede secuestrar la navegación global.

Mientras Accesos esté abierto deben responder normalmente:

```text
Inicio
Solicitudes
Facturas
Auditoría
Configuración
Salir
```

Al seleccionar una pantalla distinta de Accesos, el hash `#access-management` debe retirarse y la navegación continuar **en el mismo clic**.

La regla también aplica si el destino ya era la pestaña React subyacente. Ejemplo: Accesos se abrió desde Inicio y el usuario vuelve a pulsar Inicio.

Abrir/cerrar solo el dropdown **Configuración** no abandona Accesos; seleccionar una opción navegable dentro del dropdown sí.

Mientras exista la integración legacy, `frontend/src/access-navigation-bridge.js` es el bridge dedicado y se carga antes de `main.jsx`.

## 9. Backend como autoridad

El frontend puede mostrar u ocultar acciones por UX, pero FastAPI es la autoridad final para:

- autorización;
- permisos efectivos;
- `config:read` vs permisos de escritura;
- identidad `system_accounts`;
- herencia Grupo → Rol → Permiso;
- herencia Cargo → Rol → Permiso;
- transiciones de workflow;
- población de participantes;
- acceso a documentos;
- cancelación/corrección/cierre por recurso;
- delegación y revocación;
- invariants SIMPLE/MULTI_QUOTE;
- Área + Categoría;
- auditoría.

## 10. Capacidades por recurso

No toda acción mutable es un permiso global. `GET /api/expenses` expone capacidades calculadas por solicitud y usuario:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

### Cancelar

```text
estado cancelable
AND (solicitante original OR system_accounts)
```

### Corregir

```text
estado corregible
AND (solicitante original OR system_accounts)
```

### Cerrar / factura

```text
status ∈ {APPROVED, CLOSED}
AND (
  solicitante original
  OR system_accounts
  OR delegación activa de esa solicitud
)
```

### Delegar cierre/factura

Solo el solicitante original crea, cambia o revoca la delegación ordinaria.

El backend revalida siempre la mutación aunque el frontend muestre un botón.

## 11. Cuenta técnica / Administrador del sistema

La cuenta creada con `ADMIN_*` queda persistida como `TECHNICAL_ADMIN` en `system_accounts`.

`/api/auth/login` y `/api/auth/me` exponen `is_system_account` para UX. Nunca derivar esta identidad de `UserRole.ADMIN`, Cargo, email o nombre.

### Producción

Solo `ENVIRONMENT=production` activa segregación funcional. IAM máximo:

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

`ENVIRONMENT != production` puede conceder todos los permisos IAM activos a la cuenta técnica para testing E2E, además de las capacidades administrativas por recurso.

`RENDER=true` no sustituye `ENVIRONMENT=production`.

## 12. Dashboard y seguimiento universal

Todo usuario activo recibe `requests:read` y puede abrir Inicio/Dashboard y Solicitudes para seguimiento compartido.

Los KPIs superiores son informativos. Las tareas contextuales actuales son:

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
= solicitud APPROVED + (solicitante original OR delegado activo)
```

El Administrador del sistema conserva capacidades administrativas desde Solicitudes, pero no recibe todas las solicitudes como tareas personales.

## 13. Aprobación y Enviar a revisión

Una aprobación contextual ofrece:

```text
Aprobar
Rechazar
Enviar a revisión
```

`REVISION_REQUESTED` es una interrupción inmediata y requiere comentario útil de al menos 3 caracteres.

Una revisión válida:

```text
approval actual       → REVISION_REQUESTED
request                → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester              → CORRECT_REQUEST
```

Persiste actor, timestamp y comentario; notifica al solicitante y no concede edición al aprobador.

## 14. Corrección y reenvío

Solo:

```text
solicitante original
OR
Administrador del sistema en system_accounts
```

Un tercero con `requests:create`, `requests:approve`, `config:read` o `config:manage` no adquiere propiedad de una solicitud ajena.

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

## 15. Votación MULTI_QUOTE

La población se obtiene mediante `users_with_permission('requests:approve')`, incluyendo permiso directo, Rol directo, Grupo→Rol y Cargo→Rol. Se excluye el solicitante y se aplica la política de cuenta técnica.

Las invitaciones persistidas representan el snapshot vigente.

## 16. Cancelación

Solo solicitante original o `system_accounts`. Estados cancelables: `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION`, `APPROVED`. No cancelables: `CLOSED`, `CANCELLED`, `REJECTED`. Exige motivo y auditoría.

## 17. Cierre, factura y delegación

`APPROVED` no equivale a `CLOSED`.

Cerrar, adjuntar factura o reemplazar/corregir factura es una capacidad por recurso:

```text
solicitante original
OR
Administrador del sistema
OR
delegado activo creado por el solicitante para ESA solicitud
```

`requests:close` no participa en esta autorización.

Persistencia de delegación:

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

## 18. Documentos

PDF/JPEG/PNG/WEBP, validación MIME+firma+tamaño+cuota, almacenamiento privado y descarga backend autorizada.

Reemplazar factura conserva la anterior (`INVOICE_REPLACED`) y registra evento de cambio con actor y motivo.

## 19. Correo por ambiente y notificaciones IAM

Producción: Vercel + Render + Brevo (`EMAIL_MODE=brevo`).  
Local: Docker/FastAPI + Gmail/Workspace SMTP (`EMAIL_MODE=smtp`).

Nunca exponer secretos en frontend, Vercel, repositorio o logs.

Al crear un usuario activo, la invitación con contraseña temporal incluye:

```text
Cargo(s) activos
Permisos efectivos actuales
```

Cuando cambia realmente `position_ids`, se recalculan permisos efectivos y se envía **Actualización de cargo y permisos**. Guardar el mismo Cargo no duplica correo.

Las fuentes de verdad son `UserPosition → Position` y `effective_permission_codes()`.

## 20. Arquitectura FastAPI y migraciones

- `APIRouter` por dominio/capacidad;
- modelos SQLAlchemy fuera de routers;
- esquemas Pydantic para contratos reutilizables;
- servicios para lógica de negocio;
- `get_db()` por request;
- Settings centralizados;
- `lifespan` sin migraciones de esquema;
- Alembic antes de levantar ASGI;
- response models explícitos;
- pruebas HTTP para autorización y contratos críticos.

Cadena vigente:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

`0007` incorpora `config:read`.  
`0008` alinea columnas físicas de solicitudes a `expense_area` / `expense_category`.

Contrato de arranque:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

## 21. Compatibilidad y deuda explícita

Pueden permanecer temporalmente:

- `UserRole`;
- flags `can_*` legacy;
- `AccessProfile`;
- `BOARD_CODES`;
- `/api/users` legacy;
- vistas internas `people` / `organization` no navegables;
- `main.jsx`, `domain-normalization.js` y bridges Vite.

Esa compatibilidad no es autoridad runtime ni arquitectura objetivo.

## 22. Definition of Done

Antes de considerar terminado un cambio relevante:

1. actualizar Constitución si cambia una regla transversal;
2. actualizar `spec.md`, `plan.md` y checklist de la feature;
3. actualizar `README.md`;
4. actualizar `PROMPT_RECONSTRUCCION.md`;
5. actualizar documentación afectada en `docs/`;
6. actualizar `docs/HISTORY.md` y `CHANGELOG.md`;
7. verificar migraciones (`alembic heads`, `alembic current`, `alembic upgrade head` cuando aplique);
8. ejecutar tests backend relevantes;
9. ejecutar `npm run build`;
10. validar manualmente UX crítica cuando exista un bridge o integración legacy.

Para Feature 011, la validación manual debe incluir navegación desde Accesos hacia Inicio, Solicitudes, Facturas, Auditoría, otra opción de Configuración y Salir.
