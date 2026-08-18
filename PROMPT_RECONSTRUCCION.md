# Prompt maestro de reconstrucción

> Constitución vigente: **2.5.0**.

Reconstruye una aplicación web lista para producción llamada **Flujo de Control de Gastos**, destinada a solicitar, evaluar, aprobar, ejecutar, dar seguimiento, cancelar cuando corresponda y documentar gastos con evidencia verificable.

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

La aplicación debe servir para PH, empresas y otras organizaciones.

No introduzcas como dominio canónico:

- apartamentos;
- propietarios/copropietarios;
- residentes/arrendatarios;
- `Apartment`, `UserApartment`, `ApartmentChangeEvent`;
- `OwnershipRole`, `PersonType`, `apartment_number`;
- endpoints inmobiliarios.

Tampoco hardcodees estructuras organizacionales. Nombres como Junta Directiva, Administradora, Presidente, Vicepresidente, Tesorero, Procurement, Finance, IT, CFO o Gerente son **datos configurables**, nunca condiciones de autorización en runtime.

## 2. Terminología

Usa:

- **Usuario**: cuenta del sistema.
- **Grupo**: conjunto configurable de usuarios que puede heredar Roles.
- **Rol**: conjunto reutilizable de Permisos.
- **Permiso**: capacidad atómica implementada por el producto.
- **Cargo/Posición**: estructura organizacional configurable que puede heredar Roles; su nombre no autoriza directamente.
- **Área**: unidad organizacional asociada al gasto.
- **Categoría**: naturaleza del bien/servicio.

No uses Persona/Personas como nombre del módulo de cuentas. No uses Subárea para representar Categoría.

## 3. IAM configurable

Persistencia canónica:

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
- `position_roles`
- `system_accounts`

Modelo:

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ capacidades base
```

Permisos atómicos iniciales:

- `requests:read`
- `requests:create`
- `requests:approve`
- `requests:close`
- `config:manage`

Para un usuario operativo activo:

```text
effective_permissions =
    baseline del producto
  ∪ permisos directos
  ∪ permisos de roles directos
  ∪ permisos de roles heredados por grupos activos
  ∪ permisos de roles heredados por cargos activos
```

No existe DENY individual en esta versión. Para capacidades mutables, ausencia de ALLOW significa DENY.

### Baseline universal

`requests:read` es una capacidad base no revocable para todo usuario activo y autenticado. Quitarla de un Rol, Grupo, Cargo o permiso directo no debe eliminar el acceso de lectura del usuario activo.

### Herencia por Grupo

Un Grupo puede tener múltiples miembros y múltiples Roles:

```text
Grupo Junta Directiva
  miembros: A, B, C
  rol: Aprobador
       requests:approve
```

Todos los miembros activos heredan los permisos de los Roles activos del Grupo.

### Herencia por Cargo

Un Cargo puede tener múltiples Roles:

```text
Rol Aprobador
  requests:approve

Cargo Presidente      → Aprobador
Cargo Vicepresidente  → Aprobador
Cargo Tesorero        → Aprobador
```

Un mismo Rol puede reutilizarse en múltiples Cargos y Grupos.

**No autorices por el nombre del Cargo.** Esto está prohibido:

```python
if user.title == 'TESORERO':
    allow_approve()
```

Esto sí es correcto:

```text
UserPosition
→ Position(active)
→ PositionRole
→ Role(active)
→ RolePermission
→ Permission(active)
```

### Fuentes visibles

Los permisos efectivos deben poder explicar su origen:

```text
Acceso base del producto para usuarios activos
Asignación directa
Rol directo: Comprador
Grupo Junta Directiva → Aprobador
Cargo Tesorero → Aprobador
```

### Prohibiciones IAM

No autorices por:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure` persistidos;
- nombres/códigos concretos de Grupo, Rol, Cargo o AccessProfile;
- emails fijos;
- IDs mágicos;
- `BOARD_CODES`;
- conceptos inmobiliarios.

Los elementos legacy pueden existir temporalmente para compatibilidad/migración, pero no son autoridad runtime.

## 4. Cuenta técnica y política por ambiente

La cuenta creada con `ADMIN_*` debe quedar identificada como `TECHNICAL_ADMIN` en `system_accounts`.

La política se decide por `SystemAccount + ENVIRONMENT`, nunca por email/nombre/cargo/rol legacy.

### Producción

Solo cuando:

```env
ENVIRONMENT=production
```

