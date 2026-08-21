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

La ficha muestra **Acceso por grupo**. Cada Grupo activo tiene un selector de sus Roles. Un Usuario puede seleccionar máximo un Rol de ese Grupo.

```text
Grupo: Operación     Rol: Solicitante
Grupo: Aprobaciones  Rol: Aprobador
Grupo: Configuración Rol: Sin rol
```

No se muestran controles de permisos individuales. La membresía del Grupo no se marca separadamente.

Todos los cambios quedan staged y solo se persisten al pulsar **Guardar cambios**.

### Grupos

Un Grupo administra qué Roles le pertenecen. Un Rol solo puede pertenecer a un Grupo.

La lista de miembros es informativa: se deriva de Usuarios que tienen un Rol de ese Grupo.

### Roles

Un Rol administra sus Permisos. Al guardar, la UI usa la respuesta actualizada del backend para mantener nombre/estado sincronizados sin una recarga GET obligatoria.

### Permisos

Catálogo de capacidades implementadas. Se asignan a Roles, no a Usuarios.

## Cargo

Cargo/Posición es metadato organizacional y no aparece como fuente de autorización. La cardinalidad vigente es un Cargo máximo por Usuario.

## Modo lectura

Un usuario con `config:read` puede consultar la información autorizada de Configuración sin mutarla. El backend sigue siendo la barrera real: cualquier intento de escritura devuelve 403 si no existe autoridad de escritura.

## Sesión

Accesos usa `#access-management` durante la transición del shell. `auth-route-guard.js` evita montar la consola sin sesión y un 401 invalida la sesión local.

La topbar continúa navegando normalmente; salir de Accesos retira el hash antes de continuar.

## Política de requests

Accesos no hace PATCH por cada checkbox/select. Los GET repetidos están sujetos al gobernador global y no existe polling sub-segundo.

## API relevante

```text
GET/PATCH/POST /api/iam/users...
GET/PATCH/POST /api/iam/groups...
GET/PATCH/POST /api/iam/roles...
GET            /api/iam/permissions
GET            /api/iam/me/permissions
```

`iam_access_policy.py` bloquea rutas legacy que permitirían bypass del modelo.

## Aceptación

- seleccionar un Rol no hace request de mutación;
- Guardar cambios hace una persistencia del acceso del Usuario;
- no hay permisos individuales;
- no hay Roles sin Grupo;
- no hay Cargo→Rol;
- miembros de Grupo son derivados;
- sin sesión se vuelve a Login;
- `config:read` no puede mutar;
- un nombre de Rol actualizado se refleja inmediatamente.
