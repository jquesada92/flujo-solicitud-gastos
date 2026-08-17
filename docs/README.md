# Documentación del proyecto

## Gobierno y especificaciones

- [Constitución del proyecto](../.specify/memory/constitution.md)
- [Política de sincronización documental](DOCUMENTATION_POLICY.md)
- [Feature 001 — especificación funcional](../specs/001-domain-normalization/spec.md)
- [Feature 001 — plan técnico](../specs/001-domain-normalization/plan.md)
- [Feature 001 — criterios de aceptación](../specs/001-domain-normalization/checklists/acceptance.md)

## Dominio funcional

- [Modelo de clasificación: Área y Categoría](CLASSIFICATION_MODEL.md)
- [Terminología funcional](TERMINOLOGY.md)
- [Historial funcional y técnico](HISTORY.md)
- [Changelog del proyecto](../CHANGELOG.md)

## Fuentes operativas

- [README principal](../README.md)
- [Prompt maestro de reconstrucción](../PROMPT_RECONSTRUCCION.md)

## Clasificación vigente

La clasificación funcional de gastos es:

```text
Área + Categoría
```

- **Área** identifica la unidad organizacional asociada al gasto.
- **Categoría** identifica la naturaleza del bien o servicio.

`Subárea` y `Subcategoría` no forman parte del modelo funcional vigente para este nivel.

## Terminología de cuentas

El término canónico es:

```text
Usuario / Usuarios
```

La UI no debe utilizar Persona/Personas como nombre del dominio de administración de cuentas.

## Regla de mantenimiento

Todo cambio funcional o técnico debe evaluar y actualizar en el mismo PR los documentos afectados. La matriz completa está definida en `DOCUMENTATION_POLICY.md` y en la constitución.
