# Changelog

## 2.21.0 — 2026-08-26

- las rondas `MULTI_QUOTE` permanecen en `QUOTATION_VOTING` aunque exista un
  ganador único provisional;
- los invitados conservan **Votar o cambiar voto** hasta que se registre la
  factura, manteniendo un voto activo y un evento inmutable por cada cambio;
- un empate limpia la selección provisional y bloquea la factura con 409 sin
  persistir adjuntos;
- el cierre recalcula votos bajo bloqueo y solo una población completa con
  ganador único pasa directamente a `CLOSED` al subir factura;
- Alembic `20260825_0012_keep_quotation_voting_open` devuelve a votación las
  solicitudes múltiples antiguas en `APPROVED` sin factura;
- Inicio y Seguimiento muestran voto actual, cambio de voto, empate y ganador
  provisional; se agregan pruebas integrales y guardrails contra regresiones.
- la tabla operativa de Solicitudes muestra para `MULTI_QUOTE` el máximo sin
  votos, el monto del líder único o el máximo ante empate, sin alterar el monto
  financiero canónico.

## 2.20.0 — 2026-08-25

- layout móvil transversal desde 320 px, con navegación táctil desplazable y
  vista actual identificable;
- consulta de Solicitudes convertida de tabla fija de 1450 px a tarjetas
  etiquetadas en celular, sin eliminar datos ni acciones;
- filtros, tableros, Accesos y Seguimiento apilables con textos largos legibles;
- menús, confirmaciones, acciones pendientes y visores ajustados a `100dvh`,
  `safe-area` y objetivos táctiles de al menos 44 px;
- nueva Spec 020 y contrato estático; la aceptación visual completa permanece
  pendiente hasta revisar navegador en todos los anchos exigidos.

## 2.19.0 — 2026-08-25

- las solicitudes `SIMPLE` seleccionan aprobadores IAM aunque no exista una
  `ApprovalPolicy` aplicable, usando `MAJORITY` como modalidad predeterminada;
- Permiso propio de Rol agrupado, herencia de Grupo y Rol global con
  `requests:approve` participan de forma equivalente, excluyendo al Solicitante;
- reglas legacy por correo dejan de seleccionar aprobadores;
- crear una solicitud con URL prepara la ronda en la misma transacción y, si un
  soporte se carga aparte, el fallo del flujo elimina la solicitud y el archivo;
- Accesos separa visualmente el código efectivo de su origen para evitar textos
  engañosos como `requests:approveRol` o `requests:approveGrupo`;
- nueva Spec 019 y pruebas de regresión para población IAM y creación sin filas
  huérfanas;
- guardrails, matriz documental, Configuración y runbook local fijan
  `approver_profile_codes` como metadata legacy sin autoridad y registran la
  divergencia visual de la pantalla Reglas.

## 2.18.0 — 2026-08-25

- guía de usuario final para Solicitantes y Junta Directiva, con creación,
  aprobación, votación, corrección, factura, cierre y solución de problemas;
- `AGENTS.md` protege explícitamente los cupos de Rol, las rutas concurrentes y
  legacy, la excepción inmediata del restablecimiento y la preservación de
  asignaciones múltiples frente a simplificaciones de IA;
- la política documental incorpora una matriz de impacto y el contrato
  automático detecta resultados Alembic obsoletos y ausencia de guardrails IAM;
- Roles admiten un `max_users` opcional para limitar Usuarios activos asignados;
- Usuarios inactivos conservan su Rol sin consumir cupo y la reactivación vuelve a validarlo;
- asignación y reducción del máximo se protegen con validación backend y bloqueo transaccional del Rol;
- Accesos muestra ocupación/máximo, edita el límite con **Guardar cambios** y marca Roles sin cupo;
- migración `20260825_0011_role_user_limit` conserva Roles existentes ilimitados y amplía sus instantáneas temporales;
- el enlace de restablecimiento usa fragmento, cambios de correo/estado lo invalidan, el rate limit reconoce proxies locales de forma acotada y se envía confirmación best-effort posterior al commit.

## 2.17.0 — 2026-08-24

- ficha de Usuario incorpora envío confirmado de enlace de restablecimiento para
  cuentas activas no técnicas, separado de **Guardar cambios**;
- token de propósito exclusivo, un uso y 30 minutos por defecto, con
  invalidación de emisiones anteriores mediante `password_reset_version`;
- emisión no rota contraseña ni sesiones y hace rollback si falla el correo;
- consumo público aplica Argon2, limpia `must_change_password`, revoca sesiones,
  invalida enlaces y vuelve al Login sin auto-login;
- template de correo específico con enlace y sin contraseña, auditoría segura y
  rate limits diferenciados para emisión autenticada y consumo público;
- migración `20260824_0010_password_reset_links` y configuración
  `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30`.

## 2026-08-24 — soporte de desarrollo y guardrails

- `AGENTS.md` incorpora límites explícitos para Git, producción, secretos, dumps, migraciones, Docker, correo y servicios externos;
- prueba automática del contrato documental para enlaces, versión constitucional, head Alembic, rutas críticas, ejemplos de entorno y gate productivo;
- runner backend aislado que deshabilita `backend/.env` y fija SQLite/console para evitar pruebas contra conexiones locales o externas accidentales;
- PR y release comparten un único CI reusable con compileall, suite, build/auditoría frontend, anclas del bundle, imágenes y smoke del entrypoint;
- README y runbooks locales/productivos alineados con Docker Compose, Python 3.12, PostgreSQL 16 y el entrypoint real del backend;
- ejemplos de entorno pasan a correo `console`, eliminan schema/variables obsoletas y evitan sugerir Neon para Docker local;
- preview público exige credenciales administrativas propias y aplica URL/CORS del túnel al backend;
- consola de Accesos documentada y validada sin overflow a 1024, 640, 440, 390 y 320 px;
- tarjetas de Usuario en Accesos muestran debajo del correo todos los Roles asignados, incluidos los inactivos conservados, sin agregar una línea cuando no hay Roles;
- divergencia multirol de `UsersPanel`, dumps rastreados, identidad de release, correo productivo y conexión de migraciones registrados como riesgos abiertos, sin rebajar el contrato para ocultarlos.

