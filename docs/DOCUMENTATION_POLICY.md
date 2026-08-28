# Política de documentación

## Objetivo

Mantener documentación suficiente para comprender, operar y reconstruir el producto sin depender de conversaciones externas.

`AGENTS.md` gobierna cómo una IA o agente automatizado puede trabajar de forma segura en el repositorio. Es una política operativa: no redefine el producto ni altera la jerarquía funcional que sigue.

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

## Matriz mínima de impacto

| Tipo de cambio | Fuentes que deben revisarse | Evidencia mínima |
| --- | --- | --- |
| IAM, permisos o cardinalidades | Constitución, Spec/checklist/plan, Prompt, README, contrato, `IAM_MODEL.md`, `CONFIGURATION_ACCESS.md`, riesgos | suite backend, contrato documental y PostgreSQL local si cambia persistencia |
| Flujo, aprobadores o atomicidad de solicitudes | Constitución, Spec/checklist/plan, Prompt, README, contrato, arquitectura, guía de usuario, validación local y riesgos | suite backend, casos sin participantes/soporte y prueba del endpoint canónico |
| Seguridad, sesión o contraseña | Constitución, Spec, Prompt, contrato, arquitectura, correo, validación local y riesgos | casos adversos, auditoría sin secretos y flujo local completo |
| Migración o schema | Constitución/cadena Alembic, README, Prompt, Neon, arquitectura y Spec | un solo head, `current=head` en PostgreSQL local y prueba de migración |
| UX o responsive | Spec/checklist, Prompt, contrato, runtime frontend y guía de usuario aplicable | build y navegador en los anchos exigidos |
| Operación, CI o despliegue | `AGENTS.md`, README, runbook local/productivo, ejemplos `*.example` y workflows | comando ejecutado en el entorno autorizado, sin mutar producción |

“Revisar” significa confirmar explícitamente si el documento cambia; no exige
editar archivos que ya estén correctos. Si dos filas aplican, se acumulan sus
fuentes y evidencias. Una IA no puede omitir una fuente porque el código o una
prueba existente contradiga el contrato.

## Checklist documental por PR

1. ¿Cambió una regla constitucional? Actualizar versión de Constitución.
2. ¿Cambió una feature? Actualizar Spec, Plan y Checklist.
3. ¿Cambió el contrato transversal? Actualizar README, Prompt y `CURRENT_PRODUCT_CONTRACT.md`.
4. ¿Cambió operación/despliegue? Actualizar docs técnicos.
5. ¿Cambió terminología? Buscar y corregir todo el repositorio documental.
6. ¿Se sustituyó una idea? Eliminarla de la documentación normativa.
7. Registrar una síntesis en CHANGELOG/HISTORY si aporta trazabilidad.
8. ¿Cambió un comando, script o variable? Probarlo en el entorno local soportado y actualizar sus ejemplos.
9. ¿Apareció una divergencia entre contrato y código? Registrarla en `KNOWN_RISKS.md`; nunca modificar el contrato para hacer pasar una implementación defectuosa.
10. ¿Intervino una IA? Verificar que cumplió `AGENTS.md` y que no leyó, imprimió ni agregó secretos, respaldos o dumps.
11. ¿Se agregó un invariante destinado a evitar regresiones? Añadir o actualizar
    `test_documentation_contract.py` para comprobar la fuente canónica y detectar
    referencias operativas obsoletas.

## Validación automática/manual obligatoria

Ejecutar el contrato documental además de los tests/build aplicables:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest tests.test_documentation_contract -v
```

También revisar texto buscando:

- nombres de ramas ya mergeadas usados como instrucciones;
- heads Alembic obsoletos;
- permisos que ya no resuelve `effective_permission_codes()`;
- rutas o componentes inexistentes;
- cardinalidades diferentes a los modelos/migraciones;
- menciones a formas de acceso rechazadas por `iam_access_policy.py`.
- resultados esperados de `alembic heads/current` que apunten a una revisión
  anterior aunque el documento también mencione el head nuevo en otra sección.

## Fuentes de verdad técnica

Para verificar documentación IAM:

```text
backend/app/services/iam_service.py
backend/app/api/iam.py
backend/app/api/iam_users.py
backend/app/api/iam_group_assignments.py
backend/app/api/iam_access_policy.py
backend/app/core/security.py
backend/app/models/iam.py
backend/alembic/versions/20260824_0009_group_permission_inheritance.py
backend/alembic/versions/20260824_0010_password_reset_links.py
backend/alembic/versions/20260825_0011_role_user_limit.py
backend/alembic/versions/20260827_0012_scoped_approval_policies.py
backend/alembic/versions/20260828_0013_direct_expenses.py
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
frontend/src/iam-responsive.css
frontend/src/mobile-layout.css
frontend/src/action-state.css
frontend/src/home-dashboard.jsx
frontend/src/direct-expense-form.jsx
frontend/src/direct-expense-form.css
frontend/src/user-tracking.jsx
frontend/src/auth-route-guard.js
frontend/src/request-governor.js
```

Para población de aprobadores y creación atómica:

```text
backend/app/services/approval_engine.py
backend/app/services/approval_policy_service.py
backend/app/services/iam_service.py
backend/app/api/request_actions.py
backend/app/api/document_actions.py
backend/app/api/direct_expenses.py
backend/tests/test_request_flow_creation.py
backend/tests/test_direct_expenses.py
specs/021-scoped-approval-rules/
specs/022-direct-expense-registration/
specs/019-iam-approval-flow-atomicity/
```

Para gates y operación segura:

```text
AGENTS.md
backend/scripts/run_tests.py
backend/tests/test_documentation_contract.py
.github/workflows/reusable-ci.yml
.github/workflows/deploy-production.yml
docs/VALIDACION_LOCAL.md
docs/VALIDACION_PRODUCCION.md
```

## Regla de evidencia

Un comando que no se ejecutó no se reporta como exitoso. Un health check confirma disponibilidad, no que el proveedor haya publicado el commit esperado. Las pruebas unitarias con SQLite no sustituyen la validación funcional con PostgreSQL local, y ninguna prueba contra producción puede crear o modificar datos.

Las pruebas estáticas no deben convertir una divergencia conocida en requisito.
En particular, mientras `UsersPanel` conserve solo `role_ids[0]`, el contrato
sigue siendo máximo un Rol por Grupo más varios Roles globales; cualquier cambio
en esa ficha debe preservar todas las asignaciones que la UI aún no representa.
