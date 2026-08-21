# Spec 015 — Ocultamiento y recuperación de entidades inactivas

**Estado:** Implementado  
**Constitución:** 2.15.0

## Objetivo

Mantener limpias las listas activas sin permitir que la recreación aparente de
Usuario, Área, Rol o Grupo duplique su identidad o pierda auditoría.

## Reglas

1. Al inactivar una entidad desaparece de la lista GUI después de persistir.
2. Las APIs de listado excluyen inactivos por defecto; `include_inactive=true`
   continúa disponible solo para usos autorizados de inspección.
3. Usuario se recupera por cédula; Área, Rol y Grupo por código o nombre normalizado.
4. `/recovery` solo devuelve candidatos inactivos e incluye el ID original y
   los datos necesarios para completar el formulario.
5. La UI solicita confirmación antes de completar datos de una entidad previa.
6. Guardar usa `PATCH` sobre el ID original con `active=true`; no ejecuta `POST`.
7. La recuperación queda registrada como una nueva versión temporal auditada.
8. Una entidad activa con la misma llave continúa siendo conflicto, no recuperación.

## Rutas

```text
GET /api/iam/users/recovery?identity_document=...
GET /api/users/recovery?identity_document=...
GET /api/iam/roles/recovery?name=...|code=...
GET /api/iam/groups/recovery?name=...|code=...
GET /api/areas/recovery?name=...|code=...
```
