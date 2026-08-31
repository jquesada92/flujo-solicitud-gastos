# Configuración y Accesos

## Permisos

```text
config:read    lectura de Configuración
areas:manage   escritura de Área + Categoría
config:manage  administración técnica/IAM protegida
```

`config:read` puede satisfacer un guard de `config:manage` únicamente para GET/HEAD. POST/PUT/PATCH/DELETE requieren la capacidad de escritura correspondiente.

## Accesos

La consola editable está reservada al Administrador del sistema. El modelo visual es:

```text
Usuarios
Grupos
Roles
Permisos
```

### Usuarios

La lista muestra solamente Usuarios activos, con un máximo de 10 resultados a la vez. Incluye un buscador sin distinción de mayúsculas ni acentos que encuentra por cédula, nombres, apellidos, correo, Rol asignado o Grupo al que pertenece ese Rol. Cada tarjeta enumera debajo del correo todos los Roles asignados; omite esa línea cuando no hay Roles y marca como inactivo cualquier Rol asignado que ya no esté activo. Cuando no hay coincidencias se informa el estado vacío. Los Usuarios inactivos permanecen fuera de la lista y se recuperan mediante el flujo de reactivación por cédula.

La ficha separa dos fuentes de Rol:

```text
Acceso por grupo
Grupo: Operación     Rol: Solicitante
Grupo: Aprobaciones  Rol: Aprobador
Grupo: Configuración Rol: Sin rol adicional (solo acceso base)

Roles globales
[x] Auditor global
[ ] Otro rol global
```

Un Usuario puede seleccionar máximo un Rol de cada Grupo y cero o más Roles globales. Un Rol global no crea membresía de Grupo. Un Rol agrupado recibe sus Permisos propios más los heredables del Grupo mientras Rol y Grupo estén activos; un Grupo inactivo suspende ambas contribuciones.

No se muestran controles de permisos directos a Usuario. La membresía del Grupo no se marca separadamente y una fila `GroupMember` aislada no autoriza.

Todos los cambios quedan staged y solo se persisten al pulsar **Guardar cambios**.

La cuenta técnica muestra su Rol global protegido `Administrador del sistema`, pero no permite editarlo desde esta consola.

#### Restablecer contraseña

La ficha de un Usuario activo que no pertenezca a `system_accounts` muestra
**Regenerar contraseña**, que envía el enlace de restablecimiento. La acción
exige `config:manage`, solicita confirmación y se ejecuta de inmediato; no forma
parte del borrador de Roles ni espera **Guardar cambios**. Mientras se envía, el
control queda deshabilitado para impedir solicitudes duplicadas.

El éxito confirma el correo destinatario sin revelar el token. El email contiene
un enlace de un solo uso con vigencia de 30 minutos por defecto y nunca una
contraseña. Emitir un enlace nuevo invalida los anteriores, pero no cambia la
contraseña ni las sesiones; si falla el correo, la emisión se revierte.

#### Divergencia conocida de la ficha de Usuario

El contrato normativo continúa siendo **máximo un Rol por Grupo y cero o más Roles globales**. La implementación actual de `iam-admin.jsx` presenta temporalmente un único selector general de Rol y reduce el borrador a `role_ids[0]`. Esta limitación es una divergencia de implementación, no una nueva cardinalidad del producto ni una alternativa válida para reconstrucciones futuras.

Hasta corregirla, no se debe tomar el selector único ni las pruebas estáticas que lo fijan como fuente de verdad. Cualquier cambio en la ficha debe preservar todos los `role_ids` ya asignados, ofrecer un selector independiente por Grupo y permitir selección múltiple de Roles globales; guardar una modificación no puede eliminar Roles que el formulario no haya representado.

### Grupos

Un Grupo puede existir con cero Roles y cero Permisos. Sus Permisos heredables se editan junto con el catálogo de Roles y se aplican a cada Rol activo vinculado. Cada Rol puede pertenecer a cero o un Grupo, nunca a más de uno.

