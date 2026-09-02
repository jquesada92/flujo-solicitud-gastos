# Validación local con Docker

## Alcance

La validación local tiene dos capas aisladas:

- la suite unitaria del backend usa principalmente SQLite temporal o en memoria;
- la validación funcional con Docker usa PostgreSQL 16 y volúmenes locales del proyecto.

Ninguna de las dos debe usar credenciales, base de datos, archivos ni correo de producción. Antes de ejecutar comandos, confirma que estás en la raíz de este repositorio y que no hay variables de producción exportadas en la terminal. No ejecutes `app.demo_monitoring` directamente en el host: el único comando autorizado en este runbook lo ejecuta dentro del backend de Compose, cuya conexión se fuerza al PostgreSQL local.

`docker-compose.yml` fuerza por defecto:

```text
ENVIRONMENT=development
EMAIL_MODE=console
DATABASE_SCHEMA=administracion
```

Para cambiar el transporte local se requiere una decisión explícita mediante `LOCAL_EMAIL_MODE`; no se debe habilitar SMTP durante pruebas funcionales automáticas.

## Levantar el entorno

```powershell
docker compose up -d --build
docker compose ps
```

La configuración usa `backend/.env` solo para ajustes de aplicación. `docker-compose.yml` reemplaza expresamente `DATABASE_URL`, `ENVIRONMENT`, `PUBLIC_URL`, CORS y el modo de correo con valores locales. No cambies `BACKEND_ENV_FILE` a un archivo de producción.

Servicios:

```text
Frontend  http://127.0.0.1:3000
API       http://127.0.0.1:3000/api
Postgres  red interna de Compose
```

## Preview temporal con túnel

El túnel Cloudflare expone la aplicación a Internet y no forma parte de una validación local ordinaria. Úsalo solo cuando el usuario lo solicite expresamente y con datos ficticios.

```powershell
.\scripts\start-preview.ps1
```

En el primer intento se crean `.env.preview` y `backend/.env.preview`. El script se detiene hasta que reemplaces `ADMIN_EMAIL` y `ADMIN_PASSWORD` por credenciales aleatorias propias del preview; no las compartas ni reutilices. El script fuerza `EMAIL_MODE=console` y aplica la URL temporal tanto a `PUBLIC_URL` como a CORS antes de publicar el backend.

Los enlaces y contraseñas temporales generados durante el preview pueden aparecer en logs locales. No publiques esos logs. Al terminar:

```powershell
.\scripts\stop-preview.ps1
```

Este comando conserva volúmenes. La eliminación de datos o volúmenes requiere otra autorización explícita.

## Datos visibles

Las pruebas `unittest` usan bases temporales y eliminan sus fixtures. Sus solicitudes nunca aparecen en la aplicación Docker.

Para crear datos persistentes, idempotentes y marcados como prueba:

```powershell
docker compose exec -T backend python -m app.demo_monitoring
```

Solicitante:

```text
solicitante.prueba@example.com
Demo12345!
```

Votante:

```text
tesorero.prueba@example.com
Demo12345!
```

El sembrador crea catálogo, Roles IAM explícitos, usuarios y cinco solicitudes:

- SIMPLE pendiente;
- SIMPLE aprobada;
- SIMPLE cerrada con factura dummy;
- MULTI_QUOTE con votación abierta;
- MULTI_QUOTE con voto parcial.

Nunca imprime ni envía secretos de producción. Los correos de workflow se muestran únicamente en logs del backend.

## Validación automatizada

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.run_tests
.\.venv\Scripts\python.exe -m unittest tests.test_direct_expenses -v
.\.venv\Scripts\python.exe -m unittest tests.test_documentation_contract -v
.\.venv\Scripts\python.exe -m unittest tests.test_multi_quote_open_voting -v

