# Plan 013 — Votación de cotizaciones

1. Validar contrato MULTI_QUOTE en Pydantic y backend.
2. Persistir opciones antes de congelar participantes.
3. Resolver participantes desde IAM efectivo y excluir al solicitante.
4. Crear una invitación por participante/ronda.
5. Autorizar voto por permiso e invitación.
6. Registrar creación o cambio de voto como evento.
7. Recalcular tras cada voto y conservar solo un ganador provisional cuando sea único.
8. Mantener la ronda y la acción personal abiertas para permitir cambiar el voto.
9. Bloquear factura ante votos pendientes o empate y cerrar bajo bloqueo transaccional solo con ganador único.
10. Migrar hacia `QUOTATION_VOTING` rondas antiguas `APPROVED` sin factura.
11. Reiniciar ronda y `flow_id` durante corrección.
12. Exponer un monto operativo máximo/líder/máximo para Seguimiento sin mutar `Expense.amount`.
13. Mantener pruebas unitarias, build frontend y validación PostgreSQL local.
