# Spec 011 — Consola de Accesos y runtime seguro

**Estado:** Implementada  
**Constitución:** 2.11.0

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

“Acceso por grupo” ofrece un selector de Rol por Grupo. No hay checkboxes independientes de Grupo, permisos individuales ni Roles directos.

### Grupo

Administra Roles disponibles. Miembros son derivados y de solo lectura.

### Rol

Administra Permisos. Al guardar, la respuesta del PATCH actualiza inmediatamente la tarjeta/lista local.

## Persistencia explícita

Cambiar un select/checkbox no envía una mutación. **Guardar cambios** persiste el conjunto staged. Al navegar con cambios pendientes se confirma descarte.

## Sesión

Abrir `#access-management` sin sesión vuelve al Login antes de montar la consola. Un 401 invalida la sesión.

## Requests

Se elimina polling sub-segundo. El gobernador global deduplica GET idénticos en vuelo, reutiliza brevemente respuestas automáticas y permite refresh explícito.

## Navegación

La topbar permanece operativa y al navegar fuera de Accesos se desmonta el overlay/hash.
