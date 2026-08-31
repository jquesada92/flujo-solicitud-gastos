# Plan 023 — Bloqueo global de guardado y alta segura de Roles

1. Extender `request-governor.js` con detección de mutaciones, contador y
   liberación garantizada mediante `finally`.
2. Crear el overlay accesible en DOM, inertizar los demás hijos de `body`,
   gestionar foco y excluir `/api/auth/activity`.
3. Añadir estilos globales en `action-state.css` con prioridad sobre todos los
   overlays, `safe-area`, reducción de movimiento y soporte desde 320 px.
4. En `RolesPanel`, separar creación de edición/reactivación, bloquear doble
   submit y limpiar formulario/selección únicamente tras un `POST` exitoso.
5. Añadir contratos estáticos y una prueba de navegador con mutación demorada,
   error, concurrencia y dos altas consecutivas de Rol.
6. Sincronizar Constitución, Specs relacionadas, Prompt, README, contrato,
   documentación IAM/runtime, guía, validación, historia y changelog.
7. Ejecutar suite backend, build frontend y navegador a 1180, 1024, 640, 440,
   390 y 320 px.

Los checkboxes se marcan solo después de ejecutar y revisar esas evidencias.
