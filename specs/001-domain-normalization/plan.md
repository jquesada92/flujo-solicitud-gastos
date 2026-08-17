# Technical Plan — 001 Domain Normalization

## Contexto

Stack existente:

- React + Vite en Vercel;
- FastAPI + SQLAlchemy en Docker/Render;
- PostgreSQL/Neon;
- Brevo HTTPS API;
- almacenamiento privado en disco persistente de Render.

La feature debe evolucionar el repositorio existente sin crear una aplicación paralela.

## Cambios de dominio

### Usuarios

La entidad técnica canónica continúa siendo `User` y el API continúa bajo `/api/users`. El cambio principal es de terminología funcional: Persona/Personas → Usuario/Usuarios.

### Área

`ExpenseArea` representa la dimensión organizacional. Por compatibilidad temporal continúa mapeada a la tabla física legacy `expense_categories`.

### Categoría

Se introduce un catálogo global independiente `expense_category_catalog`.

### Relación Área-Categoría

Se introduce `expense_area_categories` con unicidad por `(area_id, category_id)`.

La tabla legacy `expense_subcategories` permanece temporalmente sincronizada como puente para no invalidar datos y validaciones históricas del MVP.

## API

Contrato principal:

- `GET /api/areas`
- `POST /api/areas`
- `PATCH /api/areas/{area_id}`
- `GET /api/areas/categories`
- `POST /api/areas/categories`
- `PATCH /api/areas/categories/{category_id}`
- `POST /api/areas/{area_id}/categories`
- `POST /api/areas/{area_id}/categories/{category_id}`
- `DELETE /api/areas/{area_id}/categories/{category_id}`

Los endpoints legacy `/api/categories` solo pueden existir mediante compatibilidad temporal del frontend; no son el contrato canónico.

## Frontend

Mientras `frontend/src/main.jsx` siga siendo monolítico, `domain-normalization.js` funciona como capa de transición para:

- redirigir contratos legacy hacia `/api/areas`;
- adaptar `categories` del Área hacia estructuras que el frontend legacy todavía espera;
- transformar Subárea/Subcategoría a Categoría en texto visible;
- transformar Persona/Personas a Usuario/Usuarios.

Esta capa es temporal y debe eliminarse cuando `main.jsx` sea modularizado y consuma los contratos canónicos directamente.

## Dominio inmobiliario

El código activo no debe depender de:

- `Apartment`;
- `UserApartment`;
- `ApartmentChangeEvent`;
- `OwnershipRole`;
- `PersonType`;
- `apartment_number`;
- endpoints `/apartments`.

La eliminación física de tablas/columnas legacy se ejecuta mediante una migración destructiva separada y backup-gated. No debe ejecutarse automáticamente al arrancar FastAPI.

## Migración y compatibilidad

Fase actual:

1. cambiar contratos y dominio activo;
2. preservar datos físicos legacy cuando son necesarios para compatibilidad;
3. validar funcionamiento;
4. realizar backup antes de limpieza destructiva;
5. retirar nombres/tablas legacy en una feature posterior con migración versionada.

No se permite asumir que recrear una tabla en `downgrade()` recupera sus datos.

## Seguridad

- Backend sigue siendo autoridad final.
- La capa de terminología del frontend no puede conceder permisos.
- Descargas/documentos siguen protegidos por backend.
- No introducir secretos en Vite ni logs.

## Testing

CI debe ejecutar:

```text
python -m compileall -q app
python -m unittest discover -s tests -v
npm ci
npm run build
Docker build backend
Docker build frontend
```

Además, una migración destructiva posterior deberá probar restauración/rollback operativo, no solo estructura.

## Documentación obligatoria de la feature

La implementación debe mantener sincronizados:

- `.specify/memory/constitution.md`;
- este `spec.md`;
- este `plan.md`;
- `checklists/acceptance.md`;
- `README.md`;
- `PROMPT_RECONSTRUCCION.md`;
- `docs/CLASSIFICATION_MODEL.md`;
- `docs/TERMINOLOGY.md`;
- `docs/HISTORY.md`;
- `CHANGELOG.md`.

## Riesgos conocidos

- `main.jsx` todavía contiene terminología y contratos legacy internamente.
- nombres físicos de clasificación todavía reflejan el modelo anterior.
- `domain-normalization.js` es una solución de transición, no arquitectura final.
- el modelo de autorización aún requiere una feature separada para ser completamente DB-driven.

Estos riesgos deben permanecer visibles en documentación hasta que se retiren realmente del código.
