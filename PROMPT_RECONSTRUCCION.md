# Prompt maestro de reconstrucción

> Constitución vigente: **2.8.0**.

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
8. código existente

Si existe discrepancia, prevalece el artefacto de mayor prioridad.

## 1. Producto neutral

Sirve para PH, empresas y otras organizaciones. No reconstruyas como dominio canónico apartamentos, propietarios/copropietarios, residentes/arrendatarios, `Apartment`, `UserApartment`, `ApartmentChangeEvent`, `OwnershipRole`, `PersonType`, `apartment_number` ni endpoints inmobiliarios.

Nombres como Junta Directiva, Administradora, Presidente, Vicepresidente, Tesorero, Procurement, Finance, IT o CFO son **datos configurables**, nunca condiciones runtime.

## 2. Terminología

- **Usuario**: cuenta del sistema.
- **Grupo**: conjunto configurable de usuarios que hereda Roles.
- **Rol**: conjunto reutilizable de Permisos.
- **Permiso**: capacidad IAM atómica.
- **Cargo/Posición**: estructura configurable que puede heredar Roles; su nombre no autoriza.
- **Área**: unidad organizacional asociada al gasto.
- **Categoría**: naturaleza del bien/servicio.
- **Gestión de Áreas**: configuración organizacional bajo `areas:manage`.
- **Administración técnica**: funciones system-only bajo `config:manage` + identidad `system_accounts`.
- **Enviar a revisión**: acción del aprobador que detiene el flujo y devuelve la solicitud con comentario.
- **Corregir / reenviar**: edición por solicitante original o Administrador del sistema.
- **Delegación de cierre/factura**: responsabilidad por solicitud que el solicitante concede a un usuario activo y puede cambiar/revocar.

No uses Persona/Personas como módulo de cuentas ni Subárea como Categoría.

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

Permisos IAM vigentes:

```text
requests:read
requests:create
requests:approve
areas:manage
config:manage  # system-only
```

`requests:close` puede existir físicamente como registro **legacy inactivo**, pero no autoriza cierre/factura ni debe presentarse como permiso operativo configurable.

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

### Grupo y Cargo

Un mismo Rol puede heredarse por ambos:

```text
Rol Aprobador
  requests:approve

Cargo Tesorero        → Aprobador
Cargo Vicepresidente  → Aprobador
Grupo Junta Directiva → Aprobador
```

Nunca autorices con `if user.title == 'TESORERO'` ni por nombres/códigos de Cargo, Grupo o Rol.

### Gestión de Áreas

`areas:manage` sí es configurable por Rol/Grupo/Cargo/usuario.

Alembic `0006` crea:

```text
Rol Gestor de áreas
  areas:manage
```

No lo asignes automáticamente a un Grupo/Cargo llamado Administración, Junta Directiva ni a ningún nombre. El Administrador del sistema hace esas asociaciones desde Accesos como datos del cliente.

### Administración técnica

`config:manage` es system-only y gobierna Usuarios, Organigrama, Accesos/IAM, Reglas y Auditoría técnica.

El resolver IAM debe ignorar `config:manage` para usuarios que no estén persistidos en `system_accounts`.

### Prohibiciones IAM

No autorices por `UserRole`, `can_*` legacy, `BOARD_CODES`, emails fijos, IDs mágicos ni conceptos inmobiliarios. Los elementos legacy pueden permanecer como compatibilidad/migración, no como autoridad runtime.

## 4. Capacidades por recurso

No toda acción mutable es un permiso global. `GET /api/expenses` expone capacidades calculadas por solicitud y usuario:

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

Solo el solicitante original administra la delegación de su solicitud. El Administrador del sistema no necesita delegación y no crea delegaciones ordinarias en nombre del solicitante.

El backend vuelve a validar siempre las mutaciones aunque el frontend muestre un botón.

## 5. Cuenta técnica / Administrador del sistema

