# Modelo IAM vigente

## Principio

Los Permisos son grants positivos configurables como propios de un Rol o heredables desde un Grupo. Un Rol puede ser global o pertenecer a un único Grupo. Los Usuarios pueden combinar Roles globales con máximo un Rol por cada Grupo.

```text
Permission propia    → Role ── 0..1 Group ← Permission heredable
                          ↑
                         User
```

## Cardinalidades

- `GroupRole.role_id` es único: un Rol puede pertenecer a cero o un Grupo, nunca a varios;
- un Grupo puede existir con cero Roles;
- un Rol sin `GroupRole` es global;
- un Usuario puede tener máximo un Rol por Grupo;
- un Usuario puede tener cero o más Roles globales ordinarios;
- un Rol puede tener `max_users` nullable; un valor configurado es entero positivo;
- el cupo cuenta Usuarios activos asignados y los inactivos conservan la asignación sin consumirlo;
- un Grupo puede tener cero o más Permisos heredables;
- un Rol agrupado suma sus Permisos propios y los del Grupo, sin `DENY`;
- `GroupMember` se deriva/reconstruye solo desde `UserRoleAssignment + GroupRole`;
- una fila `GroupMember` por sí sola no concede ningún Permiso;
- un Rol global no crea `GroupMember`;
- Cargo/Posición no es fuente IAM;
- un Usuario tiene máximo un Cargo.

## Persistencia

Tablas operativas de autorización:

```text
permissions
roles
role_permissions
user_groups
group_permissions     # grants heredables para Roles del Grupo
group_roles          # opcional por Rol
user_role_assignments
group_members        # proyección de Roles agrupados
system_accounts
user_activity_periods
role_activity_periods
group_activity_periods
```

`area_activity_periods` aplica la misma regla temporal al catálogo de Áreas.
Cada tabla de períodos tiene llave primaria propia, llave foránea a su entidad,
`active_from`, `active_until` y una instantánea `values` JSON. Solo puede existir
una fila abierta por entidad. `values.active=false` identifica los intervalos de
inactividad; el Usuario conserva su cédula y Roles, y el Rol su Grupo asociado y `max_users`.
Los metadatos `event_at`, `actor_*`, `change_type`, `changed_fields` y `changes`
permiten reconstruir quién cambió qué y cuándo, además de la vigencia temporal.

Tablas organizacionales/compatibilidad que no conceden permisos:

```text
positions
user_positions
position_roles      # estructura física compatible; nuevas asignaciones están bloqueadas
user_permissions    # estructura física compatible; nuevas asignaciones están bloqueadas
```

La existencia física de una tabla no significa que participe en `effective_permission_codes()`.

## Resolución

Para usuario ordinario activo:

```text
baseline = {requests:read}

global_role_permissions = permisos propios de Roles asignados
                          que no tienen GroupRole

grouped_own_permissions = permisos propios de Roles asignados
                          cuyo GroupRole apunta a un Grupo activo

inherited_group_permissions = permisos del Grupo activo alcanzado mediante
                              UserRoleAssignment + GroupRole activo

effective = baseline
          ∪ global_role_permissions
          ∪ grouped_own_permissions
          ∪ inherited_group_permissions
          - {config:manage}
```

Para cada Rol agrupado se calcula `RolePermission ∪ GroupPermission`. Es una unión aditiva: no duplica códigos, un Permiso propio adicional se conserva y la ausencia de un Permiso propio hereda el del Grupo. No existe estado `DENY`. `GroupMember` no aparece en la consulta de autorización.

Para `system_accounts`, se aplica la política técnica del ambiente. En producción:

```text
requests:read
areas:manage
config:manage
```

En producción esa cuenta no recibe `requests:create` ni `requests:approve` y no participa en aprobación/votación. En desarrollo y pruebas puede recibir todos los Permisos activos para ejercitar flujos end-to-end; esa política ampliada es exclusiva del ambiente no productivo y no constituye el contrato de acceso real.

El Rol `system-administrator` es global y `system_managed`. El bootstrap lo asigna a la cuenta técnica para representar su responsabilidad, pero `SystemAccount` continúa siendo la autoridad protegida para sus privilegios.

## `config:read`

