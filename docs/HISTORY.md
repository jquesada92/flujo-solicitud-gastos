# Historial funcional y técnico

## 2026-08-18 — Cierre/factura pasa a propiedad por solicitud con delegación

### Problema observado

La interfaz permitía **Registrar factura y cerrar** / **Corregir factura** a partir de una capacidad global `requests:close`/`canClose`, aunque la responsabilidad real del expediente debía pertenecer al solicitante o al Administrador del sistema.

El usuario definió además una nueva necesidad: el solicitante debe poder **delegar explícitamente** esa responsabilidad a otra persona para una solicitud concreta.

### Decisión funcional

El cierre/factura deja de ser una autorización global:

```text
solicitante original
OR Administrador del sistema (system_accounts)
OR delegado activo creado por el solicitante para ESA solicitud
```

`requests:close` deja de ser autoridad runtime. Alembic `0005` lo conserva como registro histórico inactivo para no destruir asignaciones antiguas.

### Delegación

Se crea `expense_closure_delegations` con actor/fecha de creación y revocación. Solo existe una delegación activa por solicitud. Cambiar delegado revoca y hace flush de la anterior antes de insertar la nueva; nunca se borra el historial.

Solo el solicitante puede crear/cambiar/revocar. El delegado debe estar activo, ser distinto del solicitante y no ser una cuenta de sistema. La delegación se muestra únicamente cuando la solicitud está `APPROVED` o `CLOSED`, es decir cuando cierre/factura es realmente accionable.

### Backend

- `closure_service.py` centraliza `can_manage_closure()` y la delegación.
- `closure_delegation.py` expone GET/PUT/DELETE por solicitud.
- `financial_actions.py` deja `require_permission('requests:close')` y usa `current_user + can_manage_closure()`.
- `tracking.py` devuelve `can_close` y `can_delegate_close`.
- `pending_action_service.py` redefine `CLOSE_REQUEST` como `APPROVED + (requester OR active_delegate)`.
- el Administrador del sistema conserva facultad administrativa desde Solicitudes, pero no recibe todos los cierres como tareas personales.

### Frontend

Se agrega `frontend/src/closure-delegation.jsx`. Mientras `ExpenseTable` siga monolítico, Vite consume `x.can_close` y `x.can_delegate_close` para mostrar:

```text
APPROVED + can_close → Registrar factura y cerrar
CLOSED + can_close   → Corregir factura
requester            → Delegar cierre/factura
```

El source legacy todavía contiene `canClose={true}` físicamente; el bridge temporal lo deja sin autoridad en el bundle. Debe retirarse al modularizar `ExpenseTable`.

### Migración

Cadena actual:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005
```

`0005` crea la tabla/índice único parcial y marca `requests:close` inactivo/legacy.

La Constitución evoluciona a **2.7.0**.

---

## 2026-08-18 — Propiedad de corrección y handoff de revisión

La lista compartida podía mostrar **Corregir / reenviar** a usuarios que no eran propietarios. Se separaron dos responsabilidades:

```text
Aprobador detecta problema
→ Enviar a revisión + comentario
→ NEEDS_REVISION inmediato
→ otros PENDING/WAITING EXPIRED
→ solicitante recibe CORRECT_REQUEST

Solicitante original OR Administrador del sistema
→ Corregir / reenviar
```

`ExpenseOut.can_correct` y `revision_actions.can_correct_expense()` hacen cumplir la propiedad en UI/backend. `requests:create`, `requests:approve`, Cargo, Rol o Grupo no conceden edición de una solicitud ajena.

El correo/modal de aprobación usa `REVISION_REQUESTED`; una sola revisión válida interrumpe la ronda y devuelve el trabajo al solicitante. Constitución **2.6.0** / Feature 007.

---

## 2026-08-18 — Cargo y Grupo pasan a fuentes configurables de Roles

Producción mostró Tesorero/Vicepresidente con **Aprobar** en una pantalla legacy mientras el workflow no encontraba `requests:approve` efectivo. La causa fue la convivencia de `AccessProfile.can_approve/users.can_approve` con IAM canónico.

Se evolucionó el modelo:

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
```