Quitar un Rol del Grupo lo convierte en global y conserva las asignaciones de Usuario y `RolePermission`; pierde solo la herencia. Cambiar Permisos del Grupo tampoco modifica los Permisos propios de sus Roles. Vincular Roles globales a un Grupo se rechaza si algún Usuario terminaría con dos Roles de ese mismo Grupo.

La lista de miembros es informativa: se deriva únicamente de Usuarios que tienen un Rol agrupado en ese Grupo.

### Roles

Un Rol administra sus Permisos propios y puede ser:

```text
Global      → sin Grupo
Agrupado    → pertenece a un único Grupo
```

Al editar o reactivar, la UI usa la respuesta actualizada del backend para
mantener nombre/estado sincronizados sin una recarga GET obligatoria. Después de
crear por `POST`, agrega el Rol a la lista y restablece **Crear rol** sin
selección, recuperación, ID, nombre, descripción, permisos, límite o máximo. Una
segunda alta vuelve a usar `POST`; un error conserva el borrador y
edición/reactivación continúan con `PATCH`.

Si el Rol está agrupado, también muestra los Permisos heredados. La semántica es aditiva: `RolePermission ∪ GroupPermission`; la ausencia de un grant propio hereda el del Grupo y no existe `DENY`.

El editor permite dejar el Rol sin límite o fijar un máximo entero positivo de
Usuarios activos. Muestra la ocupación actual y no permite guardar un máximo
menor. Los Usuarios inactivos conservan el Rol sin consumir cupo; asignar o
reactivar se rechaza si el cupo está lleno. La UI marca esas opciones como “sin
cupo”, pero FastAPI vuelve a validar bajo bloqueo transaccional.

### Permisos

Catálogo de capacidades implementadas. Se asignan como grants propios a Roles o heredables a Grupos, nunca directamente a Usuarios.

## Cargo

Cargo/Posición es metadato organizacional y no aparece como fuente de autorización. La cardinalidad vigente es un Cargo máximo por Usuario.

## Reglas de aprobación

Las políticas (`ApprovalPolicy`) se administran por Área concreta o `ALL` y banda
`(min_amount,max_amount]`. Dos reglas activas del mismo scope no pueden
superponerse, cualquiera que sea su modalidad; las bandas adyacentes sí son
válidas. La regla del Área concreta precede a `ALL`.

Para `ANY`, `MAJORITY` y `ALL`, la pantalla selecciona IDs de Roles y/o Grupos
activos compatibles con `requests:approve`. Esos targets acotan la población,
pero no conceden el Permiso. Un Grupo incluye Usuarios asignados a cualquiera de
sus Roles activos; las coincidencias se deduplican y el Solicitante se excluye.
Cargo, `GroupMember`, nombres y `approver_profile_codes` no seleccionan ni
autorizan. Este último queda únicamente como metadata física legacy y ya no es
un control visible.

`NO_APPROVAL` se muestra como **No requiere aprobación**, oculta los targets y
solo puede guardarse con sus listas de Rol/Grupo vacías. La regla habilita
**Registro directo**, no una ronda. Sin política aplicable, `SIMPLE` conserva
`MAJORITY` sobre toda la población IAM y `MULTI_QUOTE` espera a todos; no existe
fallback de registro directo.

## Modo lectura

Un usuario con `config:read` puede consultar la información autorizada de Configuración sin mutarla. El backend sigue siendo la barrera real: cualquier intento de escritura devuelve 403 si no existe autoridad de escritura.

## Sesión

Accesos usa `#access-management` durante la transición del shell. `auth-route-guard.js` evita montar la consola sin sesión y un 401 invalida la sesión local.

La topbar continúa navegando normalmente; salir de Accesos retira el hash antes de continuar.

## Contrato responsive

Accesos debe ser utilizable desde **320 px de ancho CSS en adelante** sin desbordamiento horizontal provocado por sus paneles o controles. En particular:

