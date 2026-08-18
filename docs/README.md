# Documentación del proyecto

## Gobierno y especificaciones

- [Constitución del proyecto](../.specify/memory/constitution.md) — versión vigente 2.5.0.
- [Política de sincronización documental](DOCUMENTATION_POLICY.md) — los cambios funcionales, técnicos y de autorización deben mantener sincronizados los artefactos gobernados.
- [Feature 001 — normalización de dominio](../specs/001-domain-normalization/spec.md)
- [Feature 001 — plan técnico](../specs/001-domain-normalization/plan.md)
- [Feature 001 — criterios](../specs/001-domain-normalization/checklists/acceptance.md)
- [Feature 002 — IAM configurable + FastAPI](../specs/002-configurable-iam-fastapi-hardening/spec.md)
- [Feature 002 — plan técnico](../specs/002-configurable-iam-fastapi-hardening/plan.md)
- [Feature 002 — criterios](../specs/002-configurable-iam-fastapi-hardening/checklists/acceptance.md)
- [Feature 003 — correcciones de solicitudes](../specs/003-request-correction-invariants/spec.md)
- [Feature 003 — plan técnico](../specs/003-request-correction-invariants/plan.md)
- [Feature 003 — criterios](../specs/003-request-correction-invariants/checklists/acceptance.md)
- [Feature 004 — correo por ambiente](../specs/004-email-delivery-by-environment/spec.md)
- [Feature 004 — plan técnico](../specs/004-email-delivery-by-environment/plan.md)
- [Feature 004 — criterios](../specs/004-email-delivery-by-environment/checklists/acceptance.md)
- [Feature 005 — dashboard, seguimiento y acciones contextuales](../specs/005-universal-dashboard-tracking/spec.md)
- [Feature 005 — plan técnico](../specs/005-universal-dashboard-tracking/plan.md)
- [Feature 005 — criterios](../specs/005-universal-dashboard-tracking/checklists/acceptance.md)
- [Feature 006 — herencia de permisos por Cargo y Grupo](../specs/006-position-group-role-inheritance/spec.md)
- [Feature 006 — plan técnico](../specs/006-position-group-role-inheritance/plan.md)
- [Feature 006 — criterios](../specs/006-position-group-role-inheritance/checklists/acceptance.md)

## Dominio funcional y seguridad

- [Modelo IAM configurable](IAM_MODEL.md) — baseline `requests:read`, Grupo/Cargo → Rol → Permiso, política `TECHNICAL_ADMIN` y fuentes efectivas.
- [Arquitectura FastAPI](FASTAPI_ARCHITECTURE.md) — rutas canónicas, acciones contextuales, resolución IAM, migraciones y separación de runtime/compatibilidad legacy.
- [Modelo Área + Categoría](CLASSIFICATION_MODEL.md)
- [Correcciones y reenvío](REQUEST_CORRECTIONS.md)
- [Seguimiento universal, acciones pendientes y cancelación](REQUEST_TRACKING.md)
- [Configuración de correo](EMAIL_CONFIGURATION.md)
- [Terminología funcional](TERMINOLOGY.md)
- [Historial funcional y técnico](HISTORY.md)
- [Changelog](../CHANGELOG.md)

## Fuentes operativas

- [README principal](../README.md)
- [Prompt maestro de reconstrucción](../PROMPT_RECONSTRUCCION.md)
- `backend/.env.example` — plantilla local sin secretos reales.
- `render.yaml` — producción declara explícitamente `ENVIRONMENT=production`.

Contrato operativo backend:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Cadena Alembic actual:

```text
0000 → 0001 → 0002 → 0003 → 0004
```

- `0003` repara filas históricas MULTI_QUOTE con `request_type=SIMPLE` incorrecto.
- `0004` agrega `position_roles` e importa una sola vez la configuración legacy de cargos/perfiles hacia relaciones IAM canónicas.
- El modal contextual de acciones pendientes no requiere una migración adicional.

## IAM vigente

```text
Usuario → Grupo ─────────→ Rol → Permiso
       ↘ Cargo/Posición ─→ Rol → Permiso
       ↘ Rol directo ─────────→ Permiso
       ↘ Permiso directo
       ↘ Baseline requests:read
```

Un Cargo puede heredar Roles. El **nombre** del Cargo nunca autoriza directamente. Por ejemplo, `Tesorero` puede recibir `requests:approve` porque existe una relación persistida `Tesorero → Aprobador → requests:approve`, no porque el backend compare la palabra `TESORERO`.

La misma regla aplica a Grupos: los miembros heredan los permisos de los Roles asociados al Grupo.

La consola autoritativa es **Configuración → Accesos**:

