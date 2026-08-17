# Historial funcional y técnico

## 2026-08-17 — Documentación como parte del Definition of Done

### Decisión

Se establece como regla transversal que ningún cambio funcional o técnico se considera terminado si deja desactualizadas las fuentes documentales afectadas.

Se incorporan como artefactos obligatorios de gobierno:

- `.specify/memory/constitution.md`;
- especificaciones por feature en `specs/`;
- planes técnicos;
- criterios de aceptación;
- `docs/DOCUMENTATION_POLICY.md`.

Cada feature debe revisar además README, prompt maestro, terminología, historial y changelog según corresponda.

### Motivo

El proyecto está evolucionando desde un MVP con términos y estructuras legacy. Sin una regla explícita de sincronización, el código puede avanzar mientras prompts, README o criterios de aceptación continúan reconstruyendo comportamiento obsoleto.

La discrepancia código-documentación pasa a considerarse un defecto de la feature.

---

## 2026-08-17 — Terminología Usuario / Usuarios

### Decisión funcional

El término canónico para el dominio de cuentas es **Usuario / Usuarios**.

La interfaz no debe utilizar **Persona / Personas** como nombre del módulo de administración de cuentas.

El backend ya utiliza `User` y `/api/users`, por lo que esta decisión alinea el lenguaje funcional con el contrato técnico existente.

---

## 2026-08-17 — Clasificación Área + Categoría

### Decisión funcional

Se redefine la clasificación de gastos para separar claramente:

- **Área**: parte de la organización asociada al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.

Ejemplos de Áreas:

- Administración
- Operaciones
- IT
- Mantenimiento
- Marketing

Ejemplos de Categorías:

- Equipos
- Servicios / Consultoría
- Insumos
- Software / Licencias

Se descarta el término **Subárea** para el segundo selector.

### Cambio de arquitectura

Se introduce un catálogo global de categorías y una relación configurable Área-Categoría.

Una misma categoría puede estar disponible para múltiples áreas sin duplicar su identidad lógica.

### Compatibilidad histórica

Las solicitudes existentes conservan los códigos almacenados en:

- `expenses.expense_type` como Área;
- `expenses.expense_subcategory` como Categoría.

Para evitar pérdida de información o una migración destructiva inmediata:

- `expense_categories` sigue funcionando temporalmente como almacenamiento legacy de Áreas;
- `expense_subcategories` permanece como puente de compatibilidad;
- el nuevo catálogo canónico es `expense_category_catalog`;
- las relaciones canónicas son `expense_area_categories`.

### Interfaz

El formulario debe mostrar:

```text
Área
Categoría
```

No debe mostrar:

```text
Categoría / Subcategoría
Área / Subárea
```

### Impacto en reportes

El cambio habilita análisis independientes y cruzados por:

- Área;
- Categoría;
- Área × Categoría.

---

## 2026-08-17 — Retiro del dominio inmobiliario

Se inició el retiro del dominio específico de propiedad horizontal del núcleo de la aplicación.

Se retiraron del modelo activo y/o contratos principales conceptos como:

- `Apartment`;
- `UserApartment`;
- `ApartmentChangeEvent`;
- `OwnershipRole`;
- `PersonType`;
- `apartment_number`;
- endpoints específicos de apartamentos.

El objetivo es mantener el producto neutral para PH y empresas, evitando que la autorización o el flujo de aprobación dependan de conceptos inmobiliarios.

La eliminación física de datos legacy se mantiene separada y requiere respaldo previo.