- la grilla principal de dos columnas se apila cuando el ancho disponible no permite conservar ambas columnas;
- tabs, toolbars, acciones y grupos de botones pueden hacer `wrap` sin superponerse ni salir del viewport;
- el nombre o resumen largo de un Rol se ajusta o trunca dentro de su columna y nunca desplaza fuera de pantalla el estado `Activo`, `Inactivo` o `SISTEMA`;
- las tarjetas de Permisos reducen sus columnas hasta una sola y sus códigos/descripciones pueden partir línea;
- formularios, inputs, textareas y botones respetan el ancho de su contenedor.
- el overlay **Procesando…** cubre el viewport, respeta `safe-area` y queda por
  encima de Accesos sin permitir interacción con sus controles.

La regresión visual mínima se valida a **1180, 1024, 640, 440, 390 y 320 px**. El criterio de aceptación no es conservar siempre dos columnas, sino mantener legibilidad, acciones alcanzables, estados visibles y ausencia de scroll horizontal accidental.

## Política de requests

Accesos no hace PATCH por cada checkbox/select. Los GET repetidos están sujetos
al gobernador global y no existe polling sub-segundo. Cada
`POST`/`PUT`/`PATCH`/`DELETE` muestra el Bloqueo global **Procesando…** y vuelve
`inert` toda la aplicación hasta finalizar la última mutación concurrente. El
sync de `/api/auth/activity` queda excluido.

## API relevante

```text
GET/PATCH/POST /api/iam/users...
POST           /api/users/{user_id}/regenerate-password
POST           /api/auth/reset-password
GET/PATCH/POST /api/iam/groups...
GET/PATCH/POST /api/iam/roles...
GET            /api/iam/permissions
GET            /api/iam/me/permissions
GET            /api/rules/approver-targets
GET/POST/PUT/DELETE /api/rules/policies...
```

`iam_access_policy.py` bloquea rutas legacy que permitirían bypass del modelo.

## Aceptación

- seleccionar un Rol agrupado o global no hace request de mutación;
- Guardar cambios hace una persistencia del acceso del Usuario;
- no hay permisos directos a Usuario;
- Permisos de Grupo y propios de Rol se unen de forma aditiva, sin `DENY`;
- editar/desvincular conserva los Permisos propios del Rol;
- un Grupo puede existir sin Roles;
- un Rol puede existir sin Grupo y entonces es global;
- un Rol pertenece como máximo a un Grupo;
- un Usuario tiene máximo un Rol por Grupo;
- no hay Cargo→Rol;
- miembros de Grupo son derivados solo de Roles agrupados;
- `GroupMember` aislado no concede acceso;
- `config:manage` sigue siendo efectivo solo por la política protegida de `system_accounts`;
- sin sesión se vuelve a Login;
- `config:read` no puede mutar;
- un nombre de Rol actualizado se refleja inmediatamente.
- crear un Rol actualiza la lista y deja el formulario vacío/sin selección;
- dos altas consecutivas usan dos `POST` y no sobrescriben el primer Rol;
- un error conserva el borrador y editar/reactivar conserva `PATCH` e ID;
- el límite vacío significa ilimitado y cero/negativos se rechazan;
- un Rol lleno rechaza asignación y reactivación, mientras inactivar libera cupo sin borrar el Rol;
- el máximo no puede guardarse por debajo de la ocupación activa;
- reglas activas del mismo scope no se solapan y conservan `(min,max]`;
- targets de Rol/Grupo solo acotan Usuarios con `requests:approve` efectivo;
- `NO_APPROVAL` guarda targets vacíos y no abre una Solicitud o ronda;
- solo `config:manage` puede emitir un enlace para un Usuario activo no técnico;
- la emisión confirmada es inmediata y no altera cambios staged de IAM;
- el correo de restablecimiento contiene un enlace de uso único y no una contraseña;
- emitir no rota credenciales/sesiones y el fallo de correo hace rollback;
- consumir aplica Argon2, revoca sesiones, invalida enlaces y vuelve al Login sin auto-login.
