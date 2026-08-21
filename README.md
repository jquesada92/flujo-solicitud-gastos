# Flujo de Control de Gastos

> Constitución vigente: **2.13.0**.

Aplicación web para registrar, evaluar, aprobar, votar, seguir, corregir, cancelar, cerrar y documentar solicitudes de gasto con trazabilidad. El producto es neutral respecto al tipo de organización: la estructura se configura como datos y los nombres organizacionales no forman parte de la lógica de autorización.

## Contrato actual en una página

```text
Usuario activo
├─ requests:read (baseline)
├─ 0..1 Cargo organizacional
├─ 0..N Roles globales
└─ 0..N Grupos
      └─ máximo 1 Rol por Grupo
            └─ Permisos
```

Reglas clave:

- un Grupo puede existir sin Roles;
- cada Rol puede pertenecer a cero o un Grupo;
- un Rol sin Grupo es global;
- el Rol agrupado asignado al Usuario determina su membresía en ese Grupo;
- un Usuario puede tener máximo un Rol por Grupo y varios Roles globales;
- no hay permisos individuales;
- Cargo no concede permisos;
- un Usuario puede tener como máximo un Cargo;
- FastAPI es la autoridad de autorización;
- los cambios de acceso se guardan explícitamente con **Guardar cambios**;
- Inicio es personal; Seguimiento es una vista de equipo de solo lectura;
- una pantalla privada sin sesión vuelve al Login;
- el frontend no debe hacer polling agresivo ni repetir GET idénticos innecesariamente.

Ver [docs/CURRENT_PRODUCT_CONTRACT.md](docs/CURRENT_PRODUCT_CONTRACT.md).

## Terminología

| Término | Significado |
| --- | --- |
| Usuario | Cuenta autenticable |
| Grupo | Ámbito organizacional opcional con cero o más Roles |
| Rol | Conjunto de Permisos; puede ser global o pertenecer a un Grupo |
| Rol global | Rol sin Grupo |
| Permiso | Capacidad IAM atómica |
| Cargo / Posición | Metadato organizacional, sin autoridad IAM |
| Área | Contexto organizacional del gasto |
| Categoría | Naturaleza del bien/servicio |
| Inicio | Mis pendientes y mis solicitudes |
| Seguimiento | Carga del equipo por Grupo/miembro/Rol |
| Accesos | Administración de Usuarios, Grupos, Roles y Permisos |

## IAM

Permisos funcionales vigentes:

| Código | Capacidad |
| --- | --- |
| `requests:read` | Consultar y seguir solicitudes; baseline de usuario activo |
| `requests:create` | Crear una solicitud nueva |
| `requests:approve` | Aprobar, rechazar, votar y enviar a revisión cuando corresponda |
| `areas:manage` | Administrar Área + Categoría |
| `config:read` | Consultar Configuración sin mutar |
| `config:manage` | Administración técnica protegida |

`requests:close` es un registro inactivo de compatibilidad; el cierre se autoriza por solicitud.

### Resolución de permisos

```text
Usuario ordinario activo
= requests:read
+ Permisos de sus Roles globales activos
+ Permisos de sus Roles agrupados dentro de Grupos activos
- config:manage
```

Un Grupo no entrega todos sus Roles a todos sus miembros: cada Usuario tiene como máximo un Rol concreto dentro de ese Grupo. Los Roles globales no crean membresía.

La cuenta técnica se identifica con `system_accounts`. En producción su política efectiva es `requests:read + areas:manage + config:manage`. El Rol `Administrador del sistema` es global, técnico y protegido; el bootstrap lo asigna como representación de responsabilidad, pero la autoridad real sigue siendo `SystemAccount`.

Ver [docs/IAM_MODEL.md](docs/IAM_MODEL.md).

## Accesos

La consola muestra:

```text
Usuarios → Acceso por grupo → selector de Rol
         → Roles globales   → selección múltiple
Grupos   → Roles opcionales + miembros derivados
Roles    → Permisos
Permisos → catálogo
```

Seleccionar opciones no guarda inmediatamente. La persistencia ocurre al pulsar **Guardar cambios**. Al cambiar de usuario/grupo con cambios pendientes se solicita confirmación.

Los miembros de un Grupo se derivan de las asignaciones de Roles agrupados. Cargo no forma parte de la autorización de esta consola.

Quitar un Rol de un Grupo lo convierte en global sin borrar sus asignaciones de Usuario. Vincular Roles globales a un Grupo se rechaza si eso produciría más de un Rol del mismo Grupo para algún Usuario.

## Inicio y Seguimiento

### Inicio

Vista rápida de la persona conectada:

- acciones que requieren su atención;
- solicitudes propias en proceso;
- métricas personales;
- modal contextual para aprobar, votar, corregir o cerrar cuando exista una tarea vigente.

### Seguimiento

