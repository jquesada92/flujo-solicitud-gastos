# Spec 009 — Configuración técnica, lectura y gestión de Áreas

**Estado:** Implementada  
**Constitución:** 2.11.0

## Objetivo

Separar tres capacidades diferentes:

```text
config:read    consultar Configuración
areas:manage   administrar Área + Categoría
config:manage  administrar IAM/configuración técnica
```

## Reglas

### config:read

Puede llegar por un Rol dentro de un Grupo. Permite GET/HEAD de recursos de Configuración compatibles con lectura. No permite mutaciones.

### areas:manage

Puede llegar por un Rol dentro de un Grupo y gobierna mutaciones del catálogo Área/Categoría. No concede IAM.

### config:manage

Es system-only. Una relación IAM ordinaria no lo vuelve efectivo para un usuario que no sea `system_accounts`.

## Navegación

La UI puede mostrar secciones según permisos efectivos. El backend sigue siendo autoridad final aunque un bridge legacy use `can_configure` para visibilidad.
