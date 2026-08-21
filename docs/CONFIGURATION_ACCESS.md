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

La ficha separa dos fuentes de Rol:

```text
Acceso por grupo
Grupo: Operación     Rol: Solicitante
Grupo: Aprobaciones  Rol: Aprobador
Grupo: Configuración Rol: Sin rol

Roles globales
[x] Auditor global
[ ] Otro rol global
```

Un Usuario puede seleccionar máximo un Rol de cada Grupo y cero o más Roles globales. Un Rol global no crea membresía de Grupo.

No se muestran controles de permisos individuales. La membresía del Grupo no se marca separadamente.

Todos los cambios quedan staged y solo se persisten al pulsar **Guardar cambios**.

La cuenta técnica muestra su Rol global protegido `Administrador del sistema`, pero no permite editarlo desde esta consola.

### Grupos

Un Grupo puede existir con cero Roles. Cada Rol puede pertenecer a cero o un Grupo, nunca a más de uno.

Quitar un Rol del Grupo lo convierte en global y conserva las asignaciones de Usuario. Vincular Roles globales a un Grupo se rechaza si algún Usuario terminaría con dos Roles de ese mismo Grupo.

La lista de miembros es informativa: se deriva únicamente de Usuarios que tienen un Rol agrupado en ese Grupo.

### Roles

Un Rol administra sus Permisos y puede ser:

```text
Global      → sin Grupo
Agrupado    → pertenece a un único Grupo
```

Al guardar, la UI usa la respuesta actualizada del backend para mantener nombre/estado sincronizados sin una recarga GET obligatoria.

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

- seleccionar un Rol agrupado o global no hace request de mutación;
- Guardar cambios hace una persistencia del acceso del Usuario;
- no hay permisos individuales;
- un Grupo puede existir sin Roles;
- un Rol puede existir sin Grupo y entonces es global;
- un Rol pertenece como máximo a un Grupo;
- un Usuario tiene máximo un Rol por Grupo;
- no hay Cargo→Rol;
- miembros de Grupo son derivados solo de Roles agrupados;
- sin sesión se vuelve a Login;
- `config:read` no puede mutar;
- un nombre de Rol actualizado se refleja inmediatamente.
