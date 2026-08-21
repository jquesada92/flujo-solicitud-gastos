# Spec 009 — Configuración técnica, lectura y gestión de Áreas

**Estado:** Implementada  
**Constitución:** 2.12.0

## Objetivo

Separar tres capacidades diferentes:

```text
config:read    consultar Configuración
areas:manage   administrar Área + Categoría
config:manage  administrar IAM/configuración técnica
```

## Reglas

### config:read

Puede llegar por un Rol global ordinario o por un Rol dentro de un Grupo. Permite GET/HEAD de recursos de Configuración compatibles con lectura. No permite mutaciones.

### areas:manage

Puede llegar por un Rol global ordinario o por un Rol dentro de un Grupo y gobierna mutaciones del catálogo Área/Categoría. No concede IAM.

### config:manage

Es system-only. Una asignación de Rol ordinaria —global o agrupada— no lo vuelve efectivo para un usuario que no sea `system_accounts`.

El Rol global técnico `system-administrator` es `system_managed`; su existencia/asignación representa la responsabilidad técnica, pero la autoridad de `config:manage` continúa siendo la política de `SystemAccount`.

## Navegación

La UI puede mostrar secciones según permisos efectivos. El backend sigue siendo autoridad final aunque un bridge legacy use `can_configure` para visibilidad.
