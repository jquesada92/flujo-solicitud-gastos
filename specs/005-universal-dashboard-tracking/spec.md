# Spec 005 — Inicio personal y Seguimiento de usuarios

**Estado:** Implementada  
**Constitución:** 2.13.0

## Objetivo

Separar la vista personal de trabajo de la vista de carga del equipo.

## Inicio

Responde “¿qué tengo que hacer yo?”. Muestra:

- acciones pendientes asignadas al usuario;
- solicitudes creadas por ese usuario;
- métricas personales;
- modal contextual para ejecutar acciones válidas.

Acciones:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## Seguimiento

Pantalla privada de solo lectura con:

- Grupos activos;
- miembros derivados de Roles agrupados;
- Rol del miembro en cada Grupo;
- cantidad de acciones pendientes por usuario y Grupo;
- KPIs de miembros, usuarios con pendientes y total pendiente;
- búsqueda y filtro “solo con pendientes”.

Los Roles globales no crean membresía de Grupo y por tanto no agregan al Usuario a un Grupo en Seguimiento. Seguimiento no permite editar accesos.

## Refresco

Inicio y Seguimiento cargan por montaje/evento/recarga explícita. No hacen polling continuo.
