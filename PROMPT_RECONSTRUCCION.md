# Prompt maestro de reconstrucción

> Constitución vigente: **2.11.0**.

Reconstruye **Flujo de Control de Gastos** como una aplicación web neutral respecto al tipo de organización, lista para desplegar con React/Vite, FastAPI, SQLAlchemy, Alembic y PostgreSQL/Neon.

## Autoridad

Respeta, en orden:

1. `.specify/memory/constitution.md`;
2. `specs/**/spec.md`;
3. checklists de aceptación;
4. `specs/**/plan.md`;
5. este prompt;
6. `README.md`;
7. `docs/`.

No reconstruyas decisiones que contradigan una fuente de mayor prioridad aunque existan estructuras físicas de compatibilidad.

## 1. Modelo organizacional

Usa únicamente conceptos genéricos de organización. Los nombres concretos de Grupos, Roles, Cargos, Áreas o Usuarios son datos configurables en PostgreSQL y nunca condiciones runtime.

Conceptos visibles:

```text
Usuario
Grupo
Rol
Permiso
Cargo / Posición
Área
Categoría
Inicio
Seguimiento
Accesos
```

## 2. IAM

Modelo exacto:

```text
Permiso → Rol → Grupo
             ↑
          Usuario

Usuario activo → requests:read
Cargo          → metadato organizacional
SystemAccount  → política técnica
```

Invariantes:

- un Rol pertenece a un solo Grupo;
- un Usuario puede tener máximo un Rol por Grupo;
- la membresía de Grupo se deriva del Rol asignado;
- no se asignan Permisos directamente a Usuarios;
- no se usan Roles de Usuario sin Grupo;
- Cargo no concede Permisos;
- un Usuario tiene 0..1 Cargo;
- nombres/códigos no autorizan.

Permisos:

```text
requests:read
requests:create
requests:approve
areas:manage
config:read
config:manage
```

`requests:read` es baseline para usuarios activos. `config:manage` es system-only. `requests:close` puede persistir inactivo por compatibilidad, pero no autoriza runtime.

Para usuario ordinario:

```text
effective_permissions = requests:read + role_permissions_of_active_group_roles - config:manage
```

## 3. Accesos

Construye una única consola administrativa:

```text
Usuarios
  → Acceso por grupo
     → selector único de Rol por Grupo

Grupos
  → Roles del Grupo editables
  → miembros derivados, solo lectura

Roles
  → Permisos

Permisos
  → catálogo de capacidades
```

No agregues controles de permisos individuales ni Roles directos. Cargo no es mecanismo de acceso.

Todas las ediciones de acceso son staged. No hagas requests de mutación al seleccionar una opción. Persiste con **Guardar cambios** y advierte antes de descartar cambios pendientes.

## 4. Configuración

- `config:read`: puede consultar endpoints de Configuración con GET/HEAD.
- `config:manage`: mutaciones de IAM/técnicas; protegido por política de cuenta técnica.
- `areas:manage`: mutaciones de Área + Categoría.

Nunca conviertas `config:read` en autoridad de escritura.

## 5. Cuenta técnica

Identifica al Administrador del sistema con `system_accounts`.

En producción su política efectiva es:

```text
requests:read
areas:manage
config:manage
```

No participa en aprobación/votación. En ambientes no productivos puede recibir los permisos activos necesarios para pruebas.

## 6. Inicio

Inicio es personal. Debe responder rápidamente:

- qué acciones esperan al usuario;
- qué solicitudes propias siguen en proceso;
- métricas de sus propias solicitudes;
- acceso contextual al detalle/acción pendiente.

Acciones actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

## 7. Seguimiento

Crea una pantalla privada, de solo lectura, para seguimiento del equipo:

- Grupos activos;
- miembros de cada Grupo;
- Rol de cada miembro en ese Grupo;
- pendientes por usuario y Grupo;
- KPIs de miembros, usuarios con pendientes y carga total;
- búsqueda por usuario/grupo/rol;
- filtro de usuarios con pendientes.

No permitas editar IAM desde Seguimiento.

## 8. Sesión y rutas privadas

Una ruta privada sin sesión debe redirigir al Login antes de montar su contenido. Un 401 recibido con token almacenado debe limpiar la sesión y retornar al Login.

