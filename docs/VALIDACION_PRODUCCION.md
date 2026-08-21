# Validación de producción

El workflow manual **Deploy production** solo puede ejecutarse desde `main` con la confirmación `DEPLOY`.

Antes del despliegue ejecuta:

- compilación y suite unitaria completa del backend;
- build y auditoría de dependencias de producción del frontend;
- construcción de las imágenes Docker del backend y frontend.

Después de activar los hooks de Render y Vercel realiza pruebas no destructivas sobre producción: espera la salud del backend, comprueba que IAM rechace acceso anónimo, valida métodos no permitidos, carga el frontend y verifica sus cabeceras de seguridad.

El environment de GitHub `production` debe definir estas variables (no secretos):

```text
PRODUCTION_BACKEND_URL=https://<api-render>
PRODUCTION_FRONTEND_URL=https://<frontend-vercel>
```

También debe conservar los secretos `RENDER_DEPLOY_HOOK` y `VERCEL_DEPLOY_HOOK`.

Las pruebas que crean o modifican solicitudes, Usuarios, Roles, Grupos o Áreas no se ejecutan contra la base productiva. Esos escenarios deben ejecutarse en local o staging con datos aislados.
