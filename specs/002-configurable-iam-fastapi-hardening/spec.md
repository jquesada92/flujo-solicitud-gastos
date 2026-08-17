# Especificación funcional — IAM configurable y hardening FastAPI

**Feature:** 002-configurable-iam-fastapi-hardening  
**Estado:** Implementación en PR #6  
**Fecha:** 2026-08-17

## Objetivo

Eliminar la autorización basada en roles/cargos hardcodeados y convertir la administración de acceso en una capacidad configurable desde la interfaz gráfica, manteniendo el backend FastAPI alineado con prácticas recomendadas de modularidad, configuración, seguridad, testing, ciclo de vida y portabilidad de despliegue.

## Problema

El MVP mezclaba tres conceptos distintos:

- rol técnico (`ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`);
- cargo organizacional (`PRESIDENTE`, `TESORERO`, etc.);
- permiso (`can_request`, `can_approve`, etc.).

Esto impedía reutilizar el producto en organizaciones con estructuras diferentes y otorgaba privilegios implícitos al administrador técnico.

## Historias de usuario

### US-001 — Administrar grupos

Como administrador de configuración quiero crear, renombrar, activar/inactivar grupos y administrar sus miembros para representar la estructura de mi organización sin solicitar cambios de código.

### US-002 — Administrar roles

Como administrador de configuración quiero crear roles y seleccionar sus permisos para reutilizar combinaciones de acceso entre grupos y usuarios.

### US-003 — Heredar permisos por grupo

Como administrador de configuración quiero asignar uno o más roles a un grupo para que sus miembros reciban automáticamente los permisos correspondientes.

### US-004 — Excepciones individuales

Como administrador de configuración quiero asignar roles o permisos adicionales directamente a un usuario para cubrir excepciones que no justifican crear un grupo nuevo.

### US-005 — Administrar cargos

Como administrador de configuración quiero crear y asignar cargos/posiciones como metadatos organizacionales sin que esos cargos otorguen permisos automáticamente.

### US-006 — Ver acceso efectivo

Como administrador de configuración quiero ver los permisos efectivos de un usuario y de dónde provienen para auditar y explicar su acceso.

### US-007 — Cuenta técnica segregada en producción

Como propietario técnico del sistema quiero que mi cuenta técnica en producción pueda administrar configuración y consultar, pero no crear, aprobar ni cerrar solicitudes, para mantener segregación de funciones.

### US-008 — Estructura empresarial variable

Como cliente empresarial quiero crear grupos, roles y cargos con nombres y combinaciones distintas a las del PH sin modificar ni desplegar backend/frontend.

### US-009 — Seguridad inmediata

Como administrador quiero que una asignación o retiro de permisos cambie la autorización efectiva sin reiniciar la aplicación ni volver a generar código.

### US-010 — Backend mantenible

Como equipo de desarrollo quiero configuración centralizada, migraciones versionadas fuera del lifespan, tests HTTP reales y separación de routers/modelos/schemas/servicios para reducir errores al escalar el producto.

### US-011 — Ejecución local portable

Como desarrollador en Windows quiero poder construir y ejecutar los contenedores Linux sin que los finales de línea CRLF rompan los scripts de entrada ni oculten el error real del backend detrás de un fallo de Nginx.

### US-012 — Bootstrap importable

Como desarrollador u operador quiero que el bootstrap técnico se ejecute con una raíz de imports estable para que pueda importar `app` tanto en desarrollo local como dentro de Docker sin depender de cómo Python calcule `sys.path` para un archivo ejecutado por ruta.

### US-013 — Cuenta técnica de pruebas con acceso completo

Como propietario técnico del producto quiero usar la cuenta **Administrador del sistema** para probar cualquier funcionalidad en local, dev, test, staging o preview, sin tener que crear usuarios auxiliares solo para validar crear, aprobar, votar, cargar factura o cerrar solicitudes.

## Permisos atómicos iniciales

| Código | Capacidad |
| --- | --- |
| `requests:read` | Consultar solicitudes y documentos autorizados |
| `requests:create` | Crear/corregir solicitudes y cargar sus soportes |
| `requests:approve` | Participar en votaciones y decisiones de aprobación |
| `requests:close` | Subir/reemplazar factura y cerrar una solicitud aprobada |
| `config:manage` | Administrar configuración organizacional y accesos |

Los permisos atómicos son capacidades implementadas por el producto. La interfaz no inventa códigos arbitrarios; permite combinar las capacidades existentes.

## Resolución de acceso de usuarios operativos

```text
effective_permissions(user) =
    direct_user_permissions
  ∪ direct_role_permissions
  ∪ group_role_permissions
```

La ausencia de permiso significa DENY. Los cargos/posiciones no participan en esta fórmula.

## Política de cuenta técnica por ambiente

Una cuenta marcada en `system_accounts` como `TECHNICAL_ADMIN` utiliza una política ambiental explícita.

### `ENVIRONMENT=production`

Permisos efectivos máximos:

```text
config:manage
requests:read
```

La cuenta técnica:

- no puede crear solicitudes;
- no puede aprobar ni votar;
- no puede subir/reemplazar factura ni cerrar;
- no entra en poblaciones financieras aunque reciba por error un rol/grupo/permiso financiero.

### Cualquier `ENVIRONMENT` distinto de `production`

La cuenta técnica recibe todos los permisos atómicos **activos** del catálogo del producto.

Por tanto puede:

- crear/corregir solicitudes;
- consultar;
- aprobar y votar;
- participar en poblaciones de aprobación/votación;
- subir/reemplazar factura y cerrar;
- administrar configuración.

