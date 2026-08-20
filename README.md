# Flujo de Control de Gastos

> Constitución vigente: **2.10.0**.

Aplicación web neutral respecto al tipo de organización para solicitar, evaluar, aprobar, votar, dar seguimiento, devolver a revisión, corregir, cancelar, cerrar y documentar gastos con trazabilidad y evidencia verificable.

## Principios del producto

- FastAPI es la autoridad final de autorización y transiciones.
- Toda estructura organizacional es dato configurable en PostgreSQL; no se hardcodean nombres de Roles, Grupos, Cargos, Áreas, Categorías ni niveles de acceso.
- `Usuario`, `Grupo`, `Rol`, `Permiso` y `Cargo/Posición` son conceptos separados.
- Grupo y Cargo pueden heredar Roles; sus nombres nunca autorizan por sí mismos.
- Todo usuario activo recibe baseline `requests:read` para Inicio/Solicitudes.
- `config:read` permite consultar Configuración sin mutarla.
- `config:manage` es administración técnica **system-only**.
- `areas:manage` permite administrar Área + Categoría sin entregar administración IAM.
- **Accesos es la única superficie administrativa para usuarios e IAM.** Usuarios/Personas y Organigrama no son pantallas independientes.
- Área y Categoría son dimensiones independientes y usan `expense_area` / `expense_category` como contrato canónico.
- Cierre/factura se autoriza por solicitud, no mediante `requests:close`.
- La persistencia vigente usa la base `ph_torre_delta` y el schema PostgreSQL dedicado `administracion`.
- La historia física anterior de base de datos no se conserva: la instalación vigente nace desde una baseline Alembic limpia.

## Terminología canónica

- **Usuario**: cuenta del sistema.
- **Grupo**: conjunto configurable de usuarios que puede heredar Roles.
- **Rol**: conjunto reutilizable de Permisos.
- **Permiso**: capacidad IAM atómica.
- **Cargo / Posición**: estructura organizacional configurable que puede heredar Roles.
- **Área**: unidad/departamento/función asociada al gasto.
- **Categoría**: naturaleza del bien/servicio.
- **Accesos**: consola única de Usuarios, Grupos, Roles, Permisos, Cargos y permisos efectivos.
- **Enviar a revisión**: decisión del aprobador para devolver inmediatamente la solicitud al solicitante.
- **Corregir / reenviar**: edición por solicitante original o Administrador del sistema.
- **Delegación de cierre/factura**: responsabilidad por solicitud concedida por el solicitante a otro usuario activo.

No usar `Personas` como módulo de cuentas ni `Subárea/Subcategoría` como equivalente de Categoría.

## IAM configurable

```text
Usuario
  ├─ Baseline: requests:read
  ├─ Grupos ───────────> Roles ──> Permisos
  ├─ Cargos/Posiciones -> Roles ──> Permisos
  ├─ Roles directos ─────────────> Permisos
  ├─ Permisos directos
  └─ Capacidades por recurso/delegación
```

Permisos vigentes:

| Código | Capacidad |
| --- | --- |
| `requests:read` | Seguimiento universal; baseline de usuarios activos |
| `requests:create` | Crear nuevas solicitudes |
| `requests:approve` | Aprobar, rechazar, votar y enviar a revisión cuando corresponda |
| `areas:manage` | Administrar Áreas, Categorías y relaciones |
| `config:read` | Consultar Configuración en modo solo lectura |
| `config:manage` | Administración técnica reservada a `system_accounts` |

`requests:close` permanece únicamente como registro legacy **inactivo** y no autoriza cierre/factura.

## Configuración y Accesos

Navegación objetivo:

```text
System Admin
→ Accesos
→ Áreas
→ Reglas
→ Auditoría / demás configuración técnica

Usuario con config:read
→ Accesos (solo lectura)
→ Áreas (solo lectura salvo areas:manage)
→ Reglas (solo lectura)
→ Auditoría (solo lectura)

Usuario con areas:manage sin config:read
→ Áreas solamente
```

**No existen entradas independientes de Usuarios/Personas u Organigrama.**

### Accesos

`Configuración → Accesos` administra:

- creación/activación/inactivación de Usuarios;
- Grupos y membresías;
- Roles y Permisos;
- Cargos/Posiciones;
- asignación de Cargos a Usuarios;
- Roles heredados por Grupo/Cargo;
- Roles directos;
- Permisos directos;
- permisos efectivos y fuentes.

Para `config:read`, la misma experiencia se presenta en modo solo lectura.

