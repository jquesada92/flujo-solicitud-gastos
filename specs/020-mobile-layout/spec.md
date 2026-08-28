# Spec 020 — Layout móvil transversal

**Estado:** Implementada

**Constitución:** 2.24.0

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
4. Formularios, filtros, Inicio, Accesos, Seguimiento y Registro directo apilan
   contenido sin cambiar permisos, estados ni comportamiento de guardado.
5. Menús, diálogos y visores permanecen dentro del viewport, usan altura
   dinámica, respetan `safe-area` y conservan un cierre visible.
6. Los controles táctiles principales miden al menos 44 px.
7. El escritorio conserva la estructura y densidad existentes.
8. El Bloqueo de procesamiento de la Spec 023 cubre el viewport completo desde
   320 px, respeta `safe-area`, no genera overflow y no deja controles de la
   aplicación accesibles por mouse, touch o teclado.

### Registro directo en teléfonos y tabletas

- entre 320 y 720 px, introducción, formulario y bandas usan una sola columna;
- hasta 440 px, nombre/descripción y rango de cada banda también se apilan;
- en tabletas de 768, 820 y 1024 px se permiten dos columnas cuando no recortan
  controles ni texto;
- Área, monto, proveedor, factura, ítem y botón de registro permanecen visibles;
- inputs, selects y botones miden al menos 44 px de alto y conservan foco visible;
- la página nunca usa scroll horizontal para ocultar una parte del formulario.

## Fuera de alcance

- Cambiar reglas de IAM, flujo, persistencia o autorización.
- Rediseñar la identidad visual del producto.
- Ocultar datos o acciones para hacer caber el contenido.
