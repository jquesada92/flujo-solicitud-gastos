# Modelo IAM vigente

## Principio

Los permisos se asignan a Roles. Un Rol puede ser global o pertenecer a un único Grupo. Los Usuarios pueden combinar Roles globales con máximo un Rol por cada Grupo.

```text
Permission → Role ── 0..1 Group
               ↑
            User
```

## Cardinalidades

- `GroupRole.role_id` es único: un Rol puede pertenecer a cero o un Grupo, nunca a varios;
- un Grupo puede existir con cero Roles;
- un Rol sin `GroupRole` es global;
- un Usuario puede tener máximo un Rol por Grupo;
- un Usuario puede tener cero o más Roles globales ordinarios;
- `GroupMember` se deriva/reconstruye solo desde `UserRoleAssignment + GroupRole`;
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
inactividad; el Usuario conserva su cédula y Roles, y el Rol su Grupo asociado.
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

global_role_permissions = permisos de Roles asignados
                          que no tienen GroupRole

group_role_permissions = permisos de Roles asignados
                         cuyo GroupRole apunta a un Grupo activo

effective = baseline
          ∪ global_role_permissions
          ∪ group_role_permissions
          - {config:manage}
```

Para `system_accounts`, se aplica la política técnica del ambiente. En producción:

```text
requests:read
areas:manage
config:manage
```

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

## Cambio de scope de un Rol

Un Rol puede moverse entre:

```text
Global ↔ Grupo
```

sin borrar `UserRoleAssignment` existentes.

Al agregar Roles a un Grupo, el backend comprueba que ningún Usuario terminaría con dos de esos Roles dentro del mismo Grupo. Después reconstruye `GroupMember` para reflejar las asignaciones vigentes. Quitar todos los Roles de un Grupo es válido y puede dejar el Grupo vacío.

## Accesos UI

Usuarios:

```text
Acceso por grupo
Grupo A → [Rol A1 | Rol A2 | Sin rol]
Grupo B → [Rol B1 | Rol B2 | Sin rol]

Roles globales
[x] Rol Global 1
[x] Rol Global 2
```

Cambiar selectores o checks es local. **Guardar cambios** envía la lista completa de `role_ids` en una única actualización; el backend deriva `group_ids` solo desde los Roles agrupados.

Grupos:

- pueden tener cero Roles;
- se administran los Roles opcionalmente vinculados al Grupo;
- miembros son solo lectura y reflejan asignaciones de Roles agrupados;
- quitar un Rol del Grupo lo convierte en global.

Roles:

- contienen Permisos;
- pueden ser globales o pertenecer a máximo un Grupo;
- guardar usa la respuesta del backend para actualizar el estado local y evitar GET innecesario.

## Fuentes explicables

`permission_sources()` produce fuentes como:

```text
Acceso base del producto para usuarios activos
Grupo <nombre> → Rol <nombre>
Rol global <nombre>
Política de cuenta técnica (...)
```

No produce fuentes de Cargo ni de permisos directos.

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