Esta elevación se determina por `SystemAccount + ENVIRONMENT`, no por email, cargo, rol legacy ni nombre visible.

`RENDER=true` puede activar validaciones estrictas de secretos/CORS, pero no activa por sí solo la política de autorización de producción. Solo `ENVIRONMENT=production` restringe financieramente la cuenta técnica.

## Configuración inicial sugerida del PH

Esta configuración es **dato**, no código:

- Grupo `Administración PH` → rol con `requests:create`, `requests:close`, `requests:read`.
- Grupo `Junta Directiva` → rol con `requests:approve`, `requests:read`.
- Cuenta técnica → identificada como `TECHNICAL_ADMIN`; su política efectiva depende del ambiente.

Ningún nombre anterior es obligatorio para futuras organizaciones.

## Consola gráfica

La pantalla **Configuración → Accesos** debe permitir:

- crear/editar/activar roles;
- seleccionar permisos de un rol;
- crear/editar/activar grupos;
- asignar roles a grupos;
- administrar miembros;
- crear usuarios;
- asignar grupos, roles directos, permisos directos y cargos;
- crear/editar/activar cargos;
- mostrar permisos atómicos disponibles;
- mostrar permisos efectivos del usuario y su origen;
- identificar la cuenta técnica y explicar si su acceso proviene de política de producción o de acceso de prueba no-productivo.

## Contrato de sesión/UI

Las respuestas autenticadas del usuario actual deben exponer `permission_codes` con los permisos efectivos calculados por backend.

Durante la compatibilidad con el frontend legacy también se derivan temporalmente:

- `can_request` desde `requests:create`;
- `can_approve` desde `requests:approve`;
- `can_view` desde `requests:read`;
- `can_configure` desde `config:manage`;
- `can_close` desde `requests:close`.

Estos campos son una vista de compatibilidad; nunca autorizan el backend.

## Requisitos FastAPI

- configuración con `pydantic-settings`;
- `get_db()` como dependencia con `yield`/context manager;
- aplicación compuesta con `APIRouter`;
- modelos SQLAlchemy en `models/`;
- contratos Pydantic reutilizables en `schemas/`;
- lógica reutilizable en `services/`;
- Argon2 para nuevos hashes con upgrade transparente de PBKDF2 legacy;
- migraciones Alembic antes de iniciar ASGI;
- `lifespan` sin DDL/backfills;
- endpoints con I/O SQLAlchemy/filesystem síncrono declarados como `def`;
- response models explícitos cuando el contrato sea sensible;
- tests `TestClient` para matriz de autorización.

## Requisitos de despliegue y portabilidad

- Los scripts `.sh` que se ejecutan dentro de imágenes Linux deben materializarse con finales de línea LF.
- `.gitattributes` debe forzar `*.sh text eol=lf`.
- El backend Docker debe normalizar defensivamente cualquier CRLF antes de ejecutar el entrypoint.
- El bootstrap técnico debe ejecutarse desde la raíz del backend como módulo: `python -m scripts.bootstrap_admin`.
- `scripts` debe ser importable como paquete/módulo y el CI debe comprobar que `scripts.bootstrap_admin` puede importarse dentro de la imagen backend.
- El frontend local debe esperar a que el backend supere `/api/health` antes de iniciar Nginx.
- Si el backend falla en Alembic/bootstrap/Uvicorn, el error debe quedar visible como fallo del backend y no quedar oculto por un error secundario de resolución DNS de Nginx.
- Producción debe declarar explícitamente `ENVIRONMENT=production`; local/dev/test/preview no deben usar ese valor si se pretende probar con acceso técnico completo.

## Compatibilidad temporal

Pueden permanecer temporalmente:

- enum `UserRole`;
- columnas `can_*`;
- `title`;
- router legacy `/api/users`;
- partes del router monolítico de gastos;
- capa frontend `domain-normalization.js`.

Condiciones:

1. no son fuente de autorización;
2. los `can_*` que vea código legacy se derivan del IAM efectivo;
3. las rutas canónicas se registran antes que las rutas legacy equivalentes;
4. la deuda se documenta y retira gradualmente.

## Criterios funcionales clave de la política ambiental

- En `test`, la cuenta técnica devuelve todos los permisos activos en `/api/iam/me/permissions`.
- En `test`, el login devuelve `can_request`, `can_approve`, `can_view`, `can_configure` y `can_close` habilitados para la cuenta técnica mientras esos permisos estén activos.
- En no producción, la cuenta técnica puede aparecer en `users_with_permission('requests:approve')`.
- En producción, aunque se asigne directamente `requests:close`, el permiso efectivo no aparece y el endpoint de cierre devuelve 403.
- En producción, la cuenta técnica no aparece como aprobador/votante financiero.

## Fuera de alcance de este PR

- motor de DENY explícito;
- scopes por organización/Área/recurso;
- SSO/OIDC empresarial;
- SCIM;
- corrección completa de la fórmula funcional de quorum/aprobación;
- rediseño completo del `main.jsx` monolítico;
- motor genérico de workflow para módulos distintos de solicitudes de gasto.

## Deuda funcional explícita

La votación `MULTI_QUOTE` mantiene en este PR la regla legacy de resolución al participar toda la población invitada y existir un ganador único. La semántica de quorum/empates de cotizaciones requiere una especificación funcional independiente.

Asimismo, la regla de mayoría del motor de aprobación existente no se declara corregida por este PR; la constitución vigente sigue siendo la fuente de verdad funcional para la futura refactorización del motor de decisiones.
