# Plan 008 — Cierre y delegación

Backend:

- `closure_service.py`: autoridad por recurso.
- `closure_delegation.py`: crear/revocar delegación.
- `financial_actions.py` / `document_actions.py`: factura y cierre.

Frontend:

- `closure-delegation.jsx` reutilizable en Solicitudes e Inicio.
- `home-dashboard.jsx` ofrece delegar dentro de CLOSE_REQUEST cuando `can_delegate_close` es true.

Mantener auditoría append-only y validación de archivo en backend.
