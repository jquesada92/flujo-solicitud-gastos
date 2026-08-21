# Política de documentación

## Objetivo

Mantener documentación suficiente para comprender, operar y reconstruir el producto sin depender de conversaciones externas.

## Jerarquía

1. Constitución.
2. Specs vigentes.
3. Checklists.
4. Plans.
5. Prompt maestro.
6. README.
7. `docs/`.
8. Código de compatibilidad marcado.

## Regla de estado actual

Los documentos normativos describen **cómo funciona el producto ahora**. Cuando una arquitectura es sustituida:

- se actualiza o reemplaza la Spec que la definía;
- no se conserva como alternativa válida;
- HISTORY/CHANGELOG resumen el cambio a nivel de capacidad, sin volver a enseñar el diseño sustituido;
- rutas, ramas, migraciones o comandos ya cerrados no se presentan como instrucciones actuales.

Una estructura física de compatibilidad puede documentarse únicamente si todavía existe en el código y se identifica claramente como deuda, nunca como fuente de autorización o diseño objetivo.

## Cambios que obligan a revisar documentación

- IAM, permisos o cardinalidades;
- navegación o pantallas;
- comportamiento de sesión;
- flujo/estados/capacidades;
- modelos, schemas o migraciones;
- persistencia, hosting o variables de entorno;
- email/notificaciones;
- documentos/seguridad;
- performance o política de red;
- terminología visible.

## Checklist documental por PR

1. ¿Cambió una regla constitucional? Actualizar versión de Constitución.
2. ¿Cambió una feature? Actualizar Spec, Plan y Checklist.
3. ¿Cambió el contrato transversal? Actualizar README, Prompt y `CURRENT_PRODUCT_CONTRACT.md`.
4. ¿Cambió operación/despliegue? Actualizar docs técnicos.
5. ¿Cambió terminología? Buscar y corregir todo el repositorio documental.
6. ¿Se sustituyó una idea? Eliminarla de la documentación normativa.
7. Registrar una síntesis en CHANGELOG/HISTORY si aporta trazabilidad.

## Validación automática/manual recomendada

Además de tests/build, revisar texto buscando:

- nombres de ramas ya mergeadas usados como instrucciones;
- heads Alembic obsoletos;
- permisos que ya no resuelve `effective_permission_codes()`;
- rutas o componentes inexistentes;
- cardinalidades diferentes a los modelos/migraciones;
- menciones a formas de acceso rechazadas por `iam_access_policy.py`.

## Fuentes de verdad técnica

Para verificar documentación IAM:

```text
backend/app/services/iam_service.py
backend/app/api/iam_users.py
backend/app/api/iam_access_policy.py
backend/app/core/security.py
```

Para persistencia:

```text
backend/app/core/database.py
backend/alembic/env.py
backend/alembic/versions/
render.yaml
docker-compose.yml
```

Para UX actual:

```text
frontend/src/iam-admin.jsx
frontend/src/home-dashboard.jsx
frontend/src/user-tracking.jsx
frontend/src/auth-route-guard.js
frontend/src/request-governor.js
```
