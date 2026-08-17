# Changelog

## 2026-08-17

### Added
- Catálogo global de Categorías independiente de Áreas.
- Relación configurable Área ↔ Categoría.
- Documentación funcional del modelo de clasificación.
- Terminología canónica **Usuario / Usuarios**.
- Constitución del proyecto en `.specify/memory/constitution.md`.
- Especificación funcional y plan técnico de `001-domain-normalization`.
- Checklist explícito de criterios de aceptación.
- Política de sincronización de documentación.
- Historial técnico/funcional de decisiones de dominio.

### Changed
- El segundo selector del formulario pasa de Subárea/Subcategoría a **Categoría**.
- El primer nivel permanece como **Área**.
- El módulo visible de cuentas utiliza **Usuario / Usuarios** en lugar de Persona / Personas.
- El backend expone las categorías habilitadas por Área.
- Las categorías pueden reutilizarse en múltiples Áreas.
- La documentación pasa a formar parte obligatoria del Definition of Done de cada feature.
- CI ejecuta la suite de regresión del backend además de compilación, build frontend e imágenes Docker.

### Compatibility
- `expenses.expense_type` se interpreta como Área.
- `expenses.expense_subcategory` se interpreta como Categoría.
- Las tablas legacy de clasificación se conservan temporalmente como puente para no romper datos históricos.
- La capa `frontend/src/domain-normalization.js` permanece temporalmente mientras el frontend monolítico se migra a contratos canónicos.

### Removed / Retired
- Se continúa el retiro de conceptos inmobiliarios específicos del núcleo de la aplicación.
- `Subárea` deja de ser término funcional para el segundo nivel de clasificación.
- `Persona / Personas` deja de ser término funcional para el dominio de cuentas.