cd ..\frontend
npm ci
npm run build
npm audit --omit=dev --audit-level=moderate
```

El entorno Python de referencia es 3.12, igual que CI y la imagen del backend. Si `.venv` no existe o usa otra versión, vuelve a crearlo e instala `backend/requirements.txt` antes de considerar el resultado equivalente a CI. `npm ci` es obligatorio para respetar `package-lock.json`; no se sustituye por una actualización de dependencias durante una validación.

`scripts.run_tests` deshabilita la carga de `backend/.env` antes de importar la aplicación y fija SQLite, entorno development y correo console. No lo reemplaces por discovery directo: un `.env` local podría apuntar la suite al schema o servicio equivocado.

## Persistencia PostgreSQL

```powershell
docker compose exec -T backend alembic current
docker compose exec -T backend alembic heads
```

Ambos deben indicar `20260831_0016 (head)` como único head.

La consolidación de Auditoría se valida en PostgreSQL local, no solo en SQLite:

- `audit_change_feed` existe y las ocho tablas retiradas ya no aparecen;
- `approval_step_events` y `quotation_vote_events` continúan presentes;
- cambiar un Rol agrega una fila `USER_ROLES_UPDATED` en la misma transacción;
- un `UPDATE`, `DELETE` o `TRUNCATE` directo del feed es rechazado;
- `GET /api/audit/events` usa una consulta paginada y un cursor
  `occurred_at|event_sequence` estable;
- la revisión `0016` declara su downgrade irreversible; se inspecciona esa
  salvaguarda sin ejecutar un downgrade. Recuperar el layout previo exige
  restaurar un respaldo controlado y desplegar la imagen anterior.

Las tablas, tipos ENUM, contadores e `alembic_version` deben resolverse dentro de `administracion`. Toda consulta SQL cruda debe usar el nombre calificado derivado del modelo; no debe depender de `search_path`.

## Navegador responsive

La matriz global se revisa a 1180, 1024, 640, 440, 390 y 320 px. Para
**Registro directo**, ampliar la validación en Chrome a 320, 360, 390, 412, 440,
600, 640, 768, 820 y 1024 px. En cada ancho comprobar:

- ancho del documento igual al viewport, sin overflow horizontal;
- ningún control o dato recortado y foco visible por teclado;
- inputs, selects y botones de al menos 44 px;
- una columna desde 320 hasta 720 px, incluida la introducción y las bandas;
- descripción y rango de cada banda apilados hasta 440 px;
- dos columnas en 768, 820 y 1024 px solo cuando ambas permanecen legibles;
- desde **Solicitudes**, un Área y un monto cubiertos por `NO_APPROVAL` muestran la
  guía sin ruta interna, conservan el borrador y resaltan el botón **Registro
  directo** dentro de la porción visible de la banda, sin cambiar `aria-current`
  ni navegar automáticamente;
- Área, monto, proveedor, factura, ítem y acción principal siempre visibles.

Para el Bloqueo global **Procesando…**, ejecutar una mutación demorada en 1180,
1024, 640, 440, 390 y 320 px y comprobar que:

- el overlay aparece antes de completar el request y cubre topbar, Accesos y modales;
- los demás hijos de `body` tienen `inert` y no responden a clic, touch, Enter o Tab;
- el mensaje/spinner caben sin overflow y respetan `safe-area`;
- dos mutaciones concurrentes mantienen la pantalla hasta terminar la última;
- éxito, error HTTP y fallo de red la retiran y presentan el resultado;
- `GET` y `POST /api/auth/activity` nunca la muestran.

Para **Configuración → Auditoría**, cambiar un Usuario de un Rol de prueba a
otro dentro del Compose local y comprobar en 1180, 1024, 640, 440, 390 y 320 px:

- al entrar, **Desde/Hasta** cubre hoy y los seis días anteriores en la zona de
  la aplicación, no aparece **Todos**, **Flujos** es la sección inicial y las
  cinco secciones respetan el rango;
- ampliar el rango a una fecha anterior a 45 días recupera su evento, sin
  descargar ni ordenar todo el historial;
- cada página muestra como máximo 10 registros y **Anterior**/**Siguiente** no
  acumulan ni duplican eventos;
- cambiar sección, búsqueda o fechas vuelve a la primera página; **Actualizar**
  conserva los criterios elegidos y también reinicia la página;
- aparece “Roles del usuario actualizados” sin recarga automática continua;
- **Roles asignados** muestra el nombre anterior y el actual;
- creación, actualización y eliminación tienen texto además de color;
- una desactivación se identifica como tal y no como borrado físico;
- desde 720 px cada evento es una tarjeta sin overflow ni datos ocultos;
- correo, teléfono e identificación están enmascarados y no aparecen secretos.

## Pruebas adversas mínimas

- token inválido y acceso anónimo → 401;
- 9 minutos 59 segundos de inactividad → sesión vigente; al alcanzar 10 minutos → `401`, token local eliminado, hash privado limpio y Login visible;
- volver a una pestaña suspendida después de 10 minutos → Login sin reactivar ni sincronizar la sesión;
- payload inválido → 422;
- Auditoría con una sola fecha o con **Desde** posterior a **Hasta** → 422;
- método no soportado → 405;
- cinco logins fallidos y un sexto intento → 429;
- cinco consumos públicos fallidos de restablecimiento en 15 minutos y el siguiente intento → 429;
- token de restablecimiento expirado, reemplazado o reutilizado → rechazo sin cambio de contraseña;
- Rol con cupo lleno → asignación y reactivación rechazadas; Usuario inactivo asignado no consume cupo;
- reducción del máximo de Rol por debajo de su ocupación activa → 409 sin cambio persistido;
- cambiar un Rol asignado → Auditoría devuelve `USER_ROLES_UPDATED` con
  `changes.assigned_roles.before/after` y actor correcto;
- evento de regla eliminada → `change_type=DELETE`, valores anteriores presentes
  y valores actuales vacíos;
- inspección de schema → no existen `user_activity_periods`,
  `area_activity_periods`, `role_activity_periods`, `group_activity_periods`,
  `user_change_events`, `access_profile_change_events`,
  `approval_policy_change_events` ni `invoice_change_events`;
- crear Rol A → lista actualizada + editor vacío/sin selección; crear Rol B a
  continuación → segundo `POST`, nunca `PATCH` sobre A;
- fallo al crear Rol → overlay liberado y borrador intacto; editar/reactivar →
  `PATCH` sobre el ID seleccionado/original;
- `SIMPLE` sin `ApprovalPolicy`, con aprobadores por Rol propio, herencia de Grupo
  o Rol global → ronda `MAJORITY` con esos Usuarios;
- `SIMPLE` sin otro Usuario con `requests:approve` → 422 sin `Expense` persistido;
- reglas del mismo Área/scope con bandas solapadas, incluso de modalidades
  distintas → 422; bandas adyacentes respetan `(min,max]`;
- `MULTI_QUOTE` resuelve por el máximo de opciones y expande/deduplica targets de
  Rol/Grupo sin incluir Usuarios sin `requests:approve`;
- con regla, quórum y líder único habilitan cierre solo al Solicitante y los
  demás invitados pueden votar/cambiar hasta factura + `CLOSED`;
- sin regla, `MULTI_QUOTE` exige todos los votos y líder único; antes de cumplir
  ambos, el cierre responde `409`, y al cumplirlos Solicitante,
  `system_accounts` o delegado activo cierra directamente a `CLOSED`;
- `MULTI_QUOTE` con todos los votos empatados conserva `QUOTATION_VOTING`, no
  tiene selección y rechaza factura con `409`;
- un invitado conserva **Votar o cambiar voto** después del primer voto; cambiarlo
  mantiene un voto activo, agrega evento y recalcula el líder sin pasar a
  `APPROVED`;
- `tracking_amount` usa máximo sin votos, monto del líder único o máximo ante
  empate sin modificar `Expense.amount`;
- votar después del cierre responde `409`;
- `NO_APPROVAL` fuera de banda, sin `requests:create` o con Área inactiva →
  rechazo sin `DirectExpense`, `Expense` ni archivo físico;
- gasto directo válido → fila + factura sin `Expense`, aprobación, invitación,
  voto o acción pendiente; otro Usuario no puede listar/descargarlo;
- fallo al iniciar la primera ronda después de cargar soporte → 422 sin
  `Expense`, `ExpenseAttachment` ni archivo físico huérfano;
- origen CORS no autorizado sin `Access-Control-Allow-Origin`;
- exceso del límite autenticado → 429 con `Retry-After`;
- archivo cuyo contenido no coincide con MIME → 415;
- doble decisión o transición cerrada → 409;
- logs sin 500, traceback o secretos.

## Limitaciones conocidas

La suite frontend actual valida contratos y compilación, pero no reemplaza pruebas de navegador. Los clics, modales, responsive y accesibilidad requieren Playwright o una revisión manual explícita.

La aplicación todavía no aplica un límite global temprano al tamaño de todos los cuerpos HTTP; existen límites específicos de schemas y uploads. Debe añadirse middleware 413 antes de considerar completa la defensa contra cuerpos sobredimensionados.

## Diagnóstico de Docker y BuildKit

Para un fallo de estado o salud, recopila primero evidencia sin modificar datos:

```powershell
docker compose ps
docker compose logs --no-color --tail=200 backend
docker compose logs --no-color --tail=200 frontend
```

Si la construcción falla con `parent snapshot ... does not exist` o `failed to prepare extraction snapshot`, el problema pertenece normalmente al estado local de BuildKit, no al código de la aplicación. La secuencia segura es:

1. reintentar solo la imagen afectada con `docker compose build --no-cache backend` o `frontend`;
2. reiniciar Docker Desktop o el daemon de Docker y repetir la construcción;
3. si persiste, detenerse y pedir autorización antes de limpiar cachés.

Una IA no debe ejecutar como solución automática `docker system prune`, `docker volume prune` ni `docker compose down -v`. Los dos últimos pueden eliminar PostgreSQL y adjuntos locales; limpiar caché de build también requiere confirmación porque afecta otras construcciones del equipo.

`docker compose down` sin `-v` detiene el entorno y conserva sus volúmenes. Antes de cualquier operación de borrado se debe identificar el proyecto Compose y los volúmenes exactos.