El nombre del Cargo nunca autoriza. Migración `0004` crea `position_roles` e importa una sola vez configuración legacy a relaciones IAM. Constitución **2.5.0** / Feature 006.

---

## 2026-08-18 — Dashboard: acciones contextuales y KPIs informativos

Todo usuario activo obtiene baseline `requests:read` para Inicio/Solicitudes y seguimiento compartido. La lectura no concede mutaciones.

Las filas de **Acciones pendientes** abren un modal que revalida `/my-actions`; **Ver todas** navega a Solicitudes. Los KPIs superiores son informativos y no clicables.

Códigos contextuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

La semántica de `CLOSE_REQUEST` fue evolucionada posteriormente por Feature 008 a propiedad/delegación por solicitud.

---

## 2026-08-17 — Seguimiento universal y cancelación por recurso

`requests:read` pasó a baseline no revocable para usuarios activos. `GET /api/expenses` dejó de filtrar por solicitante.

Cancelación quedó reservada a:

```text
solicitante original OR system_accounts
```

con `can_cancel` calculado por backend. Tener permisos mutables no permite cancelar solicitudes ajenas.

---

## 2026-08-17 — Corrección MULTI_QUOTE modular y preservación de tipo

Se corrigió el bug donde una MULTI_QUOTE en corrección podía renderizar el formulario SIMPLE según la pestaña de creación previamente seleccionada.

`frontend/src/expense-form.jsx` usa un tipo efectivo derivado de evidencia persistida:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options >= 2
```

Regla:

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

`revision_actions.py` valida backend, la ronda MULTI_QUOTE recibe nuevo `flow_id`, votos/invitaciones se reinician y evidencia se conserva. Migración `0003` repara filas históricas inconsistentes.

---

## 2026-08-17 — Correo por ambiente

Se formalizó:

```text
Producción → Render + Brevo HTTPS API
Local      → Docker/FastAPI + Gmail/Workspace SMTP
```

`PUBLIC_URL` local bajo Docker se alineó a `http://localhost:3000`; Vite directo usa normalmente `5173`. Se agregó `python -m scripts.test_email` para diagnosticar transporte sin depender del workflow.

---

## 2026-08-17 — FastAPI hardening e IAM configurable

Se incorporaron Pydantic Settings, Argon2 con compatibilidad PBKDF2, application factory, Alembic, baseline `0000`, IAM `0001`, system accounts `0002`, routers/servicios canónicos, TestClient y entrypoint Docker:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

La cuenta técnica se identifica por `system_accounts`; producción se rige por `ENVIRONMENT=production`, no por email/nombre/cargo.

---

## 2026-08-17 — Retiro de dominio inmobiliario y normalización

Se retiraron del núcleo activo conceptos como Apartment/UserApartment/ApartmentChangeEvent/OwnershipRole/PersonType/apartment_number. El producto pasó a terminología neutral y clasificación **Área + Categoría**.

Los nombres organizacionales como Presidente, Tesorero o Junta Directiva son datos configurables, nunca condiciones de autorización runtime.

---

## Deuda explícita vigente

- `UserRole`, `users.title`, `can_*`, `AccessProfile`, `BOARD_CODES`, `/api/users` legacy y `requests:close` inactivo permanecen físicamente como compatibilidad.
- `main.jsx` sigue monolítico en partes; Vite mantiene bridges transitorios hasta modularizar `ExpenseTable`/shell.
- fórmula completa de quorum/mayoría APPROVED/REJECTED y empate MULTI_QUOTE siguen como deuda separada;
- edición estructural de opciones MULTI_QUOTE y outbox/retry persistente de correo siguen pendientes.
- GitHub Actions agotó cuota durante PR #9; mientras tanto los gates deben ejecutarse localmente.
