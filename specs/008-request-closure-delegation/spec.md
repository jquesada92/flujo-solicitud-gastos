# Spec 008 — Cierre, factura y delegación

**Estado:** Implementada  
**Constitución:** 2.21.0

## Objetivo

Separar la aprobación del cierre administrativo y permitir que el solicitante delegue el registro/corrección de factura para una solicitud concreta.

## Autoridad de cierre

```text
estado compatible =
  SIMPLE      + APPROVED
  OR SIMPLE   + CLOSED
  OR MULTI_QUOTE + QUOTATION_VOTING + población completa + ganador único provisional
  OR MULTI_QUOTE + CLOSED

estado compatible
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

Cerrar requiere factura válida. Para `MULTI_QUOTE`, FastAPI recalcula bajo
bloqueo la población y el resultado: votos pendientes o empate responden 409 sin
persistir archivo, y un ganador único lleva directamente de `QUOTATION_VOTING`
a `CLOSED`. En `CLOSED`, un actor autorizado puede reemplazar/corregir la factura
conservando evidencia de la versión anterior, actor y motivo.
