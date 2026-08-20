# Acceptance Checklist — 001 Domain Normalization

**Constitución vigente:** 2.9.0

> Los gates de ejecución local permanecen sin marcar hasta ser ejecutados realmente.

## Terminología

- [x] producto usa **Usuario/Usuarios**, no Persona/Personas como módulo canónico.
- [x] Usuarios se administra dentro de **Accesos**, no mediante una pantalla independiente.
- [x] formulario de solicitud usa **Área** y **Categoría**.
- [x] segundo selector no se presenta como Subárea/Subcategoría funcional.
- [x] `docs/TERMINOLOGY.md` está alineado con Constitución 2.9.0.

## Clasificación

- [x] Área representa unidad/departamento/función organizacional.
- [x] Categoría representa naturaleza del bien/servicio.
- [x] Área y Categoría son catálogos independientes.
- [x] una Categoría puede vincularse a múltiples Áreas.
- [x] no se requieren duplicados lógicos por Área.
- [x] formulario ofrece Categorías habilitadas para el Área.
- [x] desactivar/desvincular no reescribe solicitudes históricas.
- [x] `expense_area` es el campo canónico.
- [x] `expense_category` es el campo canónico.
- [x] `expense_type` / `expense_subcategory` se documentan como aliases legacy únicamente.

## Persistencia / migración

- [x] Alembic `0008` renombra físicamente las columnas de `expenses`.
- [x] documentación ya no afirma que `expense_type` / `expense_subcategory` sean los nombres físicos vigentes.
- [x] contratos canónicos `/api/areas` están documentados.
- [ ] ejecutar `alembic heads` en head final.
- [ ] ejecutar `alembic current` contra PostgreSQL local final.

## Dominio inmobiliario

- [x] dominio canónico no incluye Apartment/UserApartment/ApartmentChangeEvent/OwnershipRole/PersonType/apartment_number.
- [x] limpieza física destructiva se mantiene separada del startup y backup-gated.

## Seguridad

- [x] backend continúa siendo autoridad de permisos.
- [x] normalización visual no concede acceso.
- [x] `areas:manage`, `config:read` y `config:manage` siguen sus fronteras actuales.
- [x] nombres organizacionales no autorizan por sí mismos.

## Pruebas y build

- [ ] `python -m unittest discover -s tests -v` pasa en head final.
- [ ] `npm ci` pasa en head final.
- [ ] `npm run build` pasa en head final.
- [ ] Docker backend/frontend construyen en head final.

## Documentación

- [x] Constitución 2.9.0 actualizada.
- [x] Feature 001 spec actualizado.
- [x] Feature 001 plan actualizado.
- [x] checklist actualizado.
- [x] README actualizado.
- [x] PROMPT_RECONSTRUCCION actualizado.
- [x] CLASSIFICATION_MODEL actualizado.
- [x] TERMINOLOGY actualizado.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [x] Feature 011 documenta la consolidación de Usuarios en Accesos.

## Definition of Done

La normalización documental actual queda sincronizada. Los gates locales solo pueden marcarse completos después de su ejecución real.
