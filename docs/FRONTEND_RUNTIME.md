# Runtime del frontend: sesión, navegación y requests

## Objetivo

Evitar vistas privadas parciales, loops de red y mutaciones implícitas.

## Fuente y construcción

La fuente vigente está en `frontend/src/`; `frontend/dist/` es generado, está ignorado y nunca se edita ni confirma. El build usa un plugin de compatibilidad en `frontend/vite.config.js` que transforma anclas concretas de `src/main.jsx` y `src/iam-admin.jsx` para completar la extracción modular y aplicar guards de acceso. Por eso leer solamente el JSX sin revisar esa transformación no describe necesariamente el bundle final.

Después de cambiar sesión, navegación, permisos, acciones o esos archivos fuente se ejecuta:

```powershell
cd frontend
npm ci
npm run build
```

`npm run build` es una validación obligatoria: falla si una ancla esperada por la transformación cambió. No se corrige ese fallo debilitando o eliminando el plugin para lograr un build verde; se actualiza conscientemente la extracción, sus pruebas y la documentación, o se completa la modularización que haga innecesaria la transformación. `npm ci` respeta el lockfile; una validación no actualiza dependencias.

`VITE_API_URL` y `VITE_TIME_ZONE` se incorporan en tiempo de build y son públicos. Docker local deja `VITE_API_URL` vacío para usar el proxy Nginx same-origin `/api`; Vercel necesita la URL HTTPS de Render antes de construir y requiere un nuevo deployment si cambia. Nunca se colocan secretos en variables `VITE_*`.

El build valida compilación y contratos estáticos, no la interacción real. Cambios de responsive, foco, modales o navegación requieren además revisión de navegador en los anchos soportados.

## Layout móvil

`frontend/src/mobile-layout.css` es la capa responsive transversal y se importa
después de `styles.css`. Desde 320 px, la página no genera overflow horizontal:
la navegación es una banda táctil desplazable, la consulta de Solicitudes se
convierte en tarjetas etiquetadas y menús, modales y visores se mantienen dentro
del viewport con altura dinámica y `safe-area`. Los estilos particulares siguen
en `iam-responsive.css`, `home-dashboard.css` y `user-tracking.css`.

No se elimina información para ajustar una pantalla. Si una tabla secundaria
conserva desplazamiento interno, el documento completo no debe desplazarse y la
primera columna debe permanecer utilizable. La prueba de navegador cubre 1180,
1024, 640, 440, 390 y 320 px y verifica overflow, controles recortados, cierre de
diálogos y foco visible.

## Guard de sesión

`auth-route-guard.js` protege las superficies privadas basadas en hash. Regla:

```text
sin access_token + hash privado
→ limpiar hash
→ renderizar Login
```

Si una llamada autenticada devuelve 401 con token almacenado:

```text
limpiar sesión local
limpiar ruta privada
volver a Login
```

El login fallido no debe crear un loop de redirección.

## Ruta pública de restablecimiento

`/reset-password#token=...` se reconoce antes de montar Login o cualquier ruta
privada. El token se mantiene fuera de almacenamiento persistente y se envía solo
a `POST /api/auth/reset-password`; no se interpreta como token de sesión ni pasa
por la caché general. Al completar, la UI confirma el cambio, retira el token de
la URL y vuelve al Login sin guardar `access_token` ni iniciar sesión.

La ficha de Accesos llama a
`POST /api/users/{user_id}/regenerate-password` solo después de confirmación. La
acción deshabilita el control mientras está pendiente, presenta éxito/error sin
mostrar el token y no modifica ni guarda el borrador IAM.

## Gobernador de requests

`request-governor.js` protege GET del API frente a duplicación accidental:

- una llamada idéntica en vuelo se comparte;
- repeticiones automáticas recientes pueden reutilizar JSON;
- mutaciones invalidan la caché;
- una interacción humana reciente puede forzar lectura fresca;
- auth, adjuntos y enlaces tokenizados —incluido restablecimiento— quedan excluidos cuando la reutilización sería incorrecta.

La ventana de caché es una optimización de frontend, no una garantía de consistencia del backend.

## Política de polling

No usar `setInterval`/`setTimeout` como mecanismo de sincronización por defecto. Si una feature necesita polling:

1. justificarlo en su Spec;
2. usar frecuencia razonable;
3. detenerlo al desmontar;
4. deduplicar requests;
5. no mutar datos como efecto del polling.

## Formularios de administración

Las selecciones son estado local. Un click/select no debe emitir PATCH/PUT/POST. El usuario confirma con Guardar cambios.

El enlace de restablecimiento no es una edición de acceso: es una acción de
seguridad inmediata con confirmación propia y no espera Guardar cambios.

El límite de Usuarios de un Rol sí es una edición staged: checkbox, valor y
validación local permanecen en el formulario hasta **Guardar cambios**. La lista
muestra ocupación/máximo y el selector identifica Roles llenos, sin sustituir la
validación autoritativa del backend.

## Recargar

Un botón explícito de Recargar debe poder consultar al servidor aunque exista una respuesta automática reciente.
