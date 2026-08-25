# Validación de producción

El workflow manual **Deploy production** solo puede ejecutarse desde `main` con la confirmación `DEPLOY`.

Esa confirmación técnica no sustituye la autorización humana. Una IA no debe activar hooks, ejecutar el workflow, migrar, restaurar ni cambiar variables de producción salvo que el usuario autorice expresamente el despliegue del commit exacto. Las comprobaciones posteriores son anónimas, de solo lectura y no deben crear sesiones, enviar correos ni modificar datos.

Antes del despliegue ejecuta:

- compilación y suite unitaria completa del backend;
- build y auditoría de dependencias de producción del frontend;
- construcción de las imágenes Docker del backend y frontend.

Sin imprimir valores, confirma en Render:

- `ENVIRONMENT=production` y `DATABASE_SCHEMA=administracion`;
- `DATABASE_URL` directa mientras `start.sh` comparta conexión entre Alembic y runtime;
- `SECRET_KEY`, `ANALYTICS_HASH_KEY`, `ADMIN_EMAIL` y `ADMIN_PASSWORD` propios del ambiente;
- `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30` o una vigencia explícitamente aprobada;
- `PUBLIC_URL` y todos los orígenes CORS en HTTPS;
- `EMAIL_MODE=brevo`, `BREVO_API_KEY` y `EMAIL_FROM` verificado.

En Vercel confirma antes del build `VITE_API_URL=<HTTPS Render API>`. Al ser build-time, cambiarla después requiere un nuevo deployment.

Después de activar los hooks de Render y Vercel realiza pruebas no destructivas sobre producción: espera la salud del backend, comprueba que IAM rechace acceso anónimo, valida métodos no permitidos, carga el frontend y verifica sus cabeceras de seguridad.

La verificación actual no demuestra por sí sola que el commit solicitado quedó desplegado. Los endpoints y cabeceras pueden responder desde la versión anterior mientras Render o Vercel todavía están construyendo. El workflow no compara un SHA ni un identificador de release publicado por la aplicación. Antes de declarar éxito se debe comprobar en ambos proveedores que el deployment terminó correctamente y corresponde al SHA de `main` que fue autorizado. Hasta que exista una verificación automática de identidad de release, este paso es manual y obligatorio.

El environment de GitHub `production` debe definir estas variables (no secretos):

```text
PRODUCTION_BACKEND_URL=https://<api-render>
PRODUCTION_FRONTEND_URL=https://<frontend-vercel>
```

También debe conservar los secretos `RENDER_DEPLOY_HOOK` y `VERCEL_DEPLOY_HOOK`.

Las pruebas que crean o modifican solicitudes, Usuarios, Roles, Grupos o Áreas no se ejecutan contra la base productiva. Esos escenarios deben ejecutarse en local o staging con datos aislados.

Tampoco se ejecutan en producción `app.demo_monitoring`, `app.live_demo`, la suite unitaria, pruebas de correo ni verificaciones autenticadas de escritura. No se usa una cuenta real para ampliar el smoke test.

## Migraciones y recuperación

El contenedor del backend ejecuta Alembic antes de iniciar Uvicorn. Por ello, un rollback de la imagen no revierte automáticamente el schema y podría dejar código antiguo sobre una base ya migrada. Antes de autorizar un despliegue con migraciones:

1. ensaya `upgrade head` y los flujos afectados sobre PostgreSQL aislado o una rama de Neon;
2. confirma la ventana y el mecanismo de restauración disponibles;
3. comprueba que la migración sea compatible con el despliegue progresivo;
4. registra el SHA, head Alembic y responsables de la decisión.

No ejecutes `alembic downgrade`, restauraciones de Neon ni borrado de volúmenes como respuesta automática a un fallo. Una recuperación productiva necesita autorización específica y debe coordinar base de datos, adjuntos persistentes y versión de la aplicación.

## Criterio de cierre

Un despliegue solo se declara validado cuando:

- CI terminó con pruebas, build, auditoría y construcción de imágenes;
- Render y Vercel muestran estado exitoso para el SHA autorizado;
- salud, límites anónimos y cabeceras responden como espera el workflow;
- no aparecen errores de migración, traceback ni fallos de entrega en logs;
- no se ejecutó ninguna prueba mutante sobre datos reales.
