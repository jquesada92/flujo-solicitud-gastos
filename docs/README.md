# Documentación del proyecto

## Gobierno y especificaciones

- [Constitución del proyecto](../.specify/memory/constitution.md) — versión vigente 2.3.2.
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

## Dominio funcional y seguridad

- [Modelo IAM configurable](IAM_MODEL.md) — incluye política `TECHNICAL_ADMIN` por ambiente.
- [Arquitectura FastAPI](FASTAPI_ARCHITECTURE.md) — incluye separación `is_production_environment` / endurecimiento de runtime, rutas canónicas y Alembic `0003`.
- [Modelo Área + Categoría](CLASSIFICATION_MODEL.md)
- [Correcciones y reenvío](REQUEST_CORRECTIONS.md) — invariantes SIMPLE/MULTI_QUOTE, aislamiento del estado de pestañas, compatibilidad legacy y reinicio de rondas.
- [Terminología funcional](TERMINOLOGY.md)
- [Historial funcional y técnico](HISTORY.md)
- [Changelog](../CHANGELOG.md)

## Fuentes operativas

- [README principal](../README.md)
- [Prompt maestro de reconstrucción](../PROMPT_RECONSTRUCCION.md)
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

`0003` repara filas históricas MULTI_QUOTE que conservaron un `request_type=SIMPLE` incorrecto.

## Política ambiental de la cuenta técnica

```text
ENVIRONMENT=production
→ TECHNICAL_ADMIN: config:manage + requests:read

ENVIRONMENT!=production
→ TECHNICAL_ADMIN: todos los permisos activos para testing
```

Esto permite usar el Administrador del sistema para probar crear/aprobar/votar/cerrar en local/dev/test/staging/preview, manteniendo segregación financiera en producción.

`RENDER=true` no sustituye a `ENVIRONMENT=production` para esta política; solo `ENVIRONMENT` decide la autorización funcional productiva.

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
```

Para usuarios operativos, autorización depende de permisos efectivos. Cargos, grupos y roles no autorizan por su nombre. La cuenta técnica aplica además la política ambiental descrita arriba.

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

## Regla de mantenimiento

Todo cambio funcional/técnico debe revisar y actualizar en el mismo PR los documentos afectados. La matriz está definida en `DOCUMENTATION_POLICY.md` y en la Constitución.