## 2.16.0 — 2026-08-24

- Permisos heredables configurables a nivel de Grupo;
- resolución aditiva `RolePermission ∪ GroupPermission` para Roles agrupados, sin `DENY`;
- conservación de Permisos propios al editar el Grupo o convertir el Rol en global;
- `GroupMember` ratificado como proyección sin autoridad de acceso;
- `config:manage` conservado como capacidad exclusiva de `system_accounts`;
- nueva revisión Alembic `20260824_0009_group_permission_inheritance`, sin backfill de grants;
- consola de Accesos actualizada para distinguir Permisos heredables y propios.

## 2.15.0 — 2026-08-21

- listas GUI activas para Usuario, Área, Rol y Grupo;
- recuperación backend de entidades inactivas por llave de negocio;
- autocompletado confirmado y reactivación con el mismo ID;
- preservación integral del historial de auditoría.

## 2.14.0 — 2026-08-21

- historial temporal de actividad para Usuarios, Áreas, Roles y Grupos;
- migración `20260821_0005_activity_periods` con backfill y restricciones;
- migración `20260821_0006_period_snapshot_values` con instantáneas JSON;
- migración `20260821_0007_period_audit_metadata` con actor, timestamp y diferencias;
- migración `20260821_0008_normalize_period_timestamps` para vigencias UTC;
- registro transaccional de altas y toda modificación relevante, incluidas relaciones IAM;
- pruebas unitarias y PostgreSQL local para integridad y períodos múltiples.

## 2026-08-21 — validación PostgreSQL y escenarios locales

- Constitución 2.13.0 formaliza población, voto y resolución de MULTI_QUOTE;
- se corrige generación de identificadores para calificar `category_counters` con el schema de aplicación;
- los Enum ORM heredan `administracion`, evitando casts PostgreSQL contra tipos inexistentes en `public`;
- Docker local fuerza correo `console` por defecto;
- `demo_monitoring` se alinea con Roles IAM explícitos y correos válidos;
- el sembrador crea escenarios persistentes SIMPLE y MULTI_QUOTE, incluida votación abierta y voto parcial;
- se documentan pruebas adversas, límites, credenciales demo y diferencia entre fixtures unitarios y datos visibles;
- suite local: 161 pruebas exitosas y build frontend exitoso.

## 2026-08-21

### IAM / contrato 2.12.0

- un Grupo puede existir con cero Roles;
- un Rol puede pertenecer a cero o un Grupo; un Rol sin Grupo es global;
- un Usuario mantiene máximo un Rol por Grupo y puede tener varios Roles globales ordinarios;
- los Roles globales participan en permisos efectivos sin crear `GroupMember`;
- quitar un Rol de un Grupo lo convierte en global sin borrar asignaciones de Usuario;
- agrupar Roles se rechaza si produciría dos Roles del mismo Grupo para un Usuario;
- `Administrador del sistema` se representa como Rol global técnico protegido, mientras `SystemAccount` conserva la autoridad de privilegios;
- nueva revisión Alembic `20260821_0004_allow_global_roles`;
- Accesos separa **Acceso por grupo** y **Roles globales**;
- se corrige la prueba obsoleta de Seguimiento para usar `_group_role_names`.

### Documentación / contrato 2.11.0 → 2.12.0

- se actualiza Constitución, README y prompt maestro al modelo vigente;
- se reescriben reglas IAM en Specs 006/011 y documentación de Accesos;
- se mantienen `docs/CURRENT_PRODUCT_CONTRACT.md` y `docs/FRONTEND_RUNTIME.md` como mapas de contrato/runtime;
- se alinean IAM, Configuración, Terminología, Seguimiento, Neon, FastAPI, Correo, Clasificación, Correcciones y Cierre;
- se eliminan de documentación normativa modelos, ramas y cadenas de migración ya sustituidos.

### Cargo

- contrato funcional: máximo un Cargo por Usuario;
- Cargo es metadato organizacional y no concede acceso;
- revisión Alembic `20260821_0003_single_user_position`.

## 2026-08-20

### IAM

- un Rol puede pertenecer como máximo a un Grupo;
- un Usuario tiene máximo un Rol por Grupo;
- membresía de Grupo derivada;
- permisos no directos a Usuario (modelo posteriormente ampliado con grants heredables de Grupo en 2.16.0);
- edición de acceso staged con Guardar cambios;
- actualización inmediata del nombre del Rol después de guardar.

### UX

- Inicio personal;
- nueva pantalla Seguimiento de usuarios;
- Nueva solicitud visible con `requests:create`;
- redirect a Login para rutas privadas sin sesión;
- eliminación de polling agresivo y gobernador global de GET.

### Datos / despliegue

- `expense_area` y `expense_category` como contrato canónico;
- Neon pooled compatible sin startup `search_path`;
- `DATABASE_SCHEMA=administracion` explícito;
- baseline limpia y revisiones incrementales.

## 2026-08-18/19

- hardening FastAPI/IAM;
- seguimiento y acciones pendientes;
- revisión/corrección con ownership por recurso;
- delegación de cierre/factura;
- gestión Área/Categoría y lectura de Configuración;
- notificaciones de creación/cambio de Cargo con permisos efectivos.
