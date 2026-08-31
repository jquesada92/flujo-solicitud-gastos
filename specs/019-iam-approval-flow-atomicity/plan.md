# Plan — Spec 019

1. Resolver aprobadores exclusivamente desde IAM; aplicar targets de Rol/Grupo
   cuando exista política y `MAJORITY` global cuando no exista.
2. Permitir preparar aprobaciones dentro de la transacción del endpoint y enviar
   notificaciones únicamente después del commit.
3. Hacer atómica la creación `SIMPLE` con URL y compensar la creación pendiente
   cuando el soporte se carga en una segunda llamada.
4. Mostrar por separado el código efectivo y su origen en Accesos.
5. Cubrir permiso propio agrupado, herencia de Grupo, Rol global y ausencia de
   participantes con pruebas locales.
6. Sincronizar Constitución, Prompt, README, contrato, guía, guardrails,
   changelog y prueba documental.

El scope de política agregado el 2026-08-27 se implementa y acepta en la Spec
021; no reintroduce perfiles legacy como autoridad.
