# Política de sincronización de documentación

## Regla

La documentación es parte del entregable. Un cambio de código no está completo si deja artefactos funcionales o técnicos desactualizados.

## Qué debe revisarse en cada cambio

Según el impacto de la feature, revisar siempre:

1. `.specify/memory/constitution.md`
2. `specs/<feature>/spec.md`
3. `specs/<feature>/plan.md`
4. criterios/checklist de aceptación
5. `README.md`
6. `PROMPT_RECONSTRUCCION.md` y prompts maestros
7. documentación funcional en `docs/`
8. `docs/TERMINOLOGY.md`
9. `docs/HISTORY.md`
10. `CHANGELOG.md`
11. contratos/API, migraciones y comentarios técnicos afectados
12. descripción del PR

## Cuándo actualizar cada artefacto

### Constitución
Actualizar cuando cambie una regla transversal, principio de arquitectura, definición de dominio, seguridad, trazabilidad, migraciones o Definition of Done.

### Especificación funcional
Actualizar cuando cambie qué hace el producto, sus historias de usuario, requisitos, reglas de negocio, estados, campos, nombres funcionales o casos límite.

### Plan técnico
Actualizar cuando cambien modelos, tablas, relaciones, endpoints, migraciones, compatibilidad, arquitectura, seguridad, rendimiento o estrategia de testing.

### Criterios de aceptación
Actualizar siempre que cambie el comportamiento observable o la forma de verificar una feature.

### README
Mantenerlo como descripción operativa actual del producto, arquitectura, conceptos, desarrollo, despliegue y validación. No debe enseñar comportamiento retirado como si siguiera vigente.

### Prompt maestro
Debe ser suficiente para reconstruir el comportamiento canónico actual. No debe reintroducir términos, entidades o reglas ya retiradas.

### Terminología
Actualizar cuando cambie cualquier nombre visible o concepto canónico. La UI debe seguir este documento.

### History
Registrar decisiones relevantes y su motivo, especialmente cambios de dominio, arquitectura, compatibilidad, migraciones y causas raíz de defectos que afecten reglas de negocio.

### Changelog
Registrar el cambio entregable de forma breve y orientada a release.

## Bugs de UI que cambian semántica

Un defecto visual se considera **cambio funcional** cuando el estado del frontend puede alterar una regla de negocio o el payload persistido.

Ejemplo canónico:

```text
Pestaña SIMPLE activa
→ Corregir una solicitud MULTI_QUOTE
→ editor/payload SIMPLE
```

Ese caso no es solamente una corrección de presentación. Cambia la semántica del flujo y, por tanto, exige revisar especificación, criterios, backend authoritative, tests, historia y documentación técnica.

El estado de controles destinados a crear entidades nuevas no debe convertirse accidentalmente en fuente de verdad al editar entidades existentes.

## Reparaciones de datos legacy

Si un defecto revela datos históricos inconsistentes y se introduce una migración para repararlos, deben sincronizarse como mínimo:

- plan técnico;
- topología y tests de migraciones;
- README/despliegue;
- documentación funcional cuando la inconsistencia afecte comportamiento;
- HISTORY y CHANGELOG;
- recuperación/rollback cuando corresponda.

## Revisión antes de merge

Antes de mergear un PR responder explícitamente:

- ¿Cambió comportamiento funcional?
- ¿Cambió terminología?
- ¿Cambió modelo de datos/API?
- ¿Cambió seguridad/autorización?
- ¿Cambió migración/compatibilidad?
- ¿Cambió despliegue/configuración?
- ¿Cambió un criterio de aceptación?
- ¿Cambió la fuente de verdad de algún estado de UI con impacto de negocio?

Si la respuesta es sí, los documentos correspondientes deben estar modificados en el mismo PR.

## Regla de discrepancia

Si código y documentación discrepan:

- no ocultar la discrepancia;
- corregirla antes del merge, o
- documentarla explícitamente como transición/deuda con alcance y condición de retiro.

No se considera válido asumir que el código 'habla por sí solo'.

## Cierre

No marcar una feature o corrección como terminada hasta que:

- pruebas relevantes pasen;
- CI del head final esté verde;
- documentación afectada esté sincronizada;
- la descripción del PR refleje el comportamiento real;
- cualquier verificación manual pendiente esté claramente identificada.