- Grupos → miembros + Roles heredados;
- Cargos → Roles heredados;
- Usuarios → Grupos + Cargos + Roles directos + permisos directos;
- Permisos efectivos → muestra también el origen.

Ejemplos de origen:

```text
Cargo Tesorero → Aprobador
Grupo Junta Directiva → Aprobador
Rol directo: Comprador
Asignación directa
```

La pantalla legacy basada en `AccessProfile`, `users.title` y `can_*` es deuda de compatibilidad y no es la fuente autoritativa para nuevos cambios de acceso.

## Política ambiental de la cuenta técnica

```text
ENVIRONMENT=production
→ TECHNICAL_ADMIN permisos IAM: config:manage + requests:read
→ las asignaciones accidentales por Grupo/Cargo/Rol/directa no habilitan permisos financieros
→ no recibe aprobación/votación/cierre como acciones personales
→ puede cancelar solicitudes abiertas como excepción administrativa de ciclo de vida

ENVIRONMENT!=production
→ TECHNICAL_ADMIN: todos los permisos activos para testing E2E
```

`RENDER=true` no sustituye `ENVIRONMENT=production` para esta política funcional.

## Seguimiento universal

Todo usuario activo recibe `requests:read` como baseline y puede abrir Inicio/Dashboard y Solicitudes para dar seguimiento.

La lectura no concede mutaciones. En particular, ver una solicitud ajena no autoriza modificarla ni cancelarla.

### Acciones pendientes

Las acciones de Inicio no son nuevos permisos IAM. Son tareas concretas resueltas por `pending_action_service.py` desde permiso efectivo + asignación + estado:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

En **Inicio → Acciones pendientes**:

```text
clic en una fila
→ GET /api/expenses/{request_id}/my-actions
→ modal contextual con las acciones vigentes del usuario

Ver todas
→ Solicitudes
```

El modal puede permitir:

- Aprobar / Rechazar / Solicitar corrección;
- revisar y votar cotizaciones;
- subir factura y cerrar;
- abrir una solicitud propia para Corregir / reenviar.

Después de cada mutación se recargan el dashboard y `my-actions`, por lo que una acción atendida desde correo, otra pestaña o sesión deja de presentarse como ejecutable.

La aprobación contextual usa `POST /api/expenses/{request_id}/approval-decision` sin exponer tokens bearer de links de correo.

Para cancelación:

```text
can_cancel = solicitud abierta
             AND (solicitante original OR system_accounts)
```

Estados cancelables: `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION`, `APPROVED`.

Estados no cancelables: `CLOSED`, `CANCELLED`, `REJECTED`.

## Participación en aprobación/votación

La población se resuelve por permiso efectivo `requests:approve` mediante `users_with_permission()`.

Fuentes válidas:

```text
Permiso directo
Rol directo
Grupo → Rol → requests:approve
Cargo → Rol → requests:approve
```

El solicitante puede quedar excluido de su propia ronda y la cuenta técnica queda excluida de permisos financieros en producción.

## Invariant de correcciones

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

La pestaña de creación seleccionada previamente no puede influir en el editor de corrección. El backend valida nuevamente el tipo canónico.

## Política de correo por ambiente

```text
Producción
Frontend: Vercel
Backend:  Render
Correo:   Brevo HTTPS API

Local / development
Frontend: localhost
Backend:  FastAPI/Docker local
Correo:   Google SMTP
```

Las credenciales SMTP/Brevo pertenecen exclusivamente al backend.

## Términos canónicos

- Usuario, no Persona como nombre del módulo.
- Grupo: conjunto configurable de usuarios que puede heredar Roles.
- Rol: conjunto reutilizable de permisos.
- Permiso: capacidad atómica.
- Cargo/Posición: estructura organizacional configurable que puede heredar Roles; el nombre no autoriza.
- Cuenta técnica / Administrador del sistema: identidad técnica gobernada por ambiente.
- Área: unidad/contexto organizacional del gasto.
- Categoría: naturaleza del gasto.
- Acción pendiente: tarea contextual que requiere intervención del usuario actual; no es un permiso IAM.
- Corrección / Corregir y reenviar: editar sin cambiar SIMPLE/MULTI_QUOTE.
- Cancelar solicitud: finalizar una solicitud abierta por solicitante original o Administrador del sistema.

## Validación durante límite de GitHub Actions

Mientras la cuenta no tenga cuota de Actions, los gates siguen siendo obligatorios localmente:

```text
python -m unittest discover -s tests -v
npm ci
npm run build
docker compose build --no-cache
docker compose up -d
```

No registrar un run bloqueado por cuota como CI verde.

## Regla de mantenimiento

Todo cambio funcional/técnico debe revisar y actualizar en el mismo PR los documentos afectados. La matriz está definida en `DOCUMENTATION_POLICY.md` y en la Constitución.