los permisos IAM efectivos máximos de la cuenta técnica son:

```text
config:manage
requests:read
```

Debe ser imposible que ejerza en producción:

```text
requests:create
requests:approve
requests:close
```

incluso si recibe accidentalmente esas capacidades por Grupo, Cargo, Rol directo o permiso directo. Tampoco participa en poblaciones financieras de aprobación/votación ni recibe acciones financieras contextuales en su bandeja personal.

Como excepción explícita de administración del ciclo de vida, la cuenta técnica puede cancelar una solicitud abierta. Esta facultad se resuelve mediante `system_accounts`; no equivale a conceder un permiso financiero.

### No producción

Para cualquier `ENVIRONMENT` distinto de `production` —local, development/dev, test, staging, preview— la cuenta técnica recibe todos los permisos atómicos activos para pruebas end-to-end y puede participar en workflows cuando no exista otra exclusión intrínseca.

`RENDER=true` puede activar validaciones fuertes de secretos/CORS, pero no sustituye `ENVIRONMENT=production` para autorización funcional.

## 5. Consola de Accesos

Dentro de **Configuración → Accesos** debe existir administración gráfica de:

- Usuarios;
- Grupos;
- Roles;
- Permisos;
- Cargos/Posiciones;
- miembros de Grupos;
- Roles heredados por Grupo;
- Roles heredados por Cargo;
- Grupos de cada Usuario;
- Cargos de cada Usuario;
- Roles directos;
- permisos directos;
- permisos efectivos y sus fuentes.

La pantalla autoritativa es esta consola IAM.

`AccessProfile`, `users.title`, `can_*` y pantallas legacy no deben volver a ser fuente autoritativa para cambios de acceso.

## 6. Contrato del usuario autenticado

Expón:

```text
permission_codes
```

con los permisos efectivos actuales.

Durante la transición del frontend legacy deriva también:

```text
can_request   <- requests:create
can_approve   <- requests:approve
can_view      <- requests:read
can_configure <- config:manage
can_close     <- requests:close
```

Estos aliases nunca autorizan el backend.

`current_user()` debe recalcular permisos efectivos por request para reflejar cambios IAM sin reiniciar la app.

## 7. Dashboard, seguimiento universal y acciones pendientes

Todo usuario activo y autenticado puede:

- abrir **Inicio / Dashboard**;
- ver métricas generales de solicitudes;
- abrir **Solicitudes**;
- consultar solicitudes creadas por otros usuarios para seguimiento.

La lectura compartida no concede acciones mutables.

`GET /api/expenses` y `GET /api/expenses/dashboard` deben depender de `requests:read`, cuyo resolver incluye el baseline.

No filtres la lista por `UserRole.REQUESTER` ni por `requested_by == current_user.email`.

### Bandeja personal de acciones

`pending_my_action` debe contar **acciones concretas vigentes** que requieren intervención del usuario actual, no simplemente solicitudes abiertas ni permisos abstractos.

Resuelve las acciones con un servicio equivalente a `pending_action_service.py` combinando:

```text
permiso efectivo
+
asignación concreta del workflow
+
estado vigente de la solicitud
```

Códigos actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

No agregues estos códigos al catálogo IAM: **son tareas contextuales, no permisos**.

Reglas:

```text
APPROVAL_DECISION
= requests:approve
+ Approval.PENDING asignado al usuario
+ solicitud PENDING_APPROVAL

QUOTATION_VOTE
= requests:approve
+ QuotationVotingInvitation para el usuario
+ solicitud QUOTATION_VOTING
+ ausencia de voto vigente del usuario

CORRECT_REQUEST
= requests:create
+ solicitud propia NEEDS_REVISION

CLOSE_REQUEST
= requests:close
+ solicitud APPROVED
```

Cada `pending_item` del dashboard debe exponer los códigos concretos correspondientes al usuario actual.

### Interacción desde Inicio

En **Inicio → Acciones pendientes**:

```text
Ver todas
→ navegar a Solicitudes

clic en una fila pendiente
→ abrir ventana/modal contextual
```

No reutilices el handler de **Ver todas** para las filas.

Al abrir una fila, consulta nuevamente al backend:

```text
GET /api/expenses/{request_id}/my-actions
```

El backend debe revalidar permiso + asignación + estado y devolver solo acciones todavía ejecutables por el usuario autenticado.

El modal muestra únicamente los controles requeridos por esas acciones:

