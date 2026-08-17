# Documentación del proyecto

## Gobierno y especificaciones

- [Constitución del proyecto](../.specify/memory/constitution.md)
- [Política de sincronización documental](DOCUMENTATION_POLICY.md)
- [Feature 001 — normalización de dominio](../specs/001-domain-normalization/spec.md)
- [Feature 001 — plan técnico](../specs/001-domain-normalization/plan.md)
- [Feature 001 — criterios](../specs/001-domain-normalization/checklists/acceptance.md)
- [Feature 002 — IAM configurable + FastAPI](../specs/002-configurable-iam-fastapi-hardening/spec.md)
- [Feature 002 — plan técnico](../specs/002-configurable-iam-fastapi-hardening/plan.md)
- [Feature 002 — criterios](../specs/002-configurable-iam-fastapi-hardening/checklists/acceptance.md)

## Dominio funcional y seguridad

- [Modelo IAM configurable](IAM_MODEL.md) — incluye política `TECHNICAL_ADMIN` por ambiente.
- [Arquitectura FastAPI](FASTAPI_ARCHITECTURE.md) — incluye separación `is_production_environment` / endurecimiento de runtime.
- [Modelo Área + Categoría](CLASSIFICATION_MODEL.md)
- [Terminología funcional](TERMINOLOGY.md)
- [Historial funcional y técnico](HISTORY.md)
- [Changelog](../CHANGELOG.md)

## Fuentes operativas

- [README principal](../README.md)
- [Prompt maestro de reconstrucción](../PROMPT_RECONSTRUCCION.md)

Contrato operativo backend:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

## Política ambiental de la cuenta técnica

```text
ENVIRONMENT=production
→ TECHNICAL_ADMIN: config:manage + requests:read

ENVIRONMENT!=production
→ TECHNICAL_ADMIN: todos los permisos activos para testing
```

Esto permite usar el Administrador del sistema para probar crear/aprobar/votar/cerrar en local/dev/test/preview, manteniendo segregación financiera en producción.

`RENDER=true` no sustituye a `ENVIRONMENT=production` para esta política; solo `ENVIRONMENT` decide la autorización funcional productiva.

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
- Área para unidad/contexto organizacional del gasto.
- Categoría para naturaleza del gasto.

## Regla de mantenimiento

Todo cambio funcional/técnico debe revisar y actualizar en el mismo PR los documentos afectados. La matriz está definida en `DOCUMENTATION_POLICY.md` y en la Constitución.