### Navegación desde Accesos

Accesos se monta actualmente con `#access-management`, pero la topbar debe seguir funcionando.

Desde Accesos responden en el mismo clic:

```text
Inicio
Solicitudes
Facturas
Auditoría
Configuración
Salir
```

`frontend/src/access-navigation-bridge.js` retira el hash antes de continuar la navegación. Abrir/cerrar solo el dropdown Configuración no abandona Accesos; seleccionar una opción navegable sí.

Ver [docs/CONFIGURATION_ACCESS.md](docs/CONFIGURATION_ACCESS.md) y Feature 011.

## Área + Categoría

Contrato canónico end-to-end:

```text
expense_area
expense_category
```

Los nombres `expense_type` / `expense_subcategory` son compatibilidad legacy y no deben usarse para nuevas APIs, modelos o documentación funcional.

La baseline `20260820_0001_initial_schema.py` crea directamente las columnas físicas `expense_area` y `expense_category`. No existe una migración vigente que primero cree nombres anteriores y luego los renombre.

El catálogo global y relaciones configurables permiten:

```text
Área ↔ Categoría (N:M)
```

Ver [docs/CLASSIFICATION_MODEL.md](docs/CLASSIFICATION_MODEL.md).

## Capacidades por recurso

```text
can_cancel
→ estado cancelable + (solicitante OR system_accounts)

can_correct
→ estado corregible + (solicitante OR system_accounts)

can_close
→ APPROVED/CLOSED + (solicitante OR system_accounts OR delegado activo)

can_delegate_close
→ solicitante original
```

Estas capacidades no son permisos IAM y el backend siempre las revalida.

## Dashboard y seguimiento

Todo usuario activo puede consultar Inicio y Solicitudes mediante `requests:read`.

Tareas contextuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

No son permisos IAM.

## Enviar a revisión

Un aprobador con una aprobación pendiente puede seleccionar **Enviar a revisión** con comentario útil.

```text
approval actual       → REVISION_REQUESTED
solicitud             → NEEDS_REVISION
otras PENDING/WAITING → EXPIRED
solicitante           → CORRECT_REQUEST
```

El aprobador no adquiere capacidad de edición.

## Corrección

Solo:

```text
solicitante original
OR
Administrador del sistema
```

Invariant:

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

El formulario canónico es `frontend/src/expense-form.jsx`.

## Cierre, factura y delegación

`APPROVED` no equivale a `CLOSED`.

Pueden gestionar cierre/factura:

```text
solicitante original
Administrador del sistema
delegado activo de esa solicitud
```

Solo el solicitante crea/cambia/revoca la delegación ordinaria. `requests:close` no participa en la autorización.

Ver [docs/CLOSURE_DELEGATION.md](docs/CLOSURE_DELEGATION.md).

## Administrador del sistema por ambiente

La cuenta técnica se identifica mediante `system_accounts`.

Producción:

```text
config:manage
config:read
areas:manage
requests:read
```

No participa en aprobación/votación. Conserva excepciones administrativas por recurso para cancelar, corregir y gestionar cierre/factura.

No producción puede recibir todos los permisos activos para pruebas E2E.

## Notificaciones de acceso

Al crear un usuario activo, la invitación con contraseña temporal incluye:

```text
Cargo(s) activos
Permisos efectivos actuales
```

Cuando cambia realmente `position_ids`, el sistema recalcula permisos efectivos y envía **Actualización de cargo y permisos**. Guardar el mismo Cargo no duplica el correo.

Fuente de verdad:

```text
Cargo(s)  → UserPosition / Position
Permisos  → effective_permission_codes()
```

Ver [docs/EMAIL_CONFIGURATION.md](docs/EMAIL_CONFIGURATION.md).

## Persistencia Neon por ambiente

Contrato canónico:

```text
DEV
DATABASE_URL=<URL Neon DEV / database ph_torre_delta>
DATABASE_SCHEMA=administracion

PROD / Render
DATABASE_URL=<URL Neon PROD / database ph_torre_delta>
DATABASE_SCHEMA=administracion
```

Estructura física:

```text
ph_torre_delta
└── administracion
    ├── users
    ├── roles
    ├── permissions
    ├── expenses
    ├── approvals
    ├── ...
    └── alembic_version
```

Reglas obligatorias:

