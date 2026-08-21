# Spec 011 — Consola de Accesos y runtime seguro

**Estado:** Implementada  
**Constitución:** 2.12.0

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

La ficha separa:

- **Acceso por grupo**: selector de máximo un Rol por Grupo;
- **Roles globales**: selección de cero o más Roles sin Grupo.

No hay checkboxes independientes de Grupo ni permisos individuales. Los Roles técnicos `system_managed` no son editables desde la consola ordinaria.

### Grupo

Administra Roles opcionales. Un Grupo puede existir sin Roles. Miembros son derivados únicamente de Roles agrupados y son de solo lectura.

Quitar un Rol del Grupo lo convierte en global; agregar Roles globales a un Grupo debe preservar la regla de máximo un Rol por Grupo para cada Usuario.

### Rol

Administra Permisos. Un Rol puede ser global o pertenecer a máximo un Grupo. Al guardar, la respuesta del PATCH actualiza inmediatamente la tarjeta/lista local.

## Persistencia explícita

Cambiar un select/checkbox no envía una mutación. **Guardar cambios** persiste el conjunto staged. Al navegar con cambios pendientes se confirma descarte.

## Sesión

Abrir `#access-management` sin sesión vuelve al Login antes de montar la consola. Un 401 invalida la sesión.

## Requests

Se elimina polling sub-segundo. El gobernador global deduplica GET idénticos en vuelo, reutiliza brevemente respuestas automáticas y permite refresh explícito.

## Navegación

La topbar permanece operativa y al navegar fuera de Accesos se desmonta el overlay/hash.
