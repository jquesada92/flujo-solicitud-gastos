# Plan 022 — Registro directo de gastos sin aprobación

1. Extender `ApprovalPolicy.approval_mode` con `NO_APPROVAL`, exigir targets
   vacíos para esa modalidad y conservar targets obligatorios para modalidades
   con ronda.
2. Reutilizar bandas `(min,max]`, ausencia de overlap y precedencia Área sobre
   `ALL` de la Spec 021 para resolver elegibilidad.
3. Agregar `DirectExpense` y una revisión Alembic nueva sobre el head vigente,
   sin reescribir migraciones históricas ni crear relación con `Expense`.
4. Implementar listado de bandas elegibles, creación multipart, listado privado
   y descarga autorizada de factura.
5. Hacer atómicos archivo y fila, incluyendo compensación del archivo ante fallo
   de validación o commit.
6. Incorporar **Registro directo → Gasto sin aprobación** para Usuarios con
   `requests:create`, con validación orientativa y layout sin overflow para
   teléfonos/tabletas, controles táctiles de al menos 44 px y apilado de una
   columna hasta 720 px. Traducir el rechazo `NO_APPROVAL` recibido al intentar
   crear una Solicitud en una guía humana sin rutas internas, conservar el
   borrador y resaltar **Registro directo** sin redirección automática.
7. Verificar que el alta no crea Solicitud, ronda, voto, acción pendiente ni
   notificación de aprobación.
8. Cubrir autorización del autor y `system_accounts`, archivos adversos,
   frontera de bandas y cambios concurrentes de política.
9. Validar el navegador en 320, 360, 390, 412, 440, 600, 640, 768, 820 y
   1024 px, además de build y contratos estáticos.
10. Sincronizar Constitución, reglas, Prompt, README, contrato, arquitectura,
    guía, runbooks, historia, guardrails y prueba documental.

Los checkboxes de aceptación se marcan únicamente después de ejecutar y revisar
la evidencia descrita; crear código o documentación no acredita por sí solo el
resultado.
