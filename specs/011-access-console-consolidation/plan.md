# Plan — Consolidación de Usuarios y Organigrama en Accesos

**Feature:** 011  
**Constitución:** 2.9.0

## Resultado objetivo

Llegar a una única superficie administrativa de identidad/IAM:

```text
Configuración
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría / configuración técnica
```

sin eliminar el modelo persistido de Usuario/Grupo/Rol/Permiso/Cargo.

## Fase 1 — Sincronizar rama base

- [x] integrar cambios faltantes de `main` en `agent/consolidate-users-organigram-in-access`;
- [x] incorporar Alembic `0008` y cambios asociados de `expense_area` / `expense_category`;
- [x] confirmar que la rama queda 0 commits detrás de `main` al momento de la sincronización;
- [ ] ejecutar localmente `alembic heads` y `alembic current` en el head final.

Regla: no usar `alembic stamp` para ocultar una revisión ausente o un esquema físico desalineado.

## Fase 2 — Consolidar navegación de Configuración

Frontend:

- [x] retirar **Usuarios/Personas** de la navegación normal;
- [x] retirar **Organigrama** de la navegación normal;
- [x] conservar **Accesos** como único punto de Usuarios/Grupos/Roles/Permisos/Cargos;
- [x] mantener cualquier vista `people` / `organization` solo como compatibilidad interna temporal;
- [x] impedir que esas vistas vuelvan a ser fuente de verdad administrativa.

Backend:

- [x] no eliminar APIs ni relaciones IAM;
- [x] mantener `config:manage` system-only;
- [x] mantener `config:read` como lectura configurable;
- [x] mantener `areas:manage` separado;
- [x] no introducir autorización por nombres de Cargo/Grupo/Rol.

## Fase 3 — Accesos editable y solo lectura

System Admin:

```text
Accesos → Usuarios + Grupos + Roles + Permisos + Cargos + asignaciones
```

`config:read`:

```text
Accesos → misma información sin controles efectivos de mutación
```

Validar:

- [x] creación de Usuario permanece dentro de Accesos;
- [x] asignación de Cargo permanece dentro de Accesos;
- [x] Grupos, Roles y Permisos permanecen dentro de Accesos;
- [x] permisos efectivos/fuentes permanecen visibles;
- [ ] validar manualmente edición de un usuario existente después del pull final.

## Fase 4 — Reparar navegación global desde Accesos

Problema:

```text
Accesos montado por #access-management
+ navegación React subyacente
→ cambio de tab podía ocurrir sin desmontar Accesos
```

Implementación:

- [x] crear `frontend/src/access-navigation-bridge.js`;
- [x] cargarlo antes de `main.jsx` en `frontend/index.html`;
- [x] escuchar clicks de `.topbar` en capture phase;
- [x] retirar `#access-management` antes de continuar la navegación;
- [x] no retirar el hash al abrir/cerrar solamente el dropdown Configuración;
- [x] sí retirarlo al seleccionar una opción navegable del dropdown;
- [x] cubrir destino igual a la pestaña React subyacente activa.

Contrato manual:

```text
Accesos → Inicio
Accesos → Solicitudes
Accesos → Facturas
Accesos → Auditoría
Accesos → Configuración → otra pantalla
Accesos → Salir
```

## Fase 5 — Clasificación canónica

- [x] conservar `expense_area` y `expense_category` como nombres canónicos;
- [x] conservar `0008` en la cadena activa;
- [x] documentar `expense_type` / `expense_subcategory` como aliases legacy únicamente;
- [x] actualizar CLASSIFICATION_MODEL, README, prompt y Constitución;
- [ ] validar localmente migración/head contra PostgreSQL final.

Cadena esperada:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

## Fase 6 — Pruebas automatizadas

Contratos existentes/relevantes:

- [x] `test_access_navigation_bridge.py` agregado;
- [x] `test_frontend_configuration_access.py` protege la integración de Accesos;
- [x] tests de clasificación protegen contrato Área/Categoría;
- [x] tests de migraciones reconocen `0008` después de sincronizar main;
- [ ] ejecutar test específico de navegación en head final;
- [ ] ejecutar suite backend completa en head final;
- [ ] ejecutar `npm run build` en head final.

## Fase 7 — Documentación / Spec-Kit

Actualizar como conjunto coherente:

- [x] `.specify/memory/constitution.md` → **2.9.0**;
- [x] `specs/011-access-console-consolidation/spec.md`;
- [x] `specs/011-access-console-consolidation/plan.md`;
- [x] `specs/011-access-console-consolidation/checklists/acceptance.md`;
- [x] `README.md`;
- [x] `PROMPT_RECONSTRUCCION.md`;
- [x] `docs/CONFIGURATION_ACCESS.md`;
- [x] `docs/IAM_MODEL.md`;
- [x] `docs/CLASSIFICATION_MODEL.md`;
- [x] `docs/TERMINOLOGY.md`;
- [x] `docs/FASTAPI_ARCHITECTURE.md`;
- [x] `docs/README.md`;
- [x] `docs/DOCUMENTATION_POLICY.md`;
- [x] `docs/HISTORY.md`;
- [x] `CHANGELOG.md`.

## Fase 8 — Gates locales finales

Desde la raíz:

```powershell
git fetch origin
git switch agent/consolidate-users-organigram-in-access
git pull origin agent/consolidate-users-organigram-in-access
```

Backend:

```powershell
cd backend
alembic heads
alembic current
python -m unittest tests.test_access_navigation_bridge -v
python -m unittest discover -s tests -v
```

Frontend:

```powershell
cd ../frontend
npm ci
npm run build
```

Docker:

```powershell
cd ..
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 backend
```

Validación manual:

```text
1. abrir Accesos;
2. probar cada destino de la topbar;
3. confirmar que Configuración abre/cierra sin salir;
4. seleccionar Áreas/Reglas desde Configuración y confirmar salida de Accesos;
5. crear/editar un usuario desde Accesos;
6. confirmar ausencia de Usuarios/Personas y Organigrama como entradas independientes.
```

## Criterio de cierre

Feature 011 puede considerarse terminada cuando:

- documentación esté sincronizada;
- `alembic current`/`heads` sean compatibles;
- suite backend pase;
- build frontend pase;
- navegación manual desde Accesos pase;
- edición de usuario dentro de Accesos se valide;
- no quede una ruta navegable que vuelva a presentar Usuarios/Personas u Organigrama como fuente administrativa independiente.
