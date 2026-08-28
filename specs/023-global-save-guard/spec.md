# Spec 023 — Bloqueo global de guardado y alta segura de Roles

**Estado:** En implementación  
**Constitución:** 2.24.0  
**Fecha:** 2026-08-28

## Objetivo

Impedir acciones concurrentes o duplicadas mientras la interfaz persiste un
registro o cambio, y garantizar que crear un Rol nunca transforme la captura del
siguiente Rol en una edición del registro recién creado.

## Bloqueo global de procesamiento

Antes de enviar una mutación `/api/*` iniciada por la UI mediante `POST`, `PUT`,
`PATCH` o `DELETE`, el frontend presenta una pantalla global no descartable con:

```text
Procesando…
Estamos guardando los cambios. Espera un momento.
```

Contrato:

1. El overlay cubre el viewport completo y queda por encima de topbar, Accesos,
   diálogos, visores y modales.
2. Todos los demás hijos del documento quedan `inert`; mouse, touch, teclado,
   Enter y navegación interna no alcanzan la aplicación.
3. El foco pasa al mensaje y, al liberar el bloqueo, solo se restaura si el
   elemento anterior sigue conectado y habilitado.
4. Un contador mantiene la pantalla hasta que termine la última mutación
   concurrente. Una pausa breve entre llamadas secuenciales evita parpadeo sin
   liberar la interacción.
5. `finally` libera el contador ante éxito, respuesta HTTP de error, aborto o
   fallo de red.
6. `GET`, `HEAD` y `OPTIONS` no muestran la pantalla. El `POST` silencioso de
   `/api/auth/activity` queda excluido y no debe interrumpir el uso normal.
7. La capa no concede autorización, no reintenta y no oculta el error final. Un
   fallo conserva los datos locales del formulario.
8. Desde 320 px respeta `safe-area`, no produce overflow y no ofrece botón para
   cerrar o cancelar mientras el servidor procesa.

`frontend/src/request-governor.js` es el punto transversal porque se carga antes
de los distintos roots React y módulos DOM. Las superficies conservan sus
estados locales de `saving` para evitar reenvíos programáticos, pero no crean
overlays independientes.

## Alta segura de Roles

El editor distingue antes del request:

```text
sin selected y sin recovery → creación por POST
selected o recovery         → edición/reactivación por PATCH
```

Solo después de un `POST` exitoso:

1. `onRoleSaved(saved)` incorpora el Rol a la lista local;
2. `selectedId` y `recovery` quedan en `null`;
3. nombre, descripción, permisos propios, límite y máximo vuelven a sus valores
   iniciales;
4. el título sigue siendo **Crear rol** y el botón queda deshabilitado;
5. escribir el siguiente Rol vuelve a enviar `POST`, nunca `PATCH` al ID creado.

Un error de creación conserva el borrador. Un `PATCH` de edición o reactivación
mantiene seleccionado el Rol correspondiente y nunca cambia su identidad. La
reactivación conserva además el contrato de la Spec 015.

## Fuera de alcance

- Cambiar endpoints, transacciones, IAM o schema de base de datos.
- Bloquear lecturas o el sync silencioso de sesión.
- Reemplazar validación y autorización de FastAPI con estado visual.
