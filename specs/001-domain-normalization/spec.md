# Feature Specification — Normalización de dominio y clasificación

**Feature:** 001-domain-normalization  
**Estado:** Implementada en branch, pendiente de merge  
**Fecha:** 2026-08-17

## Objetivo

Convertir el producto en una aplicación organizacional neutral retirando el dominio inmobiliario activo, normalizando la terminología de cuentas a **Usuario/Usuarios** y estableciendo **Área + Categoría** como modelo canónico de clasificación de gastos.

## Problema

El MVP mezclaba conceptos específicos de propiedad horizontal y una clasificación ambigua basada en Categoría/Subcategoría. Esto limitaba la reutilización en empresas y generaba ambigüedad entre unidad organizacional y naturaleza del gasto.

## Modelo funcional canónico

### Usuario

Cuenta que interactúa con el sistema. La interfaz debe utilizar Usuario/Usuarios, no Persona/Personas como nombre del módulo de cuentas.

### Área

Unidad, departamento o función organizacional asociada al gasto.

Ejemplos: Administración, Operaciones, IT, Mantenimiento, Marketing.

### Categoría

Naturaleza del bien o servicio adquirido.

Ejemplos: Equipos, Servicios / Consultoría, Insumos, Software / Licencias, Mobiliario.

Área y Categoría son catálogos independientes. Una Categoría puede habilitarse para múltiples Áreas.

## Historias de usuario

### US-001 — Clasificar una solicitud

Como usuario que crea una solicitud, quiero seleccionar un Área y una Categoría válida para esa Área, para que el gasto pueda analizarse tanto por responsable organizacional como por naturaleza del gasto.

### US-002 — Reutilizar categorías

Como usuario con permiso de configuración, quiero reutilizar una misma Categoría en varias Áreas, para evitar duplicados lógicos como `Equipos IT`, `Equipos Administración` y `Equipos Operaciones`.

### US-003 — Administrar usuarios

Como administrador autorizado, quiero que el módulo se denomine Usuarios y no Personas, para que el lenguaje funcional coincida con el modelo de cuentas y sea neutral respecto al dominio.

### US-004 — Preservar historia

Como auditor, quiero que solicitudes históricas conserven su clasificación original aunque cambien catálogos o relaciones, para poder reconstruir correctamente el expediente.

### US-005 — Producto neutral

Como organización usuaria, quiero que el núcleo del producto no dependa de apartamentos, propietarios, copropietarios, residentes o arrendatarios, para poder utilizar el sistema en distintos tipos de organización.

## Requisitos funcionales

### FR-001
La UI debe mostrar los campos `Área` y `Categoría` en el formulario de solicitudes.

### FR-002
La UI no debe mostrar `Subárea` para el segundo selector.

### FR-003
La UI no debe utilizar `Persona/Personas` como nombre del módulo de cuentas; debe utilizar `Usuario/Usuarios`.

### FR-004
Área y Categoría deben ser catálogos independientes.

### FR-005
Debe existir una relación configurable N:M entre Área y Categoría.

### FR-006
Una misma Categoría puede estar vinculada a múltiples Áreas sin duplicar su identidad lógica.

### FR-007
Al seleccionar un Área, el formulario debe ofrecer únicamente las Categorías habilitadas para esa Área.

### FR-008
Desactivar o desvincular una Categoría no debe modificar solicitudes históricas.

### FR-009
Los conceptos `Apartment`, `UserApartment`, `ApartmentChangeEvent`, `OwnershipRole`, `PersonType`, `apartment_number` y endpoints de apartamentos no deben formar parte del dominio activo.

### FR-010
La eliminación física de estructuras legacy inmobiliarias debe permanecer separada de la inicialización normal de la aplicación y requerir respaldo previo.

### FR-011
El backend sigue siendo autoridad de autorización; los cambios de terminología del frontend no pueden alterar permisos.

### FR-012
Los documentos de proyecto deben actualizarse conjuntamente con los cambios de dominio conforme a la constitución.

## Compatibilidad histórica

Durante la transición se permite mantener nombres físicos legacy si eliminarlos inmediatamente aumenta el riesgo de pérdida de datos:

- `expenses.expense_type` representa Área;
- `expenses.expense_subcategory` representa Categoría;
- `expense_categories` funciona como almacenamiento legacy de Áreas;
- `expense_subcategories` funciona temporalmente como puente Área-Categoría.

Los contratos nuevos deben expresar Área + Categoría aunque internamente exista compatibilidad temporal.

## Fuera de alcance de esta feature

- tercer nivel de Subcategoría;
- rediseño completo de autorización dinámica;
- reglas finales de quórum para votación de cotizaciones;
- migración completa de todos los nombres físicos legacy;
- eliminación automática de datos de producción sin backup.

## Criterios de aceptación resumidos

La feature se acepta cuando:

1. el formulario muestra Área + Categoría;
2. una Categoría puede relacionarse con varias Áreas;
3. la UI usa Usuario/Usuarios;
4. el backend no depende activamente del dominio inmobiliario retirado;
5. los datos históricos conservan sus códigos;
6. existe procedimiento separado de limpieza destructiva;
7. backend regression tests pasan;
8. frontend build pasa;
9. imágenes Docker construyen;
10. constitución, especificación, plan, README, prompt maestro, historia, changelog y terminología están sincronizados.
