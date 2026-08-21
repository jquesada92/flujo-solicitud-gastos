# Plan 001 — Dominio y clasificación

## Implementación vigente

Backend:

- `app/models/classification.py`: catálogos/relación.
- `app/schemas/area.py`: contratos de configuración.
- `app/schemas/expense.py`: contrato de solicitud.
- `app/api/areas.py`: gestión de catálogos.
- `app/api/expenses.py` y routers canónicos: persistencia/consulta.

Frontend:

- `expense-form.jsx`: usa `expense_area` / `expense_category` directamente.
- `classification-admin.js`: administración de catálogos.

## Pasos de mantenimiento

1. Mantener Área y Categoría independientes.
2. No introducir nombres organizacionales en autorización.
3. Si se elimina un alias de compatibilidad, actualizar tests y documentación en el mismo PR.
4. Mantener `requests:create` alineado entre UI y POST de solicitudes.
5. Probar creación, corrección y filtros con los campos canónicos.
