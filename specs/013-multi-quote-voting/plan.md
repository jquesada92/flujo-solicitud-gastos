# Plan 013 — Votación de cotizaciones

1. Validar contrato MULTI_QUOTE en Pydantic y backend.
2. Persistir opciones antes de congelar participantes.
3. Resolver participantes desde IAM efectivo, los targets de la regla o su
   fallback, y excluir al solicitante conforme a la Spec 021.
4. Crear una invitación por participante/ronda.
5. Autorizar voto por permiso e invitación.
6. Registrar creación o cambio de voto como evento.
7. Aplicar quórum y líder único con regla, o población completa y líder único
   en el fallback, conforme a la Spec 021.
8. Recalcular tras cada voto y conservar solo un ganador provisional cuando sea
   único, sin cambiar automáticamente a `APPROVED`.
9. Mantener la ronda y la acción personal abiertas para que cada invitado pueda
   votar o cambiar su voto hasta factura y `CLOSED`.
10. Bloquear factura ante quórum/población insuficiente o empate y cerrar bajo
    bloqueo transaccional solo con ganador único: cierre anticipado exclusivo
    del Solicitante con regla y autoridad ordinaria en el fallback completo.
11. Migrar hacia `QUOTATION_VOTING` rondas antiguas `APPROVED` sin factura.
12. Reiniciar política, quórum, población, votos y `flow_id` durante corrección.
13. Exponer un monto operativo máximo/líder/máximo para Seguimiento sin mutar
    `Expense.amount`.
14. Mantener escenarios persistentes Docker, pruebas backend, build frontend y
    validación PostgreSQL local.

Los pasos 3, 7 y 10 se interpretan junto con la Spec 021: esa Spec sustituye la
población y el umbral, pero no la garantía de mantener la votación abierta hasta
factura y `CLOSED`.