- todas las tablas de aplicación viven bajo `administracion`;
- índices, constraints, secuencias, tipos ENUM, funciones/triggers propios y `alembic_version` usan el mismo schema;
- `public` no es schema de aplicación ni fallback;
- ninguna base/schema anterior es fuente de verdad para esta instalación;
- DEV y PROD nacen desde cero con la misma baseline;
- no se mueven, copian, clonan ni renombran tablas anteriores;
- no se migran ni backfillean datos legacy;
- no se usa `alembic stamp` para adoptar una estructura anterior;
- SQLAlchemy y Alembic resuelven `DATABASE_SCHEMA` centralmente;
- una baseline nueva aborta si encuentra tablas de aplicación preexistentes en `administracion`.

Ver [Feature 012](specs/012-neon-schema-isolation/spec.md).

## Alembic: nueva historia

La historia física vigente comienza aquí:

```text
20260820_0001_initial_schema
```

`down_revision = None`.

Las revisiones históricas `0000 → 0008` fueron retiradas de la rama vigente. Su propósito histórico queda documentado en HISTORY/CHANGELOG, pero no forman parte del despliegue nuevo.

La baseline inicial:

- crea el modelo actual directamente;
- crea `expense_area` / `expense_category` con sus nombres canónicos;
- crea la estructura IAM actual;
- siembra los permisos/roles técnicos mínimos;
- deja `requests:close` inactivo;
- conserva los guards append-only de auditoría;
- no importa usuarios, cargos, grupos, permisos ni datos de bases anteriores;
- exige que el schema destino esté vacío.

El backend arranca con:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Una vez desplegada `20260820_0001` en un ambiente persistente, **no debe reescribirse**. Cualquier cambio físico posterior crea una nueva revisión Alembic.

## Desarrollo local

```powershell
git fetch origin
git switch feature/neon-ph-torre-delta-schema
git pull origin feature/neon-ph-torre-delta-schema

docker compose up -d --build
```

Ver estado:

```powershell
docker compose ps
docker compose logs --tail=100 backend
```

Gates recomendados:

```text
cd backend
alembic heads
# esperado: 20260820_0001

python -m unittest discover -s tests -v

cd ../frontend
npm ci
npm run build
```

Para Feature 012, después de ejecutar la baseline en DEV validar:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'administracion'
ORDER BY table_name;
```

Y confirmar que no existan tablas de aplicación nuevas en `public`.

Para cambios de Accesos validar manualmente:

```text
Accesos → Inicio
Accesos → Solicitudes
Accesos → Facturas
Accesos → Auditoría
Accesos → Configuración → otra pantalla
Accesos → Salir
```

## Arquitectura

```text
frontend/   React + Vite
backend/    FastAPI + SQLAlchemy + Alembic
Neon        PostgreSQL persistencia DEV/PROD
```

Componentes relevantes:

```text
frontend/src/expense-form.jsx
frontend/src/home-dashboard.jsx
frontend/src/closure-delegation.jsx
frontend/src/iam-admin.jsx
frontend/src/access-navigation-bridge.js
frontend/src/config-readonly.js
frontend/src/classification-admin.js
```

FastAPI mantiene routers, schemas, servicios y modelos separados. SQLAlchemy y Alembic resuelven el schema de aplicación desde configuración central. El frontend puede usar bridges legacy de forma temporal, pero esos bridges no reemplazan la autorización backend.

## Documentación

Autoridad documental:

1. [.specify/memory/constitution.md](.specify/memory/constitution.md)
2. `specs/**/spec.md`
3. checklists de aceptación
4. `specs/**/plan.md`
5. [PROMPT_RECONSTRUCCION.md](PROMPT_RECONSTRUCCION.md)
6. este README
7. [docs/](docs/README.md)
8. código legacy cuando exista discrepancia documentada

Feature vigente de persistencia: [specs/012-neon-schema-isolation/spec.md](specs/012-neon-schema-isolation/spec.md).  
Feature vigente para consolidación de Accesos: [specs/011-access-console-consolidation/spec.md](specs/011-access-console-consolidation/spec.md).

## Deuda explícita

Permanecen temporalmente en código sin ser autoridad runtime ni arquitectura objetivo:

- `UserRole` y flags `can_*` legacy;
- `AccessProfile` y `BOARD_CODES`;
- `/api/users` legacy;
- vistas internas `people` / `organization` no navegables;
- `main.jsx`, `domain-normalization.js` y bridges Vite;
- aliases `expense_type` / `expense_subcategory` de compatibilidad interna.

La compatibilidad de código legacy no implica conservar la base anterior. La fuente física vigente es la instalación limpia de `ph_torre_delta.administracion`.
