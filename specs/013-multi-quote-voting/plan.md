# Plan 013 — Votación de cotizaciones

1. Validar contrato MULTI_QUOTE en Pydantic y backend.
2. Persistir opciones antes de congelar participantes.
3. Resolver participantes desde IAM efectivo, los targets de la regla o su
   fallback, y excluir al solicitante conforme a la Spec 021.
4. Crear una invitación por participante/ronda.
5. Autorizar voto por permiso e invitación.
6. Registrar creación o cambio de voto como evento.
7. Aplicar quórum/cierre configurado o espera total del fallback conforme a la
   Spec 021, siempre con líder único.
8. Exponer acción pendiente únicamente mientras falte el voto personal.
9. Reiniciar ronda y `flow_id` durante corrección.
10. Mantener escenarios persistentes Docker y pruebas unitarias de errores.

Los pasos 3 y 7 originales fueron sustituidos el 2026-08-27 por la Spec 021; no
deben interpretarse como una alternativa que espere siempre a toda la población.
