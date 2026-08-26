# Spec 020 — Layout móvil transversal

**Estado:** Implementada pendiente de validación visual completa

**Constitución:** 2.20.0

## Problema

Aunque varias superficies tenían reglas responsive aisladas, la consulta de
Solicitudes conservaba una tabla fija de 1450 px y la navegación, menús y
overlays no compartían un contrato móvil coherente.

## Contrato

1. La aplicación funciona desde 320 px sin overflow horizontal de página,
   controles recortados ni pérdida de foco visible.
2. La navegación principal permanece disponible como una banda táctil
   desplazable e identifica la vista actual.
3. La consulta de Solicitudes representa cada fila como tarjeta etiquetada en
   móvil y conserva datos, soportes, avance y acciones.
4. Formularios, filtros, Inicio, Accesos y Seguimiento apilan contenido sin
   cambiar permisos, estados ni comportamiento de guardado.
5. Menús, diálogos y visores permanecen dentro del viewport, usan altura
   dinámica, respetan `safe-area` y conservan un cierre visible.
6. Los controles táctiles principales miden al menos 44 px.
7. El escritorio conserva la estructura y densidad existentes.

## Fuera de alcance

- Cambiar reglas de IAM, flujo, persistencia o autorización.
- Rediseñar la identidad visual del producto.
- Ocultar datos o acciones para hacer caber el contenido.