La cuenta creada con `ADMIN_*` queda persistida como `TECHNICAL_ADMIN` en `system_accounts`.

`/api/auth/login` y `/api/auth/me` exponen `is_system_account` para UX. Nunca derives esta identidad de `UserRole.ADMIN`, Cargo, email o nombre.

### Producción

Solo `ENVIRONMENT=production` activa segregación funcional. IAM máximo:

```text
config:manage
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

No recibe automáticamente todas las correcciones/cierres como tareas personales del Dashboard.

### No producción

`ENVIRONMENT != production` concede todos los permisos IAM activos para testing E2E además de las capacidades administrativas por recurso.

`RENDER=true` no sustituye `ENVIRONMENT=production`.

## 6. Configuración: frontera técnica vs Áreas

UX objetivo:

```text
System Admin
→ Usuarios
→ Organigrama
→ Accesos
→ Áreas
→ Reglas/Auditoría técnica

Usuario ordinario con areas:manage
→ Áreas solamente

Usuario ordinario sin areas:manage
→ sin Configuración
```

Backend:

- IAM/Usuarios/Reglas/Auditoría permanecen bajo `config:manage` system-only;
- mutaciones de `/api/areas` usan `areas:manage`;
- `include_inactive` de Área/Categoría requiere `areas:manage`.

Frontend:

```text
isSystemAdmin = user.is_system_account === true
canManageAreas = isSystemAdmin OR permission_codes incluye areas:manage
```

`iam-admin.jsx` solo puede inyectar **Accesos** dentro de un menú marcado como System Admin. Ocultar UI nunca sustituye backend.

## 7. Consola de Accesos

**Configuración → Accesos** está reservada al System Admin y administra Usuarios, Grupos, Roles, Permisos, Cargos/Posiciones, miembros, Roles heredados por Grupo/Cargo, Cargos de Usuario, Roles/permisos directos y permisos efectivos/fuentes.

Para dar Gestión de Áreas a colectivos, asocia el Rol **Gestor de áreas** al Grupo/Cargo que la organización decida. Sus nombres son datos, no reglas.

La delegación de cierre/factura **no pertenece al IAM global**; se administra desde la solicitud.

La pantalla `AccessProfile/can_*` es legacy.

## 8. Usuario autenticado

Expón:

```text
permission_codes
is_system_account
```

Los aliases UX legacy (`can_request`, `can_approve`, `can_view`, `can_configure`, `can_close`) pueden existir temporalmente, pero no autorizan backend. `can_close` de sesión no debe confundirse con `ExpenseOut.can_close`, que es por recurso.

`current_user()` recalcula permisos efectivos por request.

## 9. Dashboard y seguimiento universal

Todo usuario activo puede abrir Inicio/Dashboard y Solicitudes y consultar solicitudes ajenas para seguimiento.

KPIs superiores son informativos, sin `onClick`:

```text
Acciones que requieren mi atención
Solicitudes en proceso
Cerradas en 24 horas
```

Interacción:

```text
fila pendiente → modal contextual
Ver todas      → Solicitudes
```

Tareas contextuales actuales:

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

El Administrador del sistema puede cerrar desde Solicitudes como excepción, pero no recibe todas las solicitudes aprobadas en su bandeja personal.

Al abrir una fila consulta `GET /api/expenses/{request_id}/my-actions` y revalida las tareas.

## 10. Aprobación y Enviar a revisión

Una aprobación contextual ofrece:

```text
Aprobar
Rechazar
Enviar a revisión
```

`REVISION_REQUESTED` es una interrupción inmediata, no una respuesta que espere mayoría. Requiere comentario útil de al menos 3 caracteres.

Una revisión válida:

```text
approval actual       → REVISION_REQUESTED
request                → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester              → CORRECT_REQUEST
```

Persiste actor/timestamp/comentario y notifica al solicitante. No concede al aprobador capacidad de edición.

La ruta autenticada del modal usa `POST /api/expenses/{request_id}/approval-decision` sin exponer tokens bearer de correo.

## 11. Corrección y reenvío

Solo:

```text
solicitante original
OR
Administrador del sistema en system_accounts
```

Un tercero con `requests:create`, `requests:approve` o `config:manage` recibe 403.

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

`PUT /api/expenses/{request_id}/resubmit` usa una regla por recurso, no `require_permission('requests:create')`.

Invariant:

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

La pestaña de creación nunca decide el tipo de una corrección. Una MULTI_QUOTE corregida conserva evidencia/opciones, genera `flow_id` nuevo, invalida ronda anterior y excluye siempre al solicitante original de la nueva población.

`frontend/src/expense-form.jsx` es el formulario canónico.

## 12. Votación MULTI_QUOTE

Población: `users_with_permission('requests:approve')`, incluyendo permiso directo, Rol directo, Grupo→Rol y Cargo→Rol. Excluye solicitante y aplica política de cuenta técnica.

Las invitaciones persistidas representan el snapshot vigente.

## 13. Cancelación

Solo solicitante original o `system_accounts`. Estados cancelables: `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION`, `APPROVED`. No cancelables: `CLOSED`, `CANCELLED`, `REJECTED`. Exige motivo y auditoría.

## 14. Cierre, factura y delegación

`APPROVED` no equivale a `CLOSED`.

Cerrar, adjuntar factura o reemplazar/corregir factura es una capacidad por recurso:

```text
solicitante original
OR
Administrador del sistema
OR
delegado activo creado por el solicitante para ESA solicitud
```

`requests:close` **no** participa en esta autorización.

### Delegación

Persistencia:

```text
expense_closure_delegations
- expense_id
- delegate_user_id
- delegated_by_user_id
- delegated_by_email
- created_at
- revoked_at
- revoked_by_user_id
- revoked_by_email
```

Reglas:

- solo el solicitante original crea/cambia/revoca;
- una sola delegación activa por solicitud;
- delegado activo, distinto del solicitante y no `system_accounts`;
- cambiar delegado revoca/flush primero el anterior;
- historial no se borra;
- revocar elimina inmediatamente autoridad futura;
- delegación no se propaga a otras solicitudes.

API:

```text
GET    /api/expenses/{request_id}/closure-delegation
PUT    /api/expenses/{request_id}/closure-delegation
DELETE /api/expenses/{request_id}/closure-delegation
```

Endpoints financieros:

```text
POST /api/expenses/{request_id}/close
PUT  /api/expenses/{request_id}/invoice
```

usan `current_user + can_manage_closure()`, nunca `require_permission('requests:close')`.

Frontend:

```text
frontend/src/closure-delegation.jsx
```

- `APPROVED + x.can_close` → Registrar factura y cerrar.
- `CLOSED + x.can_close + factura` → Corregir factura.
- `x.can_delegate_close` → Delegar cierre/factura.

## 15. Área + Categoría

Catálogos independientes con relación configurable N:M. No reconstruyas Subárea como Categoría.

API canónica de configuración: `/api/areas`. Mutaciones e inactivos requieren `areas:manage`; no uses `config:manage` para esta responsabilidad.

## 16. Documentos

PDF/JPEG/PNG/WEBP, validación MIME+firma+tamaño+cuota, almacenamiento privado y descarga backend autorizada. Reemplazar factura conserva la anterior (`INVOICE_REPLACED`) y registra `InvoiceChangeEvent` con actor/motivo.

## 17. Correo por ambiente

Producción: Vercel + Render + Brevo (`EMAIL_MODE=brevo`). Local: Docker/FastAPI + Gmail/Workspace SMTP (`EMAIL_MODE=smtp`). Nunca expongas secretos en frontend/Vercel/repositorio/logs.

Mantén `python -m scripts.test_email --to destino@example.com` para diagnóstico.

## 18. Arquitectura FastAPI

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

Rutas/servicios canónicos relevantes:

```text
request_actions.py
revision_actions.py
cancellation_actions.py
closure_delegation.py
quotation_actions.py
document_actions.py
financial_actions.py
my_actions.py
tracking.py
areas.py
position_access.py
iam.py
iam_users.py

