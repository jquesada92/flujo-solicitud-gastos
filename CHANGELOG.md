# Changelog

## 2026-08-17

### Added
- Catálogo global de Categorías independiente de Áreas.
- Relación configurable Área ↔ Categoría.
- Documentación funcional del modelo de clasificación.
- Historial técnico/funcional de la migración del dominio.

### Changed
- El segundo selector del formulario pasa de Subárea/Subcategoría a **Categoría**.
- El primer nivel permanece como **Área**.
- El backend expone las categorías habilitadas por Área.
- Las categorías pueden reutilizarse en múltiples Áreas.

### Compatibility
- `expenses.expense_type` se interpreta como Área.
- `expenses.expense_subcategory` se interpreta como Categoría.
- Las tablas legacy de clasificación se conservan temporalmente como puente para no romper datos históricos.

### Removed / Retired
- Se continúa el retiro de conceptos inmobiliarios específicos del núcleo de la aplicación.