Vista de equipo de solo lectura:

- Grupos activos;
- miembros y sus Roles agrupados;
- pendientes por usuario;
- pendientes agregados por Grupo;
- búsqueda y filtro de usuarios con pendientes.

Los Roles globales no generan membresía en Seguimiento.

## Nueva solicitud

El formulario se muestra únicamente a quien tenga `requests:create`. Tener `requests:read` no es suficiente.

Contrato canónico:

```text
expense_area
expense_category
```

Área y Categoría son catálogos independientes con relación N:M configurable.

Tipos:

```text
SIMPLE
MULTI_QUOTE
```

Las correcciones conservan el tipo original.

En `MULTI_QUOTE`, la población votante se congela por ronda desde usuarios activos con `requests:approve`, excluyendo al solicitante. La ronda espera todos los votos y solo se resuelve con ganador único; un empate permanece abierto. Ver [docs/MULTI_QUOTE_VOTING.md](docs/MULTI_QUOTE_VOTING.md).

## Revisión, corrección y cierre

`REVISION_REQUESTED` interrumpe la ronda, lleva la solicitud a `NEEDS_REVISION`, expira decisiones pendientes restantes y crea `CORRECT_REQUEST` para el solicitante.

Capacidades por recurso:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

Cerrar/facturar depende de ser solicitante, Administrador del sistema o delegado activo de esa solicitud; no depende de un permiso global de cierre.

## Sesión y frontend

Los hashes privados como `#access-management` y `#user-tracking` requieren sesión. Sin token se limpia la ruta privada y se muestra Login; un `401` invalida la sesión almacenada.

El frontend aplica una política transversal de requests:

- carga inicial al montar;
- GET idénticos concurrentes deduplicados;
- caché corta para repeticiones automáticas;
- mutaciones invalidan lecturas;
- interacción explícita puede forzar datos frescos;
- sin polling sub-segundo.

Ver [docs/FRONTEND_RUNTIME.md](docs/FRONTEND_RUNTIME.md).

## Persistencia

```text
Database: ph_torre_delta
Schema:   administracion
```

Todas las tablas, `alembic_version` y objetos propios de aplicación viven bajo `administracion`. El backend puede usar el endpoint pooled de Neon porque no envía `search_path` como startup option; el schema se resuelve explícitamente en SQLAlchemy/Alembic.

Cadena actual:

```text
20260820_0001_initial_schema
→ 20260820_0002_group_scoped_roles
→ 20260821_0003_single_user_position
→ 20260821_0004_allow_global_roles
```

`0002` fija que un Rol no puede pertenecer a más de un Grupo y un Usuario no puede tener dos Roles del mismo Grupo. `0003` fija un Cargo por Usuario. `0004` permite Roles globales sin relajar la restricción de un Rol por Grupo.

## Despliegue

Backend Render:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

Frontend Vercel usa `VITE_API_URL=<HTTPS Render API>`.

Variables relevantes:

```text
DATABASE_URL
DATABASE_SCHEMA=administracion
SECRET_KEY
ANALYTICS_HASH_KEY
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS
PUBLIC_URL
EMAIL_MODE
```

Correo de producción: Brevo HTTPS API. Docker local: console por defecto; SMTP requiere override explícito.

## Desarrollo local

```powershell
git switch main
git pull origin main
docker compose up -d --build
docker compose exec -T backend python -m app.demo_monitoring
```

Compose local usa `EMAIL_MODE=console` por defecto. Las pruebas unitarias eliminan sus fixtures y no dejan solicitudes visibles; `demo_monitoring` crea cinco escenarios persistentes SIMPLE/MULTI_QUOTE. Ver [docs/VALIDACION_LOCAL.md](docs/VALIDACION_LOCAL.md).

Validación:

```text
cd backend
alembic heads
# 20260821_0004
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

cd ../frontend
npm ci
npm run build
```

## Arquitectura

```text
frontend/  React + Vite
backend/   FastAPI + SQLAlchemy + Alembic
Neon       PostgreSQL
Render     backend de producción
Vercel     frontend de producción
```

Componentes frontend relevantes:

```text
expense-form.jsx
home-dashboard.jsx
user-tracking.jsx
iam-admin.jsx
auth-route-guard.js
request-governor.js
classification-admin.js
closure-delegation.jsx
```

## Documentación

Empieza por:

1. [.specify/memory/constitution.md](.specify/memory/constitution.md)
2. [docs/CURRENT_PRODUCT_CONTRACT.md](docs/CURRENT_PRODUCT_CONTRACT.md)
3. [PROMPT_RECONSTRUCCION.md](PROMPT_RECONSTRUCCION.md)
4. [docs/README.md](docs/README.md)
5. `specs/`

La documentación normativa debe reflejar el producto vigente y no mantener diseños sustituidos como opciones activas.
