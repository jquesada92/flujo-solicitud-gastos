# Plan — Consolidación de Usuarios y Organigrama en Accesos

**Feature:** 011  
**Constitución:** 2.9.0

## Frontend

- retirar **Usuarios/Personas** y **Organigrama** de la navegación de Configuración;
- mantener **Accesos** como punto único para Usuarios, Grupos, Roles, Permisos y Cargos;
- conservar el modo solo lectura de Accesos para `config:read`;
- no duplicar formularios o lógica IAM en vistas legacy;
- dejar cualquier vista legacy no navegable como compatibilidad temporal hasta su limpieza;
- verificar que el plugin/bridge de Vite continúe compilando después del cambio de menú.

## Backend

- no eliminar APIs ni relaciones IAM por este cambio;
- mantener `config:manage` como system-only y `config:read` como lectura;
- mantener resolución de permisos efectivos desde relaciones persistidas;
- no introducir reglas por nombre de Cargo, Grupo o Rol.

## Clasificación de solicitudes

- conservar `expense_area` y `expense_category` como nombres canónicos;
- mantener la migración Alembic `20260819_0008` o cualquier sucesora equivalente en la cadena activa;
- no volver a modelar `expense_type` / `expense_subcategory` como contrato vigente;
- al integrar ramas, validar que código, modelos y volumen PostgreSQL apunten a una revisión Alembic disponible en la rama activa.

## Documentación

Actualizar como un conjunto coherente:

- `.specify/memory/constitution.md`;
- Feature 011 (`spec.md`, `plan.md`, checklist);
- `README.md`;
- `PROMPT_RECONSTRUCCION.md`;
- `docs/CONFIGURATION_ACCESS.md`;
- `docs/README.md`;
- `docs/HISTORY.md`;
- `CHANGELOG.md`.

## Pruebas

- System Admin ve **Accesos** pero no Usuarios/Personas ni Organigrama como entradas independientes;
- `config:read` usa Accesos en modo lectura y no obtiene mutaciones;
- `areas:manage` no obtiene administración IAM;
- creación/edición de usuarios sigue disponible dentro de Accesos;
- Cargos y permisos efectivos siguen configurables desde Accesos;
- `npm run build` completa sin errores del transform de Vite;
- suite backend continúa verde;
- `alembic heads` y `alembic current` son compatibles con la rama activa.

## Gates locales

```text
git fetch origin
git switch agent/consolidate-users-organigram-in-access
git pull origin agent/consolidate-users-organigram-in-access

cd backend
alembic heads
python -m unittest discover -s tests -v

cd ../frontend
npm run build
```

No se elimina ninguna tabla IAM ni se requiere una migración nueva exclusivamente por la consolidación de navegación.
