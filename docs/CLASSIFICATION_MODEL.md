# Modelo de clasificación: Área y Categoría

## Contrato

```text
expense_area
expense_category
```

**Área** identifica el contexto organizacional relacionado con el gasto. **Categoría** identifica la naturaleza del bien o servicio. Son catálogos independientes y se habilitan conjuntamente mediante una relación N:M.

## Flujo de creación

1. el usuario selecciona Área;
2. la aplicación consulta/muestra Categorías activas habilitadas para esa Área;
3. el usuario selecciona Categoría;
4. ambos valores se persisten en la solicitud.

El formulario de solicitud nueva solo está disponible con `requests:create`.

## Gestión

Las mutaciones de Área/Categoría requieren:

```text
areas:manage
```

Para un usuario ordinario, ese permiso puede ser propio de un Rol global activo o provenir de la unión de Permisos propios y heredados de un Rol agrupado activo dentro de un Grupo activo. Un Grupo inactivo suspende ambas contribuciones del Rol agrupado. El Administrador del sistema lo recibe por su política técnica de producción.

`config:read` permite lectura de Configuración donde aplique; no autoriza mutaciones del catálogo.

## Persistencia

```text
expenses.expense_area
expenses.expense_category
expense_category_catalog
expense_area_categories
```

La baseline vigente crea directamente el contrato canónico. Las revisiones posteriores 0002/0003/0004 cambian cardinalidades IAM/organizacionales y no alteran este modelo. `category_counters` conserva su nombre físico de compatibilidad y toda consulta runtime debe referenciarlo con el schema configurado.

## Comportamiento de catálogo

- desactivar una Categoría no modifica solicitudes existentes;
- desactivar una relación no reescribe historia;
- la UI de administración puede stagear relaciones y guardarlas explícitamente;
- una Categoría puede estar habilitada en varias Áreas.

## Reportes esperados

- gasto por Área;
- gasto por Categoría;
- Área × Categoría;
- evolución temporal;
- proveedores y estados por clasificación.

Una tercera dimensión de clasificación solo se agrega si una nueva necesidad funcional la justifica mediante Spec y migración correspondiente.
