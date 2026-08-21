# Spec 007 — Enviar a revisión y propiedad de corrección

**Estado:** Implementada  
**Constitución:** 2.13.0

## Objetivo

Separar claramente la decisión del aprobador de la autoridad para editar una solicitud.

## Enviar a revisión

Disponible en una aprobación pendiente para un actor autorizado por `requests:approve`. Requiere comentario útil de al menos 3 caracteres.

Resultado atómico:

```text
approval actual       → REVISION_REQUESTED
solicitud             → NEEDS_REVISION
otras PENDING/WAITING → EXPIRED
solicitante           → CORRECT_REQUEST
```

El aprobador no recibe `can_correct` por realizar esta acción.

## Corrección

Solo el solicitante original o el Administrador del sistema protegido pueden corregir cuando el estado lo permite. El frontend puede mostrar `can_correct`, pero el backend revalida siempre.

## Trazabilidad

El comentario de revisión, decisión, actor y cambios de estado deben permanecer consultables en el historial/auditoría del proceso.
