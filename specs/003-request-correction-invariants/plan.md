# Plan 003 — Correcciones

1. Calcular `can_correct` en backend por solicitud.
2. Revalidar autoridad en el endpoint de reenvío.
3. Rehidratar el formulario desde el request seleccionado.
4. Preservar `request_type`.
5. Para MULTI_QUOTE, conservar opciones/soportes editables y reiniciar estado activo de la ronda.
6. Mantener historial/auditoría.
7. Probar actor no propietario, System Admin, SIMPLE y MULTI_QUOTE.

Archivos relevantes: `revision_actions.py`, `request_actions.py`, `expense-form.jsx`, tests de corrección/revisión.
