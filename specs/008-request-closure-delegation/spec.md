# Spec 008 — Cierre, factura y delegación

**Estado:** Implementada  
**Constitución:** 2.13.0

## Objetivo

Separar la aprobación del cierre administrativo y permitir que el solicitante delegue el registro/corrección de factura para una solicitud concreta.

## Autoridad de cierre

```text
status ∈ {APPROVED, CLOSED}
AND (
  solicitante original
  OR Administrador del sistema
  OR delegado activo de esa solicitud
)
```

La autoridad es por recurso; `requests:close` no participa.

## Delegación

- solo el solicitante original administra la delegación ordinaria;
- el delegado debe ser usuario activo;
- una sola delegación activa por solicitud;
- cambiar delegado revoca la anterior y conserva historial;
- la delegación no concede permisos sobre otras solicitudes.

## Factura

Cerrar requiere factura válida. En `CLOSED`, un actor autorizado puede reemplazar/corregir la factura conservando evidencia de la versión anterior, actor y motivo.
