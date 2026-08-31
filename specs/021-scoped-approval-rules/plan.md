# Plan 021 — Reglas de aprobación por Área, audiencia y quórum

1. Agregar una revisión Alembic sobre `20260825_0011` para targets de
   Rol/Grupo y la instantánea de política/quórum por solicitud.
2. Unificar validación y resolución de bandas `(min,max]` sin superposición por
   scope, con precedencia del Área sobre `ALL`.
3. Exponer únicamente targets activos compatibles con `requests:approve` y
   resolver Usuarios por IAM efectivo, expansión de Grupo y deduplicación.
4. Evaluar `SIMPLE` por su monto y `MULTI_QUOTE` por el máximo de sus opciones
   antes de congelar la ronda.
5. Calcular y persistir el umbral `ANY`/`MAJORITY`/`ALL` junto con la política y
   el monto evaluado.
6. Mantener abierta una ronda configurada después del quórum; exponer líder,
   progreso, `can_vote` y cierre anticipado exclusivo del Solicitante.
7. Cerrar con factura de forma atómica, fijar el ganador y rechazar votos
   posteriores.
8. Conservar el fallback sin regla y la atomicidad definida por la Spec 019;
   exigir todos los votos y un líder único, mantener `QUOTATION_VOTING` y cubrir
   por HTTP el cierre ordinario directo a `CLOSED`, además del `409` sin factura
   ni ganador cuando falte un voto o exista empate.
9. Sustituir la UI legacy de perfiles por Roles/Grupos y modalidad, con estados
   de carga/error y comportamiento responsive.
10. Sincronizar fuentes normativas, guías, riesgos, historia y pruebas.

La modalidad `NO_APPROVAL`, sus targets vacíos y el registro independiente sin
`Expense` se implementan y aceptan en la Spec 022.
