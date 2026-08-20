# Feature Specification — Normalización de dominio y clasificación

**Feature:** 001-domain-normalization  
**Constitución vigente:** 2.9.0  
**Estado:** Implementada y evolucionada por features posteriores.

## Objetivo

Mantener el producto neutral respecto al tipo de organización, retirar dominio inmobiliario activo y establecer **Área + Categoría** como clasificación canónica.

## Modelo funcional canónico

### Usuario

Cuenta que interactúa con el sistema. Usar Usuario/Usuarios, no Persona/Personas.

La administración vigente de Usuarios no es una pantalla independiente: vive dentro de **Configuración → Accesos** conforme a Feature 011.

### Área

Unidad/departamento/función organizacional asociada al gasto.

Campo canónico:

```text
expense_area
```

### Categoría

Naturaleza del bien o servicio adquirido.

Campo canónico:

```text
expense_category
```

Área y Categoría son catálogos independientes con relación N:M.

## Historias de usuario

### US-001 — Clasificar una solicitud

Como usuario que crea una solicitud, quiero seleccionar un Área y una Categoría válida para esa Área.

### US-002 — Reutilizar categorías

Como gestor autorizado, quiero reutilizar una misma Categoría en varias Áreas sin duplicar su identidad lógica.

### US-003 — Terminología neutral de cuentas

Como administrador autorizado, quiero que el producto use Usuario/Usuarios y administre esas cuentas desde Accesos.

### US-004 — Preservar historia

Como auditor, quiero que solicitudes históricas conserven su clasificación aunque cambien catálogos/relaciones.

### US-005 — Producto neutral

Como organización usuaria, quiero que el núcleo no dependa de apartamentos, propietarios, residentes o arrendatarios.

## Requisitos funcionales

### FR-001

La UI muestra **Área** y **Categoría** en el formulario de solicitudes.

### FR-002

No usa Subárea/Subcategoría para el segundo nivel funcional vigente.

### FR-003

No usa Persona/Personas como módulo de cuentas. La superficie vigente es **Accesos → Usuarios**.

### FR-004

Área y Categoría son catálogos independientes.

### FR-005

Existe relación configurable N:M entre Área y Categoría.

### FR-006

Una Categoría puede estar vinculada a múltiples Áreas sin duplicados lógicos.

### FR-007

Al seleccionar Área, el formulario ofrece únicamente Categorías habilitadas y activas para esa Área.

### FR-008

Desactivar/desvincular una Categoría no modifica solicitudes históricas.

### FR-009

`Apartment`, `UserApartment`, `ApartmentChangeEvent`, `OwnershipRole`, `PersonType`, `apartment_number` y endpoints inmobiliarios no forman parte del dominio activo.

### FR-010

Cualquier limpieza destructiva legacy permanece separada del startup y exige backup/procedimiento explícito.

### FR-011

Backend sigue siendo autoridad de autorización.

### FR-012

Documentación se sincroniza conforme a Constitución y `docs/DOCUMENTATION_POLICY.md`.

## Persistencia canónica actual

Alembic `0008` completó la transición física de los campos de solicitud:

```text
expenses.expense_area
expenses.expense_category
```

Por tanto, la afirmación histórica de que `expenses.expense_type` / `expenses.expense_subcategory` eran los nombres físicos vigentes **ya no aplica**.

Pueden existir aliases/código legacy de compatibilidad, pero nuevo código/API/ORM/documentación usa `expense_area` / `expense_category`.

Catálogos/relaciones:

```text
expense_category_catalog
expense_area_categories
```

Las tablas/rutas legacy que permanezcan son deuda de transición, no dominio canónico.

## Relación con features posteriores

- Feature 002: IAM configurable.
- Feature 006: Cargo/Grupo → Rol → Permiso.
- Feature 009: `areas:manage`, `config:read`, frontera técnica.
- Feature 011: Usuarios/Organigrama se consolidan dentro de Accesos y `expense_area` / `expense_category` quedan reafirmados como contrato actual.

## Fuera de alcance

- tercer nivel de Subcategoría;
- multi-tenancy;
- eliminación automática destructiva sin backup;
- retiro total de todos los bridges legacy dentro de esta feature.

## Criterios resumidos

1. formulario usa Área + Categoría;
2. Categoría puede relacionarse con varias Áreas;
3. lenguaje de cuentas usa Usuario/Usuarios dentro de Accesos;
4. dominio activo no depende de conceptos inmobiliarios;
5. historia se conserva;
6. persistencia/API nuevas usan `expense_area` / `expense_category`;
7. backend/tests/build validan el contrato;
8. documentación permanece sincronizada.
