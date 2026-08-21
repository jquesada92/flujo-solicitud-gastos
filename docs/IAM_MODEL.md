# Modelo IAM vigente

## Principio

Los permisos se asignan a Roles; los Roles se acotan a Grupos; los Usuarios reciben un Rol concreto dentro de cada Grupo donde participan.

```text
Permission → Role → Group
               ↑
            User
```

## Cardinalidades

- `GroupRole.role_id` es único: un Rol pertenece a un Grupo.
- un Usuario puede tener varios Roles solo si pertenecen a Grupos diferentes;
- máximo un Rol del Usuario por Grupo;
- `GroupMember` se deriva/reconstruye desde `UserRoleAssignment + GroupRole`;
- Cargo/Posición no es fuente IAM;
- un Usuario tiene máximo un Cargo.

## Persistencia

Tablas operativas de autorización:

```text
permissions
roles
role_permissions
user_groups
group_roles
user_role_assignments
group_members
system_accounts
```

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
role_permissions = permisos de Roles asignados
                   cuyo GroupRole apunta a un Grupo activo

effective = baseline ∪ role_permissions - {config:manage}
```

Para `system_accounts`, se aplica la política técnica del ambiente. En producción:

```text
requests:read
areas:manage
config:manage
```

## `config:read`

Es un permiso ordinario de lectura. `require_permission('config:manage')` acepta `config:read` solo para métodos `GET`/`HEAD`; una mutación continúa exigiendo `config:manage`.

## `areas:manage`

Permite mutar Área/Categoría. Puede estar en un Rol de negocio ligado a un Grupo. No concede gestión IAM.

## Prohibiciones de acceso

`iam_access_policy.py` rechaza:

- permisos directos a Usuario;
- Cargo→Rol;
- membresía de Grupo independiente;
- Rol de Usuario sin el contexto del formulario por Grupo.

`iam_users.py` vuelve a validar que los Roles seleccionados pertenezcan a Grupos activos y que no se repita Grupo.

## Accesos UI

Usuarios:

```text
Grupo A → [Rol A1 | Rol A2 | Sin rol]
Grupo B → [Rol B1 | Rol B2 | Sin rol]
```

Cambiar el selector es local. **Guardar cambios** envía la lista de `role_ids` en una única actualización; el backend deriva `group_ids`.

Grupos:

- se administran los Roles permitidos del Grupo;
- miembros son solo lectura y reflejan asignaciones de Usuario.

Roles:

- contienen Permisos;
- guardar usa la respuesta del backend para actualizar el estado local y evitar GET innecesario.

## Fuentes explicables

`permission_sources()` produce fuentes como:

```text
Acceso base del producto para usuarios activos
Grupo <nombre> → Rol <nombre>
Política de cuenta técnica (...)
```

No produce fuentes de Cargo ni de asignación directa.

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
