# Spec 001 — Dominio organizacional y clasificación

**Estado:** Implementada  
**Constitución:** 2.11.0

## Objetivo

Mantener un producto reusable entre organizaciones y un contrato único para clasificación de gastos.

## Contrato

Términos de producto:

```text
Usuario
Área
Categoría
```

Clasificación de solicitud:

```text
expense_area
expense_category
```

Área representa contexto organizacional; Categoría representa naturaleza del bien/servicio. Son catálogos independientes y la disponibilidad conjunta se configura con relación N:M.

## Reglas

1. Los nombres organizacionales son datos, no condiciones runtime.
2. El formulario, Pydantic, ORM y persistencia usan `expense_area` y `expense_category` como contrato nuevo.
3. Las APIs de catálogo permiten crear/activar/inactivar Áreas, Categorías y sus relaciones conforme a permisos.
4. `requests:create` gobierna la posibilidad de registrar una solicitud nueva.
5. La documentación visible usa **Usuario** para cuentas.
6. Cualquier alias técnico temporal debe permanecer aislado como compatibilidad y no aparecer como contrato nuevo.

## Persistencia

La baseline actual crea directamente las columnas canónicas en `expenses`. No existe una operación de reconstrucción que dependa de una base anterior.

## UX

El formulario debe seleccionar primero Área y luego una Categoría habilitada para esa Área. Una corrección rehidrata los valores canónicos persistidos.
