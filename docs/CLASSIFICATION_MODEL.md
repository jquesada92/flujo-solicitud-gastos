# Modelo funcional de clasificación: Área y Categoría

## Objetivo

La clasificación de una solicitud de gasto se divide en dos dimensiones independientes:

- **Área**: unidad organizacional que origina, utiliza o es responsable del gasto.
- **Categoría**: naturaleza del bien o servicio que se está adquiriendo.

Esta separación permite usar la aplicación tanto en empresas como en PH sin introducir conceptos específicos de un solo dominio.

## Área

Ejemplos:

- Administración
- Operaciones
- IT
- Mantenimiento
- Marketing
- Recursos Humanos

El Área responde principalmente a la pregunta: **¿qué parte de la organización está asociada con este gasto?**

## Categoría

Ejemplos:

- Equipos
- Servicios / Consultoría
- Insumos
- Software / Licencias
- Mobiliario
- Capacitación
- Publicidad

La Categoría responde principalmente a la pregunta: **¿qué clase de bien o servicio se está comprando?**

## Relación Área ↔ Categoría

Área y Categoría son catálogos independientes. Una misma categoría puede utilizarse en múltiples áreas.

Ejemplo:

```text
Administración
 ├─ Equipos
 ├─ Insumos
 └─ Servicios / Consultoría

IT
 ├─ Equipos
 ├─ Software / Licencias
 └─ Servicios / Consultoría

Operaciones
 ├─ Equipos
 ├─ Insumos
 └─ Servicios / Consultoría
```

No deben crearse tres categorías distintas llamadas `Equipos`. Debe existir una sola categoría lógica `Equipos` y relaciones configurables con las áreas en las que está habilitada.

## Comportamiento funcional

Al crear una solicitud:

1. El usuario selecciona un **Área**.
2. El sistema muestra las **Categorías** habilitadas para esa Área.
3. El usuario selecciona una Categoría.
4. La solicitud conserva ambos códigos para análisis histórico.

Si posteriormente se desactiva una relación Área-Categoría, las solicitudes históricas no se modifican.

## Reportes esperados

Este modelo permite analizar:

- gasto por Área;
- gasto por Categoría;
- gasto por Área × Categoría;
- evolución mensual por Área;
- evolución mensual por Categoría;
- proveedores por Área o Categoría;
- solicitudes aprobadas/rechazadas por Área o Categoría.

## Compatibilidad histórica

El MVP original almacenaba estos conceptos con nombres legacy:

```text
expense_type          → Área
expense_subcategory   → Categoría
expense_categories    → almacenamiento histórico de Áreas
expense_subcategories → puente de compatibilidad Área-Categoría
```

Los nombres físicos legacy se mantienen temporalmente para no romper solicitudes existentes ni exigir una migración destructiva inmediata.

El contrato funcional nuevo es siempre **Área + Categoría**.

El catálogo global de categorías utiliza:

```text
expense_category_catalog
```

y las relaciones configurables utilizan:

```text
expense_area_categories
```

La tabla legacy `expense_subcategories` se mantiene temporalmente sincronizada como puente de compatibilidad con validaciones y datos históricos del MVP.

## Regla de diseño

No utilizar `Subárea` ni `Subcategoría` para este nivel de clasificación.

La jerarquía funcional vigente es:

```text
Área + Categoría
```

Una futura Subcategoría solo debe introducirse si existe una necesidad real de tercer nivel, por ejemplo:

```text
Área: IT
Categoría: Equipos
Subcategoría: Laptops
```

Ese tercer nivel no forma parte del alcance actual.
