# Plan técnico — IAM configurable y hardening FastAPI

> Constitución vigente: **2.9.0**.  
> Feature 002 fue evolucionada por Features 003–011; este plan refleja el estado técnico actual.

## Arquitectura objetivo

```text
Frontend React/Vite
  ├─ shell legacy en transición
  ├─ Accesos / IAM
  ├─ configuración Área + Categoría
  └─ componentes modulares
       ↓ HTTPS
FastAPI
  ├─ api/
  ├─ schemas/
  ├─ services/
  ├─ models/
  └─ core/
       ↓
PostgreSQL
```

## Modelo IAM

Tablas canónicas:

```text
permissions
roles
role_permissions
user_groups
group_members
group_roles
user_role_assignments
user_permissions
positions
user_positions
position_roles
system_accounts
```

`UserRole`, `users.title`, `can_*`, `AccessProfile` y `BOARD_CODES` son compatibilidad temporal.

## Resolución de permisos

Usuario ordinario activo:

```text
{requests:read}
∪ permiso directo
∪ Rol directo
∪ Grupo → Rol → Permiso
∪ Cargo → Rol → Permiso
- {config:manage}
```

Permisos actuales:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage  # system-only
```

`requests:close` es legacy inactivo.

## Cuenta técnica

```text
ENVIRONMENT=production
→ requests:read + areas:manage + config:read + config:manage
→ sin requests:create / requests:approve
→ capacidades administrativas por recurso para cancel/correct/close

ENVIRONMENT!=production
→ todos los permisos atómicos activos para testing E2E
```

Identidad siempre desde `system_accounts`.

## API IAM / Accesos

Base `/api/iam` mantiene:

- permisos;
- roles;
- grupos;
- miembros;
- roles de grupos;
- cargos/posiciones;
- roles de cargos;
- usuarios IAM;
- asignaciones directas;
- permisos efectivos/fuentes.

La superficie canónica es **Configuración → Accesos**.

Feature 011 retira Usuarios/Personas y Organigrama como entradas independientes.

`config:read` permite consultas de Accesos en modo read-only; mutaciones requieren administración técnica.

## Rutas de solicitudes

- creación → `request_actions.py` + `requests:create`;
- corrección/reenvío → `revision_actions.py` + regla por recurso;
- votación/aprobación → `requests:approve` + asignación contextual;
- cierre/factura → `financial_actions.py` + `can_manage_closure()`;
- documentos → autorización por operación;
- seguimiento → `requests:read` baseline.

`requests:close` no protege endpoints financieros.

## Capacidades por recurso

```text
can_cancel
can_correct
can_close
can_delegate_close
```

El backend las calcula y revalida.

## Área + Categoría

Contratos vigentes:

```text
expense_area
expense_category
```

`areas.py` es API canónica de catálogos y relaciones. Escrituras usan `areas:manage`.

## Password hashing

- Argon2 para hashes nuevos;
- PBKDF2 legacy verificable temporalmente;
- login exitoso puede migrar hash;
- cambio de contraseña genera Argon2.

## Settings

`app/core/config.py` centraliza DB, JWT/sesión, CORS, rate limits, documentos, correo, bootstrap, timezone y ambiente funcional.

`ENVIRONMENT=production` es la señal de segregación funcional.

## Migraciones y startup

Cadena actual:

```text
0000 baseline
 ↓
0001 IAM foundation
 ↓
0002 system accounts
 ↓
0003 MULTI_QUOTE repair
 ↓
0004 position_roles
 ↓
0005 closure delegation
 ↓
0006 areas:manage
 ↓
0007 config:read
 ↓
0008 expense_area / expense_category
```

`FastAPI.lifespan` no ejecuta DDL/backfills.

Docker:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

No usar `alembic stamp` para esconder una revisión ausente o esquema incompatible.

## Portabilidad Windows → Linux

- `*.sh` en LF mediante `.gitattributes`;
- Docker normaliza CRLF defensivamente;
- bootstrap como módulo desde raíz backend;
- frontend espera healthcheck backend.

## Frontend actual

Componentes relevantes:

```text
frontend/src/iam-admin.jsx
frontend/src/access-navigation-bridge.js
frontend/src/config-readonly.js
frontend/src/classification-admin.js
frontend/src/expense-form.jsx
frontend/src/home-dashboard.jsx
frontend/src/closure-delegation.jsx
```

Mientras `main.jsx` siga parcialmente legacy, `vite.config.js` puede aplicar transforms fail-fast. Bridges no son autoridad de seguridad.

## Navegación de Accesos

`#access-management` es una integración transitoria.

`access-navigation-bridge.js` se carga antes de `main.jsx` y limpia el hash en capture phase al navegar fuera de Accesos, incluso cuando el destino ya es la pestaña subyacente activa.

## Testing

Matriz mínima vigente:

- permisos efectivos por direct/role/group/position;
- `config:manage` system-only;
- `config:read` read-only;
- `areas:manage` aislado;
- cuenta técnica prod/no-prod;
- capacidades por recurso;
- navegación desde Accesos;
- clasificación `expense_area` / `expense_category`;
- migraciones con un solo head hasta `0008`;
- portabilidad de contenedor.

Gates:

```text
cd backend
alembic heads
alembic current
python -m unittest discover -s tests -v

cd ../frontend
npm ci
npm run build
```

## Despliegue

1. backup/snapshot antes de cambios riesgosos;
2. construir imagen backend;
3. ejecutar/validar Alembic en preview;
4. ejecutar bootstrap;
5. iniciar FastAPI y verificar `/api/health`;
6. validar política de permisos del ambiente;
7. validar Accesos/configuración y workflows con usuarios apropiados;
8. promover a producción.

## Rollback

No depender exclusivamente de downgrade para recuperar datos. Usar snapshot/backup cuando una migración modifica estructura o datos relevantes.

## Documentación

Mantener sincronizados Constitución, features específicas posteriores, README, prompt maestro, IAM_MODEL, FASTAPI_ARCHITECTURE, HISTORY y CHANGELOG.