```text
APPROVAL_DECISION
→ Aprobar
→ Rechazar
→ Solicitar corrección

QUOTATION_VOTE
→ revisar opciones, URLs y soportes
→ votar una cotización

CLOSE_REQUEST
→ seleccionar factura
→ notas de cierre
→ cerrar

CORRECT_REQUEST
→ abrir la solicitud propia para corregir / reenviar
```

Para aprobación autenticada desde el modal usa una ruta por solicitud —por ejemplo `POST /api/expenses/{request_id}/approval-decision`— que localice la aprobación pendiente asignada al usuario actual. **No expongas al frontend el token bearer usado en los enlaces de correo.**

Votación y cierre pueden reutilizar los endpoints canónicos existentes.

Después de cada mutación refresca tanto el dashboard como `my-actions`. Si otra pestaña, correo o sesión ya procesó la tarea, el modal debe informar que ya no quedan acciones pendientes en vez de ofrecer controles obsoletos.

`frontend/src/home-dashboard.jsx` es la implementación canónica del Dashboard/Modal durante esta transición.

## 8. Cancelación de solicitudes

La cancelación es una capacidad **por recurso**, no un permiso derivado de `requests:create`.

Puede cancelar una solicitud abierta únicamente:

```text
solicitante original
OR
cuenta protegida en system_accounts
```

Estados cancelables:

- `QUOTATION_VOTING`
- `SUBMITTED`
- `PENDING_APPROVAL`
- `NEEDS_REVISION`
- `APPROVED`

No cancelables:

- `CLOSED`
- `CANCELLED`
- `REJECTED`

La cancelación exige motivo y persiste:

- `cancelled_at`
- `cancelled_by`
- `cancellation_reason`

El backend devuelve `can_cancel` por solicitud y vuelve a validar siempre la acción. El frontend no debe reconstruir esta autorización con `can_request`, Cargo o Rol.

## 9. Clasificación Área + Categoría

Área y Categoría son catálogos independientes con relación configurable N:M.

```text
Área: Administración, Operaciones, IT, Marketing
Categoría: Equipos, Servicios/Consultoría, Insumos, Licencias
```

Una Categoría puede habilitarse para múltiples Áreas sin duplicarse.

Compatibilidad histórica de columnas puede mantenerse mientras se migra, pero la terminología funcional debe ser Área + Categoría.

## 10. Solicitudes

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

## 11. SIMPLE y MULTI_QUOTE

### SIMPLE

Exige proveedor, monto y soporte/cotización.

### MULTI_QUOTE

Mantiene varias opciones de cotización y una ronda de selección/votación.

La población canónica se obtiene mediante:

```text
users_with_permission('requests:approve')
```

Este resolver debe incluir:

```text
Permiso directo
Rol directo
Grupo → Rol → requests:approve
Cargo → Rol → requests:approve
```

Excluye al solicitante cuando el flujo así lo exige y aplica política de cuenta técnica por ambiente.

Las invitaciones guardadas representan el snapshot de participantes de esa ronda.

## 12. Correcciones

`Corregir / reenviar` preserva siempre el tipo canónico:

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

La pestaña SIMPLE/MULTI_QUOTE seleccionada para una nueva solicitud no puede decidir el tipo de una corrección.

