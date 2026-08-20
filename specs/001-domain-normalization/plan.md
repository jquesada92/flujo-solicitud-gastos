# Technical Plan — 001 Domain Normalization

**Constitución vigente:** 2.9.0

## Contexto

Stack vigente:

- React + Vite;
- FastAPI + SQLAlchemy + Alembic;
- PostgreSQL;
- Vercel/Render para producción;
- Brevo en producción y SMTP local.

La feature evoluciona el repositorio existente; no crea una aplicación paralela.

## Usuarios

La entidad canónica continúa siendo `User`.

Terminología visible:

```text
Persona/Personas → Usuario/Usuarios
```

Evolución vigente por Feature 011:

```text
Configuración → Accesos → Usuarios
```

No existe un módulo Usuarios independiente en navegación.

## Área + Categoría

### Área

Dimensión organizacional asociada al gasto.

### Categoría

Catálogo global independiente.

### Relación

`expense_area_categories` mantiene N:M con unicidad por `(area_id, category_id)`.

## Contrato de solicitud

Estado vigente después de Alembic `0008`:

```text
expense_area
expense_category
```

Los nombres físicos `expense_type` / `expense_subcategory` ya no son el estado objetivo ni el estado actual de `expenses`; solo pueden aparecer como aliases/código legacy transitorio.

## API

Contrato canónico de catálogos:

```text
GET    /api/areas
POST   /api/areas
PATCH  /api/areas/{area_id}
GET    /api/areas/categories
POST   /api/areas/categories
PATCH  /api/areas/categories/{category_id}
POST   /api/areas/{area_id}/categories
POST   /api/areas/{area_id}/categories/{category_id}
DELETE /api/areas/{area_id}/categories/{category_id}
```

Contratos nuevos de solicitudes usan `expense_area` / `expense_category`.

## Frontend

Mientras el shell siga parcialmente legacy:

- `domain-normalization.js` puede adaptar contratos/textos legacy;
- `classification-admin.js` maneja la experiencia canónica de Área + Categoría;
- nuevo código no debe introducir `expense_type` / `expense_subcategory` como contrato;
- Usuarios se gestionan desde `iam-admin.jsx`/Accesos, no desde una pantalla Persona/Usuario separada.

## Dominio inmobiliario

Código activo no debe depender de:

```text
Apartment
UserApartment
ApartmentChangeEvent
OwnershipRole
PersonType
apartment_number
```

La eliminación física destructiva de cualquier residuo se ejecuta mediante migración/procedimiento separado y backup-gated.

## Migraciones y evolución

Evolución relevante:

```text
0003 → reparación de request_type MULTI_QUOTE
0004 → position_roles / IAM por Cargo
0005 → delegación de cierre
0006 → areas:manage
0007 → config:read
0008 → expense_area / expense_category físicos
```

No hacer `stamp` para ocultar incompatibilidad de esquema.

## Seguridad

- backend sigue siendo autoridad final;
- terminología frontend no concede permisos;
- `areas:manage` protege escrituras del catálogo;
- `config:read` solo lectura;
- `config:manage` system-only;
- ningún nombre organizacional autoriza por sí mismo.

## Testing

Gates actuales:

```text
cd backend
alembic heads
alembic current
python -m unittest discover -s tests -v

cd ../frontend
npm ci
npm run build
```

Contratos específicos de `expense_area` / `expense_category` y clasificación deben permanecer verdes.

## Documentación

Mantener sincronizados:

- Constitución;
- spec/plan/checklist de Feature 001 cuando cambie el dominio;
- Feature 009/011 cuando cambien configuración/navegación;
- README;
- prompt maestro;
- CLASSIFICATION_MODEL;
- TERMINOLOGY;
- HISTORY;
- CHANGELOG.

## Deuda vigente

- `domain-normalization.js` es transitorio;
- `main.jsx` conserva código legacy;
- puede existir compatibilidad interna con nombres antiguos, pero no como contrato canónico;
- limpieza destructiva residual se mantiene separada y explícita.
