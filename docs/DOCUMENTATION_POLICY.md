# Política de sincronización de documentación

## Regla

La documentación es parte del entregable. Un cambio de código no está completo si deja artefactos funcionales o técnicos desactualizados.

La fuente de verdad documental se mantiene en este orden:

1. `.specify/memory/constitution.md`
2. `specs/<feature>/spec.md`
3. `specs/<feature>/checklists/acceptance.md`
4. `specs/<feature>/plan.md`
5. `PROMPT_RECONSTRUCCION.md`
6. `README.md`
7. `docs/`
8. código legacy cuando exista una transición documentada

## Artefactos que deben revisarse

Según el impacto de cada cambio, revisar siempre:

1. `.specify/memory/constitution.md`;
2. `specs/<feature>/spec.md`;
3. `specs/<feature>/plan.md`;
4. `specs/<feature>/checklists/acceptance.md`;
5. `README.md`;
6. `PROMPT_RECONSTRUCCION.md`;
7. documentación funcional/técnica afectada en `docs/`;
8. `docs/TERMINOLOGY.md`;
9. `docs/HISTORY.md`;
10. `CHANGELOG.md`;
11. contratos/API, migraciones y comentarios técnicos afectados;
12. descripción del PR cuando aplique.

## Cuándo actualizar cada artefacto

### Constitución

Actualizar cuando cambie una regla transversal, principio de arquitectura, definición de dominio, seguridad, autorización, navegación canónica, persistencia canónica, migraciones o Definition of Done.

### Especificación funcional

Actualizar cuando cambie qué hace el producto, sus superficies, reglas de negocio, campos, nombres funcionales, permisos, navegación o casos límite.

### Plan técnico

Actualizar cuando cambien modelos, tablas, relaciones, endpoints, migraciones, bridges, compatibilidad, arquitectura, seguridad o estrategia de testing.

### Criterios de aceptación

Actualizar siempre que cambie el comportamiento observable o la forma de verificar una feature. No marcar como completado un gate que no se haya ejecutado realmente.

### README

Mantenerlo como descripción operativa actual del producto. No debe enseñar pantallas, permisos, nombres de campos o migraciones retiradas como si siguieran vigentes.

### Prompt maestro

Debe ser suficiente para reconstruir el comportamiento canónico actual sin reintroducir arquitectura legacy.

### Terminología

Actualizar cuando cambie cualquier nombre visible o técnico canónico. La UI, API nueva y documentación deben seguir este documento.

### HISTORY

Registrar decisiones relevantes y su causa: cambios de dominio, arquitectura, navegación, compatibilidad, migraciones y causas raíz de defectos.

### CHANGELOG

Registrar brevemente el cambio entregable orientado a release.

## Cambios de navegación son funcionales

Eliminar, consolidar o mover una pantalla es un cambio funcional cuando modifica la superficie desde la que el usuario completa una tarea.

Ejemplo vigente:

```text
Antes
Configuración → Usuarios
Configuración → Organigrama
Configuración → Accesos

Ahora
Configuración → Accesos
```

Si Usuarios/Personas y Organigrama se consolidan en Accesos, deben sincronizarse Constitución, Feature 011, README, prompt maestro, documentos de IAM/Configuración, HISTORY y CHANGELOG.

## Bridges y defectos de integración legacy

Mientras existan bridges de Vite/DOM/hash para integrar componentes nuevos con el shell legacy, cualquier cambio debe incluir:

- contrato explícito en spec/plan;
- test de regresión automatizado cuando sea viable;
- fail-fast ante transformaciones ambiguas;
- validación manual de la UX crítica cuando el comportamiento depende del navegador.

Para Accesos, la validación mínima es:

```text
Accesos → Inicio
Accesos → Solicitudes
Accesos → Facturas
Accesos → Auditoría
Accesos → Configuración → otra pantalla
Accesos → Salir
```

Abrir/cerrar únicamente el dropdown Configuración no debe abandonar Accesos.

## Renombres de contrato y persistencia

Un renombre de campo que atraviesa API/ORM/DB no es solo cosmético.

Si se cambia el contrato canónico, por ejemplo:

```text
expense_type        → expense_area
expense_subcategory → expense_category
```

se deben revisar como mínimo:

- Constitución y terminología;
- schemas/API;
- modelos ORM;
- migración Alembic y topología;
- pruebas de contrato/migración;
- README y prompt maestro;
- documentación funcional/técnica;
- HISTORY y CHANGELOG.

No usar aliases legacy como excusa para documentar el nombre retirado como contrato vigente.

## Reparaciones de datos o migraciones legacy

Si una rama o volumen PostgreSQL referencia una revisión Alembic ausente, debe resolverse sincronizando la cadena correcta y validando el esquema físico.

No se considera válido usar `alembic stamp` para ocultar una incompatibilidad entre código y base de datos.

## Revisión antes de merge

Responder explícitamente:

- ¿Cambió comportamiento funcional?
- ¿Cambió navegación o superficie de administración?
- ¿Cambió terminología?
- ¿Cambió modelo de datos/API?
- ¿Cambió seguridad/autorización?
- ¿Cambió migración/compatibilidad?
- ¿Cambió despliegue/configuración?
- ¿Cambió un criterio de aceptación?
- ¿Cambió un bridge legacy o su contrato?

Si la respuesta es sí, los documentos correspondientes deben modificarse en el mismo PR/rama.

## Regla de discrepancia

Si código y documentación discrepan:

- no ocultar la discrepancia;
- corregirla antes del merge; o
- documentarla explícitamente como transición/deuda con alcance y condición de retiro.

No es válido asumir que el código “habla por sí solo”.

## Cierre

No marcar una feature/corrección como terminada hasta que:

- pruebas relevantes pasen;
- migraciones aplicables se validen;
- build frontend pase;
- documentación afectada esté sincronizada;
- la descripción del PR refleje el comportamiento real;
- cualquier verificación manual pendiente esté claramente identificada.