Mientras exista compatibilidad legacy, considera MULTI_QUOTE si:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options.length >= 2
```

El backend debe rechazar con `409` una conversión real entre tipos durante `resubmit`.

Para una corrección MULTI_QUOTE:

- renderiza **Opciones para votación**;
- muestra el tipo como dato de solo lectura;
- restaura opciones existentes;
- conserva soportes existentes;
- permite editar proveedor/monto/URL/observaciones dentro de cada opción;
- mantiene por ahora la cantidad de opciones;
- genera `flow_id` nuevo;
- invalida/limpia votos e invitaciones activas anteriores;
- conserva historial;
- crea nuevas invitaciones usando el resolver IAM vigente;
- vuelve a `QUOTATION_VOTING`.

`frontend/src/expense-form.jsx` es la implementación canónica del formulario.

## 13. Aprobaciones y decisiones

Los participantes se seleccionan por permisos/políticas persistidas, nunca por Cargo hardcodeado.

La población elegible de una ronda debe congelarse/versionarse.

Objetivo funcional de aprobación:

```text
response_rate = valid_responses / eligible_participants
resolver solo cuando response_rate > 0.50
approval_rate = approvals / valid_decision_responses
rejection_rate = rejections / valid_decision_responses
aprobar si approval_rate > 0.50
rechazar si rejection_rate > 0.50
empate/falta de mayoría permanece pendiente
```

No afirmes que el código legacy cumple esta fórmula si todavía existe deuda conocida.

## 14. Aprobado no significa cerrado

`APPROVED` no equivale a `CLOSED`.

Cerrar o reemplazar factura requiere `requests:close` y evidencia de factura.

Producción: cuenta técnica recibe DENY para cierre.

No producción: cuenta técnica puede cerrar para pruebas E2E.

Conserva versiones anteriores de factura y registra actor/fecha/motivo al sustituir.

## 15. Documentos

Admite PDF/JPEG/PNG/WEBP.

Valida:

- MIME;
- firma real;
- tamaño;
- cuota total;
- nombre interno impredecible.

Los documentos son privados y se sirven mediante backend autorizado.

Una corrección reconoce soportes existentes sin intentar prellenar `input[type=file]`.

## 16. Correo por ambiente

Centraliza en Settings y servicio único de correo.

Producción:

```text
Frontend: Vercel
Backend: Render
Correo: Brevo HTTPS API
EMAIL_MODE=brevo
```

Local/development:

```text
Frontend: localhost
Backend: FastAPI/Docker
Correo: Gmail/Google Workspace SMTP
EMAIL_MODE=smtp
smtp.gmail.com
465 + ssl (recomendado)
587 + starttls (alternativa)
```

Nunca expongas `BREVO_API_KEY` ni `SMTP_PASSWORD` en frontend/Vercel/repositorio/logs.

`EMAIL_MODE=console` es solo simulación sin entrega real.

Mantén:

```bash
python -m scripts.test_email --to destino@example.com
```

para diagnosticar transporte independientemente del workflow.

## 17. Arquitectura FastAPI

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
- `get_db()` entrega/cierra sesión por request.
- modelos SQLAlchemy fuera de routers.
- schemas reutilizables fuera de routers.
- servicios para lógica reutilizable.
- response models explícitos.
- SQLAlchemy/filesystem síncrono en path functions `def` o con offload.
- `lifespan` no ejecuta DDL/backfills/seeds.
- rutas canónicas registradas antes de rutas legacy equivalentes.
- autorización crítica vive también en backend.

Rutas/capacidades canónicas actuales incluyen:

- `request_actions.py`
- `revision_actions.py`
- `cancellation_actions.py`
- `quotation_actions.py`
- `document_actions.py`
- `financial_actions.py`
- `my_actions.py`
- `tracking.py`
- `position_access.py`
- `iam.py`
- `iam_users.py`

Servicios relevantes incluyen:

- `iam_service.py` para permisos efectivos/poblaciones;
- `pending_action_service.py` para tareas concretas del usuario;
- `approval_engine.py` para transiciones de aprobación;
- `quotation_service.py` para votación.

## 18. Passwords y sesiones

- Argon2 mediante `pwdlib.PasswordHash.recommended()` para hashes nuevos.
- Compatibilidad temporal PBKDF2 legacy.
- Login PBKDF2 correcto actualiza a Argon2.
- JWT con expiración absoluta.
- timeout de inactividad.
- revocación mediante `session_version`.
- errores de login no revelan existencia del usuario.

## 19. Alembic, Docker y despliegue

No uses `Base.metadata.create_all()` ni migraciones ad-hoc dentro de FastAPI startup productivo.

Cadena vigente:

```text
20260817_0000 application baseline
→ 20260817_0001 IAM foundation
→ 20260817_0002 system accounts
→ 20260817_0003 MULTI_QUOTE request_type repair
→ 20260818_0004 position role inheritance
```

### 0004

`0004` crea `position_roles` y realiza una importación única de compatibilidad desde:

```text
access_profiles.can_*
users.title
```

hacia:

```text
Position
Role
RolePermission
PositionRole
UserPosition
```

Esta migración preserva la configuración productiva existente. Por ejemplo, un AccessProfile legacy con `can_approve=true` se traduce a un Rol que contiene `requests:approve`, asociado al Cargo canónico correspondiente.

Esto **no** significa que `can_approve` vuelva a ser autoridad: se lee una sola vez como entrada histórica de migración. Runtime usa únicamente IAM canónico.

Excluye `system_accounts` de asignaciones organizacionales migradas.

El modal contextual de acciones pendientes no agrega migración adicional.

Secuencia de arranque:

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

Antes de producción para migraciones de datos: respaldo/snapshot, prueba en PostgreSQL/Neon de preview/copia y plan de recuperación.

## 20. Testing obligatorio

Usa unit tests y `FastAPI TestClient`.

Matriz IAM mínima:

- active user recibe baseline `requests:read`;
- permiso directo funciona;
- Rol directo funciona;
- Grupo → Rol → Permiso funciona;
- Cargo → Rol → Permiso funciona;
- Cargo inactivo deja de conceder permiso;
- `permission_sources()` distingue orígenes;
- `users_with_permission()` reconoce Grupo y Cargo;
- producción filtra permisos financieros de cuenta técnica aunque lleguen por Grupo/Cargo/Rol/directo;
- no producción permite E2E técnico;
- usuario sin `config:manage` obtiene 403 de administración IAM.

Matriz de seguimiento/cancelación:

- usuario de solo lectura ve dashboard/solicitudes ajenas;
- lectura no concede mutaciones;
- solicitante puede cancelar propia solicitud abierta;
- otro usuario no puede cancelarla por tener `requests:create`/approve/config;
- system admin puede cancelar abierta;
- cerrada no puede cancelarse.

Matriz de acciones pendientes:

- Approval.PENDING asignado + `requests:approve` produce `APPROVAL_DECISION`;
- invitación MULTI_QUOTE vigente sin voto produce `QUOTATION_VOTE`;
- solicitud propia NEEDS_REVISION + `requests:create` produce `CORRECT_REQUEST`;
- APPROVED + `requests:close` produce `CLOSE_REQUEST`;
- usuario con permiso pero sin asignación concreta no recibe una acción falsa;
- `GET /my-actions` revalida tareas para el usuario actual;
- aprobación contextual funciona sin exponer token de correo;
- después de responder, una acción obsoleta desaparece;
- frontend: clic de fila abre modal contextual y **Ver todas** conserva navegación a Solicitudes;
- frontend refresca dashboard + detalle después de mutación.

Matriz de correcciones:

- MULTI_QUOTE permanece MULTI_QUOTE;
- pestaña SIMPLE previa no cambia el editor;
- opciones/evidencia se preservan;
- `flow_id` cambia;
- ronda activa se reinicia;
- conversión real devuelve 409;
- migración 0003 repara legacy inconsistente.

Matriz de Feature 006:

- Cargo Tesorero → Rol Aprobador → `requests:approve` produce permiso efectivo;
- fuente visible correcta;
- Grupo y Cargo pueden conceder simultáneamente;
- población `requests:approve` incluye ambos caminos;
- topología Alembic tiene `0004` como único head.

CI normalmente debe ejecutar compilación/tests backend, build frontend y construcción/smoke de imágenes Docker. Si la cuota de GitHub Actions está agotada, los mismos gates son obligatorios localmente antes de merge/deploy:

```text
python -m unittest discover -s tests -v
npm ci && npm run build
docker compose build --no-cache
docker compose up -d
```

No marques CI como verde cuando el run no pudo ejecutarse por cuota.

## 21. Deuda legacy permitida solo si está explícita

Puede permanecer temporalmente:

- `UserRole`;
- `users.title`;
- `can_*`;
- `AccessProfile`;
- `BOARD_CODES`;
- `/api/users` legacy;
- `main.jsx` monolítico;
- `domain-normalization.js`;
- transforms temporales Vite.

Pero ninguno de esos elementos puede ser autoridad de autorización nueva.

La pantalla autoritativa de acceso es **Configuración → Accesos**.

`frontend/vite.config.js` puede eliminar temporalmente las definiciones legacy completas de `ExpenseForm` y `HomeDashboard` para usar los módulos canónicos, pero evita nuevos parches de handlers internos sensibles a whitespace. Retira esos transforms cuando `main.jsx` importe directamente los componentes.

Retira progresivamente:

- comparaciones `user.role === "ADMIN"`;
- `canClose={true}`;
- pantallas legacy que mezclan Cargo y permiso;
- cualquier dependencia runtime en `BOARD_CODES`.

## 22. Documentación obligatoria

Un cambio no está terminado hasta revisar y actualizar cuando aplique:

- Constitución;
- spec;
- plan;
- criterios de aceptación;
- README;
- este prompt;
- docs técnicos/funcionales;
- terminología;
- HISTORY;
- CHANGELOG;
- PR.

No presentes deuda legacy como arquitectura objetivo y no reconstruyas dominio inmobiliario retirado.
