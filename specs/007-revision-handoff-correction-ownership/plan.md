# Plan 007 — Revisión y handoff

1. Mantener `REVISION_REQUESTED` como decisión explícita del aprobador.
2. Validar comentario mínimo.
3. Expirar el resto de la ronda activa.
4. Crear/mostrar `CORRECT_REQUEST` al solicitante.
5. Mantener autoridad de corrección por recurso.
6. Recalcular el dashboard después de la decisión.
7. Cubrir con tests HTTP y contratos de frontend.

Archivos relevantes: `approvals.py`, `revision_actions.py`, `pending_action_service.py`, `home-dashboard.jsx`, `expense-form.jsx`.