Protege al menos Accesos y Seguimiento y aplica el mismo patrón a cualquier nueva pantalla privada.

## 9. Eficiencia de red

No implementes polling agresivo por defecto.

Política:

- carga al montar;
- refresh después de mutación/navegación/acción explícita;
- GET idénticos en vuelo se deduplican;
- repeticiones automáticas pueden usar caché corta;
- una mutación invalida caché;
- clicks/teclas explícitos pueden forzar lectura fresca;
- autenticación, adjuntos y URLs tokenizadas quedan fuera de la caché general.

## 10. Solicitudes

El formulario de nueva solicitud solo se muestra con `requests:create`. El backend también exige ese permiso.

Contrato de clasificación:

```text
expense_area
expense_category
```

Área y Categoría son catálogos independientes con relación N:M.

Tipos:

```text
SIMPLE
MULTI_QUOTE
```

Una corrección conserva el tipo original.

## 11. Aprobación y revisión

Una aprobación pendiente admite:

```text
APPROVED
REJECTED
REVISION_REQUESTED
```

`REVISION_REQUESTED` requiere comentario útil y produce:

```text
approval actual       → REVISION_REQUESTED
request                → NEEDS_REVISION
otros PENDING/WAITING → EXPIRED
requester              → CORRECT_REQUEST
```

No concede edición al aprobador.

## 12. Capacidades por solicitud

Calcula y expón:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

No las conviertas en permisos globales.

Cerrar/facturar requiere estado compatible y requester, `system_accounts` o delegado activo de esa solicitud. Solo el solicitante administra la delegación ordinaria.

## 13. Documentos

Acepta PDF/JPEG/PNG/WEBP conforme a los límites configurados. Valida tipo, firma y tamaño; almacena de forma privada; sirve archivos a través del backend autorizado. Reemplazar factura conserva la versión anterior y su evento de auditoría.

## 14. Backend

- `APIRouter` por dominio/capacidad;
- modelos SQLAlchemy separados;
- schemas Pydantic;
- servicios para lógica reusable;
- `get_db()` por request;
- Settings centralizados;
- lifespan sin migraciones;
- Alembic antes del servidor ASGI;
- response models explícitos;
- rate limiting de API autenticada;
- headers `no-store` y headers de seguridad en respuestas API.

## 15. Persistencia Neon

Contrato:

```text
DATABASE_URL=<Neon PostgreSQL URL>
DATABASE_SCHEMA=administracion
```

Base objetivo: `ph_torre_delta`.

Aislamiento:

- ORM con `MetaData(schema=DATABASE_SCHEMA)`;
- Alembic con schema explícito y `version_table_schema`;
- crear schema si falta;
- no usar startup `options=-csearch_path=...` con endpoint pooled;
- SQLite de tests permanece sin schema.

Cadena:

```text
20260820_0001_initial_schema
→ 20260820_0002_group_scoped_roles
→ 20260821_0003_single_user_position
```

`0001` crea la instalación limpia. `0002` agrega las cardinalidades de Roles/Grupos. `0003` garantiza un Cargo por Usuario.

## 16. Correo

Producción: Brevo HTTPS API. Local: SMTP configurable.

Invitación de usuario activo:

```text
correo
contraseña temporal
Cargo, si existe
permisos efectivos
URL pública
```

Cuando cambia el Cargo de un usuario activo, envía actualización con Cargo y permisos efectivos actuales. El cambio de Cargo no modifica esos permisos.

## 17. Frontend relevante

```text
frontend/src/expense-form.jsx
frontend/src/home-dashboard.jsx
frontend/src/user-tracking.jsx
frontend/src/iam-admin.jsx
frontend/src/auth-route-guard.js
frontend/src/request-governor.js
frontend/src/classification-admin.js
frontend/src/closure-delegation.jsx
```

Los bridges o campos de compatibilidad que existan en código no definen el diseño objetivo.

## 18. Definition of Done

Después de implementar cualquier cambio relevante revisa Constitución, Spec, Plan, Checklist, README, prompt maestro, docs, HISTORY y CHANGELOG.

Gates:

```text
cd backend
alembic heads
# 20260821_0003
python -m unittest discover -s tests -v

cd ../frontend
npm ci
npm run build
```

El resultado debe poder comprenderse y reconstruirse leyendo únicamente la documentación vigente, sin contexto externo.
