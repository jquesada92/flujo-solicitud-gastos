# Spec 011 — Consola de Accesos y runtime seguro

**Estado:** Implementada con regresión abierta en la ficha de Usuario
**Constitución:** 2.24.0

## Objetivo

Concentrar IAM en una experiencia consistente, explícita y eficiente.

## Pantallas

```text
Usuarios
Grupos
Roles
Permisos
```

### Usuario

Cada tarjeta de la lista muestra el nombre, correo y todos los Roles asignados al Usuario. Los Roles aparecen debajo del correo con etiqueta singular o plural; si no hay ninguno asignado, esa línea se omite. Una asignación a un Rol inactivo sigue siendo visible y se identifica como inactiva.

La ficha separa:

- **Acceso por grupo**: selector de máximo un Rol por Grupo;
- **Roles globales**: selección de cero o más Roles sin Grupo.

No hay checkboxes independientes de membresía de Grupo ni permisos directos a Usuario. Los Roles técnicos `system_managed` no son editables desde la consola ordinaria.

La implementación actual que reduce el borrador a `role_ids[0]` no satisface esta sección: es una divergencia conocida, no una nueva regla. La ficha debe representar y preservar simultáneamente los selectores de cada Grupo y la multiselección global antes de considerarse cerrada.

Para un Usuario activo no técnico, la ficha ofrece **Regenerar contraseña**, que
envía un enlace de restablecimiento. Es una acción de seguridad inmediata,
confirmada y protegida por `config:manage`; no modifica el borrador de Roles, no
espera **Guardar cambios** y no se muestra para `system_accounts`.

### Grupo

Administra Permisos heredables y Roles opcionales. Un Grupo puede existir sin Roles o sin Permisos. Miembros son derivados únicamente de Roles agrupados y son de solo lectura; `GroupMember` aislado no autoriza.

Quitar un Rol del Grupo lo convierte en global y conserva sus Permisos propios; agregar Roles globales a un Grupo debe preservar la regla de máximo un Rol por Grupo para cada Usuario. Editar los Permisos del Grupo no modifica `RolePermission`.

### Rol

Administra Permisos propios. Un Rol puede ser global o pertenecer a máximo un Grupo. Si está agrupado, la UI muestra además los Permisos heredados del Grupo: el efectivo es la unión aditiva, sin `DENY`. Al guardar, la respuesta del PATCH actualiza inmediatamente la tarjeta/lista local.

Puede definir un máximo opcional y positivo de Usuarios activos. La UI muestra
ocupación/máximo, conserva ilimitado como valor predeterminado y marca Roles
llenos en el selector. Usuarios inactivos conservan la asignación sin consumir
cupo; FastAPI valida asignación, reactivación y reducción del máximo.

Después de crear un Rol mediante `POST`, la lista incorpora la respuesta y el
editor regresa a **Crear rol** completamente vacío, sin conservar selección,
recuperación ni ID. Una segunda alta vuelve a usar `POST` y nunca sobrescribe el
Rol anterior. Edición y reactivación continúan usando `PATCH`; un error conserva
el borrador. El bloqueo transversal durante el request se rige por la Spec 023.

## Persistencia explícita

Cambiar un select/checkbox no envía una mutación. **Guardar cambios** persiste el conjunto staged. Al navegar con cambios pendientes se confirma descarte.

La emisión confirmada del enlace de restablecimiento es una excepción explícita
porque no edita IAM: se ejecuta inmediatamente, evita doble envío mientras está
pendiente y muestra éxito o error sin revelar el token.

## Sesión

Abrir `#access-management` sin sesión vuelve al Login antes de montar la consola. Un 401 invalida la sesión.

`POST /api/auth/login` y `GET /api/auth/me` exponen `role_names` con los nombres
ordenados de todos los Roles IAM activos asignados al Usuario. La cabecera muestra
esos Roles, no traduce el perfil técnico legacy `user.role` a frases de capacidad.
Si hay varios los presenta juntos; una cuenta técnica sin asignación visible usa
**Administrador del sistema** y un Usuario ordinario sin Rol usa **Sin rol
asignado**.

## Requests

Se elimina polling sub-segundo. El gobernador global deduplica GET idénticos en vuelo, reutiliza brevemente respuestas automáticas y permite refresh explícito.

## Navegación

La topbar permanece operativa, identifica los Roles IAM de la sesión y al navegar
fuera de Accesos se desmonta el overlay/hash.

## Responsive

La consola es utilizable desde 320 px sin overflow horizontal de página. Cuando dos columnas no caben, lista y editor se apilan; tabs, toolbars y acciones hacen wrap; nombres, códigos y descripciones largos no ocultan estado ni controles. La matriz visual mínima es 1180, 1024, 640, 440, 390 y 320 px.
