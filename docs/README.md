# Documentación del proyecto

## Gobierno y especificaciones

- [Constitución del proyecto](../.specify/memory/constitution.md) — versión vigente 2.4.0.
- [Política de sincronización documental](DOCUMENTATION_POLICY.md) — los defectos de estado UI que pueden cambiar semántica de negocio se tratan como cambios funcionales.
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
- [Feature 005 — dashboard y seguimiento universal](../specs/005-universal-dashboard-tracking/spec.md)
- [Feature 005 — plan técnico](../specs/005-universal-dashboard-tracking/plan.md)
- [Feature 005 — criterios](../specs/005-universal-dashboard-tracking/checklists/acceptance.md)

## Dominio funcional y seguridad

- [Modelo IAM configurable](IAM_MODEL.md) — incluye baseline `requests:read`, política `TECHNICAL_ADMIN` por ambiente y cancelación por propiedad/cuenta técnica.
- [Arquitectura FastAPI](FASTAPI_ARCHITECTURE.md) — incluye separación `is_production_environment` / endurecimiento de runtime, rutas canónicas y Alembic `0003`.
- [Modelo Área + Categoría](CLASSIFICATION_MODEL.md)
- [Correcciones y reenvío](REQUEST_CORRECTIONS.md) — invariantes SIMPLE/MULTI_QUOTE, aislamiento del estado de pestañas, compatibilidad legacy y reinicio de rondas.
- [Seguimiento universal y cancelación](REQUEST_TRACKING.md) — lectura compartida, `can_cancel` y regla solicitante/Admin del sistema.
- [Configuración de correo](EMAIL_CONFIGURATION.md) — Google SMTP en local/desarrollo y Brevo en producción.
- [Terminología funcional](TERMINOLOGY.md)
- [Historial funcional y técnico](HISTORY.md)
- [Changelog](../CHANGELOG.md)

## Fuentes operativas

- [README principal](../README.md)
- [Prompt maestro de reconstrucción](../PROMPT_RECONSTRUCCION.md)
- `backend/.env.example` — plantilla de variables local sin secretos reales.
- `render.yaml` — declara explícitamente `ENVIRONMENT=production` para el servicio productivo.

Contrato operativo backend:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Cadena Alembic actual:

```text
0000 → 0001 → 0002 → 0003
```

`0003` repara filas históricas MULTI_QUOTE que conservaron un `request_type=SIMPLE` incorrecto. Feature 005 no agrega migración de esquema.

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

Configuración local recomendada:

```env
EMAIL_MODE=smtp
EMAIL_FROM=<CUENTA_GOOGLE>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=<CUENTA_GOOGLE>
SMTP_PASSWORD=<APP_PASSWORD_GOOGLE>
```

Diagnóstico local sin crear una solicitud:

```bash
docker compose exec backend python -m scripts.test_email --to destino@example.com
```

Las credenciales SMTP/Brevo pertenecen exclusivamente al backend y nunca al frontend/Vercel.

## Política ambiental de la cuenta técnica

```text
ENVIRONMENT=production
→ TECHNICAL_ADMIN permisos IAM: config:manage + requests:read
→ puede cancelar solicitudes abiertas como excepción explícita de ciclo de vida

ENVIRONMENT!=production
→ TECHNICAL_ADMIN: todos los permisos activos para testing
```

En producción la cuenta técnica no crea, aprueba, vota ni cierra. La cancelación administrativa se autoriza por `system_accounts`, no mediante un permiso financiero.

`RENDER=true` no sustituye a `ENVIRONMENT=production` para esta política; solo `ENVIRONMENT` decide la autorización funcional productiva.

## Seguimiento universal

Todo usuario activo recibe `requests:read` como baseline y puede abrir Inicio/Dashboard y Solicitudes para dar seguimiento.

La lectura no concede acciones. En particular, ver una solicitud ajena no autoriza modificarla ni cancelarla.

Para cancelación:

```text
can_cancel = solicitud abierta
             AND (solicitante original OR system_accounts)
```

Estados cancelables: `QUOTATION_VOTING`, `SUBMITTED`, `PENDING_APPROVAL`, `NEEDS_REVISION`, `APPROVED`.

Estados no cancelables: `CLOSED`, `CANCELLED`, `REJECTED`.

## Invariant de correcciones

```text
SIMPLE      → corrección → SIMPLE
MULTI_QUOTE → corrección → MULTI_QUOTE
```

La pestaña SIMPLE/MULTI_QUOTE seleccionada antes del clic no puede influir en la corrección. El editor se remonta/rehidrata desde la solicitud seleccionada y el backend vuelve a validar el tipo canónico.

Una corrección MULTI_QUOTE conserva evidencia y opciones existentes, crea un `flow_id` nuevo y reinicia el estado vigente de votación.

## Modelo vigente

```text
Usuario → Grupo → Rol → Permiso
       ↘ Rol directo
       ↘ Permiso directo
       ↘ Cargo (descriptivo)
       ↘ Baseline requests:read
```

Para usuarios operativos, autorización depende de permisos efectivos y reglas explícitas por recurso. Cargos, grupos y roles no autorizan por su nombre. La cuenta técnica aplica además la política ambiental descrita arriba.

Clasificación de solicitudes:

```text
Área + Categoría
```

## Términos canónicos

- Usuario, no Persona como nombre del módulo.
- Grupo para conjuntos de usuarios.
- Rol para conjuntos de permisos.
- Permiso para capacidades de autorización.
- Cargo/Posición para metadato organizacional.
- Cuenta técnica / Administrador del sistema para la identidad técnica gobernada por ambiente.
- Área para unidad/contexto organizacional del gasto.
- Categoría para naturaleza del gasto.
- Corrección / Corregir y reenviar para editar una solicitud sin cambiar su tipo SIMPLE/MULTI_QUOTE.
- Cancelar solicitud para finalizar una solicitud abierta por el solicitante original o el Administrador del sistema.

## Regla de mantenimiento

Todo cambio funcional/técnico debe revisar y actualizar en el mismo PR los documentos afectados. La matriz está definida en `DOCUMENTATION_POLICY.md` y en la Constitución.
