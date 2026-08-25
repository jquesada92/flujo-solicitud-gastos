# Guardrails operativos para agentes de IA

## Alcance y autoridad

Este archivo aplica a todo el repositorio. Las instrucciones explícitas del
usuario definen el objetivo; este archivo define cómo trabajar sin ampliar ese
objetivo ni poner en riesgo datos, entornos o trabajo ajeno.

Para decisiones de producto, leer en este orden:

1. `.specify/memory/constitution.md`;
2. la Spec vigente y su checklist/plan;
3. `PROMPT_RECONSTRUCCION.md`;
4. `README.md` y `docs/CURRENT_PRODUCT_CONTRACT.md`;
5. el resto de `docs/`.

Si dos fuentes vigentes se contradicen, detener la implementación afectada,
mostrar la contradicción con rutas concretas y pedir dirección. El código
legacy o de compatibilidad no sustituye una fuente normativa.

`AGENTS.md` gobierna la operación segura, no el comportamiento del producto.
Nunca modificar Constitución, Specs o contrato para justificar una limitación
del código actual. Si la implementación diverge, conservar la regla normativa,
registrar la divergencia en `docs/KNOWN_RISKS.md` y corregir código/pruebas en
una tarea con alcance explícito.

## Antes de cambiar archivos

- Ejecutar `git status --short --branch` y revisar el diff relevante.
- Preservar cambios existentes que no pertenezcan a la tarea. No asumir que un
  árbol sucio fue creado por el agente actual.
- No cambiar de rama, hacer pull, stash, rebase o merge automáticamente. Hacerlo
  solo si forma parte explícita del pedido y después de comprobar que el trabajo
  local está protegido.
- Leer la Constitución, el contrato vigente y la Spec relacionada antes de
  modificar IAM, workflow, persistencia, seguridad, correo o despliegue.
- Leer `docs/KNOWN_RISKS.md` y no convertir una divergencia conocida en una
  regla nueva, un test de aceptación o una simplificación del contrato.
- Identificar la Spec que gobierna el cambio y comprobar su estado antes de
  marcar tareas o aceptación. Un checkbox documental no es evidencia: solo se
  marca después de ejecutar la validación descrita y revisar su resultado.
- Mantener el cambio mínimo y trazable. No aprovechar una tarea para hacer
  refactors, upgrades o limpiezas no solicitadas.

## Límites no negociables

### Producción y servicios externos

- El alcance por defecto es local: `localhost`, `127.0.0.1` y los contenedores
  Docker del proyecto.
- No conectarse a Neon, Render, Vercel, Brevo, SMTP real ni otros recursos
  remotos para probar o diagnosticar salvo autorización explícita del usuario.
- No abrir un túnel público ni ejecutar `scripts/start-preview.ps1` salvo que el
  usuario pida explícitamente un preview; usar solo datos y credenciales de prueba.
- No ejecutar despliegues, deploy hooks ni el workflow `Deploy production` sin
  una solicitud explícita de despliegue. Producción exige `main`, confirmación
  `DEPLOY` y la aprobación humana configurada en el environment `production`.
- Las verificaciones de producción son solo lectura/no destructivas. Nunca crear,
  editar o borrar Solicitudes, Usuarios, Roles, Grupos, Áreas o archivos allí.
- No enviar correos reales en pruebas. En local conservar
  `EMAIL_MODE=console`; SMTP/Brevo requieren un objetivo explícito y destinatario
  controlado.

### Secretos, datos y respaldos

- No abrir, imprimir, copiar, restaurar ni analizar `.env`, `*.dump`, archivos
  bajo `backups/`, credenciales, tokens o datos exportados, salvo que el usuario
  autorice expresamente una remediación de seguridad con alcance definido.
- Para configuración usar únicamente archivos `*.example`. Si basta validar una
  variable, informar presencia/ausencia sin mostrar su valor.
- Nunca colocar secretos en Git, Vite, logs, capturas, comentarios, commits o
  respuestas. Todo valor `VITE_*` es público en el navegador.
- No editar archivos `.env` locales. No versionar dumps, bases, uploads ni datos
  reales. Si se descubre uno ya versionado, detenerse y reportarlo; purgar
  historia o rotar credenciales requiere un plan coordinado y autorización.

### Git y sistema de archivos

- Prohibidos sin autorización específica: `git reset --hard`, `git clean`,
  `git checkout --`, force push, reescritura de historia y borrados recursivos.
- No revertir ni sobrescribir cambios del usuario. No borrar archivos para
  silenciar tests.
- No editar artefactos generados o dependencias: `dist/`, `node_modules/`,
  `.venv/`, `__pycache__/`, `.pytest_cache/`.
- Commit, push, creación/modificación de PR y acciones remotas solo cuando el
  usuario los pida. Un commit debe incluir únicamente archivos de la tarea.

### Base de datos y migraciones

- Tratar toda revisión Alembic existente como desplegada e inmutable. Una
  evolución física se implementa con una nueva revisión sobre el head actual;
  nunca reescribir la baseline ni una migración histórica.
- No ejecutar `alembic downgrade`, `DROP`, `TRUNCATE`, restauraciones, resets de
  datos ni `docker compose down -v` contra datos persistentes sin autorización
  explícita y confirmación del destino exacto.
- Antes de una operación potencialmente destructiva, comprobar ambiente,
  host/base/schema y estrategia de respaldo. Producción o una base compartida no
  son destinos de experimentación.
- SQLite sirve para pruebas unitarias, pero no valida schema, ENUM ni SQL propio
  de PostgreSQL. Cambios de persistencia requieren validación adicional contra
  el PostgreSQL local de Compose.