iam_service.py
closure_service.py
pending_action_service.py
approval_engine.py
quotation_service.py
```

Modelos adicionales:

```text
models/closure.py → ExpenseClosureDelegation
```

Mientras `ExpenseTable`/shell continúe legacy en `main.jsx`, Vite puede mantener bridges mínimos para capacidades por recurso, componentes modulares y separación del menú de configuración. Retíralos al modularizar.

## 19. Passwords y sesiones

Argon2 para hashes nuevos, compatibilidad/upgrade PBKDF2 legacy, JWT con expiración absoluta, timeout de inactividad y `session_version` para revocación.

## 20. Alembic / Docker / despliegue

Cadena vigente:

```text
20260817_0000 application baseline
→ 20260817_0001 IAM foundation
→ 20260817_0002 system accounts
→ 20260817_0003 MULTI_QUOTE request_type repair
→ 20260818_0004 position role inheritance
→ 20260818_0005 closure delegation
→ 20260818_0006 area management permission
```

`0005` crea `expense_closure_delegations`, su índice único parcial y marca `requests:close` inactivo/legacy.

`0006` crea/activa `areas:manage`, crea el Rol neutral `Gestor de áreas` y documenta `config:manage` como administración técnica; no asigna acceso por nombres organizacionales.

Inicio:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Antes de producción: backup/snapshot + smoke PostgreSQL/Neon preview/copia + plan de recuperación.

## 21. Testing obligatorio

Matriz mínima:

- baseline `requests:read`;
- IAM directo/Rol/Grupo/Cargo;
- `areas:manage` efectivo para usuario ordinario;
- usuario `areas:manage` no accede a IAM/Usuarios/Organigrama;
- `config:manage` legacy asignado a usuario ordinario no es efectivo;
- `is_system_account` explícito en login/`/auth/me`;
- política técnica producción/no-producción (`read + areas + config` en producción);
- menú System Admin vs Gestor de áreas vs usuario sin configuración;
- topología Alembic con `0006` único head;
- `can_cancel` solicitante/Admin;
- `can_correct` solicitante/Admin;
- tercero no corrige ajena;
- revisión inmediata + comentario + expiración;
- `CORRECT_REQUEST` solicitante;
- `can_close` solicitante/Admin/delegado;
- tercero con `requests:close` legacy NO cierra solicitud ajena;
- solo solicitante administra delegación;
- delegado recibe `CLOSE_REQUEST`;
- revocación elimina autoridad;
- una sola delegación activa;
- factura reemplazada conserva versión anterior;
- frontend usa capacidades por recurso, no `canClose={true}` como autoridad runtime.

GitHub Actions puede estar bloqueado por cuota; en ese caso suite backend + `npm run build` + Docker build/smoke siguen siendo gates locales obligatorios. No declares CI verde si no se ejecutó.

## 22. Deuda legacy permitida solo explícitamente

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
bridges Vite
requests:close como registro inactivo histórico
```

Ninguno autoriza nueva lógica runtime.

La UI IAM puede todavía mostrar referencias legacy a `config:manage`, pero runtime lo filtra para usuarios no-system hasta retirar esa deuda visual.

Deuda funcional separada: fórmula completa de quorum/mayoría APPROVED/REJECTED, empate MULTI_QUOTE, edición estructural de opciones y outbox/retry persistente.

## 23. Documentación obligatoria

Un cambio no termina hasta revisar/actualizar Constitución, spec, plan, checklist, README, este prompt, docs funcionales/técnicos, terminología, HISTORY, CHANGELOG y PR.