Es un permiso ordinario de lectura. `require_permission('config:manage')` acepta `config:read` solo para métodos `GET`/`HEAD`; una mutación continúa exigiendo `config:manage`.

## `areas:manage`

Permite mutar Área/Categoría. Puede estar en un Rol global o en un Rol de negocio ligado a un Grupo. No concede gestión IAM.

## Prohibiciones de acceso

`iam_access_policy.py` rechaza:

- permisos directos a Usuario;
- Cargo→Rol;
- membresía de Grupo independiente;
- mutaciones legacy de Roles de Usuario fuera del payload canónico de Accesos.

`iam_users.py` valida que:

- un Rol agrupado pertenezca a un Grupo activo para ser asignado;
- no se repita el mismo Grupo entre los Roles agrupados de un Usuario;
- un Rol global ordinario pueda asignarse sin crear membresía de Grupo;
- Roles técnicos `system_managed` no puedan asignarse desde la consola ordinaria.
- un Rol con límite no exceda su cantidad de Usuarios activos al asignar o reactivar;
- `max_users` no se reduzca por debajo de la ocupación activa vigente.

La asignación bloquea las filas de Roles objetivo en orden estable antes de contar
ocupación. Esto serializa dos asignaciones concurrentes en PostgreSQL. La
desactivación libera cupo sin borrar `UserRoleAssignment`; reactivar vuelve a
validarlo.

## Cambio de scope de un Rol

Un Rol puede moverse entre:

```text
Global ↔ Grupo
```

sin borrar `UserRoleAssignment` ni `RolePermission` existentes. Al quedar global desaparece solo la herencia; al vincularse a un Grupo suma la nueva herencia a sus Permisos propios.

Al agregar Roles a un Grupo, el backend comprueba que ningún Usuario terminaría con dos de esos Roles dentro del mismo Grupo. Después reconstruye `GroupMember` para reflejar las asignaciones vigentes. Quitar todos los Roles de un Grupo es válido y puede dejar el Grupo vacío. Editar los Permisos del Grupo reemplaza solo sus `GroupPermission` y nunca modifica los Permisos propios de sus Roles.

## Accesos UI

Usuarios:

```text
Acceso por grupo
Grupo A → [Rol A1 | Rol A2 | Sin rol adicional]
Grupo B → [Rol B1 | Rol B2 | Sin rol adicional]

Roles globales
[x] Rol Global 1
[x] Rol Global 2
```

“Sin rol adicional” elimina la membresía derivada de ese Grupo, pero no elimina el baseline `requests:read` que conserva todo Usuario activo.

Cambiar selectores o checks es local. **Guardar cambios** envía la lista completa de `role_ids` en una única actualización; el backend deriva `group_ids` solo desde los Roles agrupados.

Grupos:

- pueden tener cero Roles;
- tienen cero o más Permisos heredables editables;
- se administran los Roles opcionalmente vinculados al Grupo;
- miembros son solo lectura y reflejan asignaciones de Roles agrupados;
- quitar un Rol del Grupo lo convierte en global.

Roles:

- contienen Permisos propios;
- muestran por separado los Permisos heredados del Grupo; un heredado sigue efectivo aunque el checkbox propio esté desmarcado;
- pueden ser globales o pertenecer a máximo un Grupo;
- pueden quedar sin límite o definir el máximo de Usuarios activos asignados;
- muestran ocupación actual y deshabilitan como “sin cupo” una opción llena para otro Usuario;
- guardar usa la respuesta del backend para actualizar el estado local y evitar GET innecesario.

## Fuentes explicables

`permission_sources()` produce fuentes como:

```text
Acceso base del producto para usuarios activos
Grupo <nombre> → Rol <nombre>
Grupo <nombre> (heredado por Rol <nombre>)
Rol global <nombre>
Política de cuenta técnica (...)
```

No produce fuentes de Cargo, `GroupMember` ni permisos directos a Usuario.

## Cargo y notificaciones

Cargo es 0..1 por Usuario y no afecta autorización. La invitación y el correo de actualización pueden mostrar Cargo y los permisos efectivos actuales; ambos valores se obtienen de fuentes distintas:

```text
Cargo    → UserPosition → Position
Permisos → effective_permission_codes()
```

## Capacidades por recurso

No forman parte del IAM global:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

Se calculan por solicitud y el backend las revalida en cada mutación.
