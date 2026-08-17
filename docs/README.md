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

- [Modelo IAM configurable](IAM_MODEL.md)
- [Arquitectura FastAPI](FASTAPI_ARCHITECTURE.md)
- [Modelo Área + Categoría](CLASSIFICATION_MODEL.md)
- [Terminología funcional](TERMINOLOGY.md)
- [Historial funcional y técnico](HISTORY.md)
- [Changelog](../CHANGELOG.md)

## Fuentes operativas

- [README principal](../README.md)
- [Prompt maestro de reconstrucción](../PROMPT_RECONSTRUCCION.md)

El contrato operativo backend vigente es:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

El bootstrap debe ejecutarse como módulo desde la raíz del backend; no se documenta `python scripts/bootstrap_admin.py` como comando canónico.

## Modelo vigente

```text
Usuario → Grupo → Rol → Permiso
       ↘ Rol directo
       ↘ Permiso directo
       ↘ Cargo (descriptivo)
```

Autorización depende de Permisos efectivos. Cargos, grupos y roles no autorizan por su nombre.

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
