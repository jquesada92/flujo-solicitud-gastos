# Modelo funcional de clasificación: Área y Categoría

## Objetivo

La clasificación de una solicitud de gasto se divide en dos dimensiones independientes:

- **Área**: unidad organizacional que origina, utiliza o es responsable del gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.

Esta separación permite usar la aplicación en empresas, PH y otras organizaciones sin introducir conceptos específicos de un solo dominio.

## Contrato canónico

La solicitud usa de extremo a extremo:

```text
expense_area
expense_category
```

Estos son los nombres canónicos de:

- columnas físicas de `expenses`;
- atributos ORM;
- contratos Pydantic;
- respuestas de API;
- nuevo código frontend/backend;
- documentación funcional.

Los nombres:

```text
expense_type
expense_subcategory
```

son **legacy** y solo pueden existir como aliases de compatibilidad transitoria. No deben volver a introducirse como contrato nuevo.

## Migración 0008

Alembic:

```text
20260819_0008_expense_area_category_columns.py
```

renombra en PostgreSQL:

```text
expenses.expense_type        → expenses.expense_area
expenses.expense_subcategory → expenses.expense_category
```

y renombra el índice correspondiente de Área sin perder valores históricos.

El downgrade existe para reversibilidad técnica, pero el estado funcional vigente usa `expense_area` / `expense_category`.

No se debe hacer `alembic stamp` para fingir compatibilidad cuando la base física no coincide con el código activo.

## Área

Ejemplos:

- Administración
- Operaciones
- IT
- Mantenimiento
- Marketing
- Recursos Humanos

Pregunta principal: **¿qué parte de la organización está asociada con este gasto?**

## Categoría

Ejemplos:

- Equipos
- Servicios / Consultoría
- Insumos
- Software / Licencias
- Mobiliario
- Capacitación
- Publicidad

Pregunta principal: **¿qué clase de bien o servicio se está comprando?**

## Relación Área ↔ Categoría

Área y Categoría son catálogos independientes. Una misma Categoría puede utilizarse en múltiples Áreas.

```text
Administración
 ├─ Equipos
 ├─ Insumos
 └─ Servicios / Consultoría

IT
 ├─ Equipos
 ├─ Software / Licencias
 └─ Servicios / Consultoría
```

No se deben duplicar Categorías lógicas por Área. Se configura una relación N:M.

## Comportamiento funcional

Al crear una solicitud:

1. el usuario selecciona un **Área**;
2. el sistema muestra las **Categorías** habilitadas para esa Área;
3. el usuario selecciona una Categoría;
4. la solicitud conserva ambos valores para análisis histórico.

Si posteriormente se desactiva una relación Área-Categoría, las solicitudes históricas no se modifican.

## Administración del catálogo

Permiso de escritura:

```text
areas:manage
```

Puede llegar mediante:

```text
Rol directo
Grupo → Rol
Cargo → Rol
Permiso directo
```

El Administrador del sistema también posee `areas:manage` según la política de `system_accounts`.

`config:manage` no es necesario para administrar este catálogo.

`config:read` permite inspeccionar la configuración sin mutarla.

### Categorías por área

La pantalla separa:

```text
Maestro de Categorías
→ activas + inactivas
→ mantenimiento / reactivación

Categorías por área
→ solo categorías activas
→ asignación operativa
```

Desactivar una Categoría:

- no elimina relaciones `expense_area_categories`;
- no altera solicitudes históricas;
- la retira temporalmente de la tarjeta de asignación;
- permite reactivarla desde el Maestro.

Los cambios de asignación son staged y se persisten únicamente al pulsar **Guardar** por fila.

## API canónica

```text
GET    /api/areas
POST   /api/areas
PATCH  /api/areas/{id}
GET    /api/areas/categories
POST   /api/areas/categories
PATCH  /api/areas/categories/{id}
POST   /api/areas/{id}/categories
POST   /api/areas/{id}/categories/{category_id}
DELETE /api/areas/{id}/categories/{category_id}
```

Las lecturas activas necesarias para clasificar solicitudes permanecen disponibles a usuarios autenticados. Las mutaciones requieren `areas:manage`.

## Persistencia de catálogos

Catálogo global:

```text
expense_category_catalog
```

Relación configurable:

```text
expense_area_categories
```

Pueden existir tablas/routers legacy de clasificación durante la migración del MVP, pero no definen el contrato nuevo.

## Frontend legacy

`domain-normalization.js` y otros bridges pueden traducir temporalmente estructuras legacy hacia el contrato canónico. Esa capa es compatibilidad transitoria y debe retirarse cuando el shell principal esté completamente modularizado.

Nuevo código no debe depender de `expense_type` / `expense_subcategory`.

## Reportes esperados

- gasto por Área;
- gasto por Categoría;
- gasto por Área × Categoría;
- evolución mensual por Área;
- evolución mensual por Categoría;
- proveedores por Área/Categoría;
- solicitudes aprobadas/rechazadas por Área/Categoría.

## Regla de diseño

La jerarquía funcional vigente es:

```text
Área + Categoría
```

No usar Subárea ni Subcategoría para este nivel.

Una futura Subcategoría solo se introduce si existe una necesidad real de tercer nivel y mediante una nueva especificación/migración.