### Dependencias y automatización

- No cambiar versiones, usar `latest`, regenerar lockfiles ni instalar nuevas
  dependencias salvo que la tarea lo necesite. Explicar el motivo y validar el
  diff del lockfile.
- No desactivar tests, auditorías, guards, rate limits o validaciones para lograr
  un resultado verde.
- No convertir scripts de diagnóstico en mutaciones implícitas. Los sembradores
  solo pueden apuntar al PostgreSQL local y deben usar datos inequívocamente demo.
- `app.demo_monitoring` y `app.live_demo` mutan datos: ejecutarlos únicamente
  dentro del backend de Compose y solo cuando la tarea requiera esos escenarios.

## Particularidades de esta arquitectura

- FastAPI es la autoridad final de autorización; ocultar un botón nunca sustituye
  un guard backend.
- `frontend/vite.config.js` transforma código legacy de `main.jsx` durante el
  build e inyecta componentes modulares. Antes de editar una implementación
  duplicada, rastrear el transform para identificar cuál llega al bundle.
- `expense-form.jsx`, `home-dashboard.jsx`, `iam-admin.jsx` y otros módulos
  listados en el README son las superficies nuevas; los anchors de extracción en
  `main.jsx`/`vite.config.js` siguen siendo frágiles. Todo cambio allí exige
  `npm run build`.
- IAM usa grants aditivos `RolePermission ∪ GroupPermission`, sin `DENY`.
  `GroupMember`, Cargo y nombres organizacionales no autorizan;
  `config:manage` sigue reservado a `system_accounts`.
- Un Usuario puede tener máximo un Rol por Grupo y varios Roles globales. La
  regresión actual de `UsersPanel` que conserva solo `role_ids[0]` no es contrato;
  no fijarla en nueva documentación o pruebas ni permitir que un guardado borre
  Roles que la UI no representa.
- `Role.max_users` es `NULL` para ilimitado o un entero positivo. Cuenta solo
  Usuarios activos asignados; un Usuario inactivo conserva el Rol sin consumir
  cupo. Asignación y reactivación deben rechazar un Rol lleno, y el máximo no
  puede reducirse por debajo de la ocupación activa.
- El cupo se aplica en FastAPI, bajo bloqueo transaccional de los Roles en orden
  estable. Debe cubrir rutas canónicas, rutas legacy aún expuestas y
  reactivaciones; `assigned_user_count` o un selector deshabilitado en frontend
  no sustituyen la comprobación de servidor.
- Toda edición de acceso se prepara en UI y se persiste solo con **Guardar
  cambios**. El envío confirmado de un enlace de restablecimiento es una acción
  de seguridad inmediata y constituye una excepción explícita: no debe aplicar
  ni descartar el borrador IAM.
- Restablecer contraseña requiere `config:manage`, Usuario activo no técnico y
  confirmación. El correo lleva `/reset-password#token=...`, nunca una
  contraseña; token, contraseña y hash no se imprimen ni persisten en logs o
  auditoría. Emitir incrementa `password_reset_version` e invalida enlaces
  anteriores sin cambiar contraseña o sesiones; consumir revoca sesiones. Un
  cambio de correo o estado también invalida enlaces pendientes.

## Validación mínima proporcional

Ejecutar desde la raíz o indicar claramente el directorio de trabajo. Si una
herramienta no está disponible, reportarlo; no declarar una prueba exitosa sin
haberla ejecutado.

Siempre:

```powershell
git diff --check
git status --short
```

Documentación/guardrails:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest tests.test_documentation_contract -v
```

Backend o contrato API:

```powershell
cd backend
.\.venv\Scripts\python.exe -m compileall -q app scripts
.\.venv\Scripts\python.exe -m scripts.run_tests
```

No sustituir el runner por discovery directo: `scripts.run_tests` evita leer
`backend/.env` y fuerza SQLite + correo console dentro del proceso de prueba.

Frontend:

```powershell
cd frontend
npm ci
npm run build
npm audit --omit=dev --audit-level=moderate
```

Persistencia, migraciones o SQL PostgreSQL:

```powershell
docker compose up -d --build
docker compose exec -T backend alembic current
docker compose exec -T backend alembic heads
```

Cambios visuales requieren además prueba de navegador local. Para Accesos,
comprobar al menos anchos 320, 390, 440, 640, 1024 y 1180 px, sin overflow
horizontal, controles recortados ni pérdida de foco visible.

## Documentación y cierre

- Un cambio funcional, de seguridad, UX, persistencia u operación debe revisar
  Constitución, Spec/plan/checklist, prompt, README, docs y CHANGELOG/HISTORY
  según `docs/DOCUMENTATION_POLICY.md`.
- Aplicar la matriz de impacto de `docs/DOCUMENTATION_POLICY.md`: no cerrar un
  cambio IAM, de correo, persistencia o UX actualizando solo un documento.
- Cuando una nueva regla proteja contra regresiones de IA, incorporarla también
  a `backend/tests/test_documentation_contract.py`. La prueba debe comprobar la
  fuente canónica o su sincronización, no congelar deuda legacy como contrato.
- No subir la versión constitucional por una corrección puramente editorial;
  hacerlo solo si cambia el contrato normativo.
- Antes de entregar, resumir archivos modificados, pruebas realmente ejecutadas,
  riesgos o limitaciones pendientes y cualquier acción externa realizada.
- Si se eliminó algo material, indicar exactamente qué y cómo recuperarlo.
