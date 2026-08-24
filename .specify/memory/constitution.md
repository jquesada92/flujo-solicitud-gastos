# Constitución del proyecto

**Proyecto:** Flujo de Control de Gastos  
**Versión:** 2.16.0
**Vigente desde:** 2026-08-24

## 1. Propósito

El producto digitaliza solicitudes de gasto y sus decisiones con trazabilidad verificable. Debe servir a distintos tipos de organización sin introducir reglas de negocio dependientes del nombre de una organización, grupo, cargo, rol, usuario o área.

FastAPI es la autoridad final para autorización, transiciones, acceso a documentos y capacidades por solicitud. El frontend puede anticipar esas reglas por UX, pero nunca sustituirlas.

## 2. Fuente de verdad y documentación

Orden de autoridad:

1. esta Constitución;
2. `specs/**/spec.md` vigentes;
3. checklists de aceptación;
4. `specs/**/plan.md`;
5. `PROMPT_RECONSTRUCCION.md`;
6. `README.md`;
7. `docs/`;
8. código de compatibilidad explícitamente marcado como deuda.

Un cambio funcional, de seguridad, persistencia, UX o arquitectura no está terminado si deja estas fuentes desalineadas. La documentación normativa describe el estado actual del producto; HISTORY/CHANGELOG pueden resumir evolución, pero no convierten un diseño anterior en alternativa vigente.

## 3. Terminología canónica

- **Usuario**: cuenta autenticable del producto.
- **Grupo**: ámbito organizacional opcional que puede contener cero o más Roles y aportar Permisos heredables a esos Roles.
- **Rol**: conjunto reutilizable de Permisos propios. Puede ser global o pertenecer como máximo a un Grupo; si está agrupado suma los Permisos de su Grupo.
- **Rol global**: Rol sin Grupo. No crea membresía de Grupo.
- **Permiso**: capacidad IAM atómica implementada por el producto.
- **Cargo / Posición**: dato organizacional descriptivo. No concede acceso.
- **Área**: unidad, función o contexto organizacional asociado al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.
- **Inicio**: vista personal y operativa del usuario conectado.
- **Seguimiento**: vista de solo lectura de carga del equipo por Grupo, miembro y Rol.
- **Accesos**: consola administrativa de Usuarios, Grupos, Roles y Permisos.
- **Enviar a revisión**: decisión del aprobador que interrumpe la ronda y devuelve la solicitud al solicitante.
- **Corregir / reenviar**: edición por solicitante original o Administrador del sistema cuando el estado lo permite.
- **Delegación de cierre/factura**: autoridad por solicitud, explícita y revocable.

No se crearán sinónimos funcionales para estos conceptos.

## 4. IAM vigente

Modelo normativo:

```text
Permiso propio    → Rol ── 0..1 Grupo ← Permiso heredable
                       ↑
                    Usuario

Usuario activo → requests:read (baseline)
Cargo          → dato organizacional, sin autorización
SystemAccount  → política técnica protegida + Rol global técnico
```

Reglas obligatorias:

1. Un Grupo puede existir con cero Roles y cero miembros.
2. Un Rol puede pertenecer a cero o un Grupo; nunca a más de uno.
3. Un Rol sin Grupo es un Rol global.
4. Un Usuario puede tener como máximo un Rol dentro de cada Grupo.
5. Un Usuario puede tener cero o más Roles globales ordinarios.
6. Asignar un Rol agrupado al Usuario determina automáticamente su membresía en ese Grupo.
7. Quitar o volver global ese Rol elimina la membresía derivada cuando el Usuario ya no conserva otro Rol de ese Grupo.
8. Un Rol global no crea membresía de Grupo.
9. No se asignan Permisos directamente a Usuarios.
10. Un Cargo no hereda Roles ni Permisos y no participa en `effective_permission_codes()`.
11. Cada Usuario puede tener como máximo un Cargo activo asociado.
12. El nombre/código de Grupo, Rol, Cargo, Área o Usuario nunca autoriza por sí mismo.
13. Un Grupo puede tener cero o más Permisos; cada Rol activo vinculado a ese Grupo hereda esos Permisos mientras el Grupo esté activo.
14. Para un Rol agrupado, los Permisos aplicables son la unión aditiva de sus Permisos propios y los de su Grupo. La ausencia de un Permiso propio significa “heredar si el Grupo lo aporta”; no existe `DENY` ni precedencia negativa a nivel de Rol.
15. Editar los Permisos de un Grupo o mover un Rol entre Grupo y scope global no borra ni reemplaza sus filas `RolePermission`. Al desvincularlo solo deja de heredar del Grupo y conserva sus Permisos propios y sus asignaciones de Usuario.
16. `GroupMember` es una proyección organizacional. Una fila de membresía sin `UserRoleAssignment` a un Rol activo de ese Grupo no concede ningún Permiso.

Permisos vigentes:

```text
requests:read     baseline para usuarios activos
requests:create   crear solicitudes nuevas
requests:approve  aprobar, rechazar, votar y enviar a revisión cuando corresponda
areas:manage      administrar Área + Categoría
config:read       consultar Configuración sin mutarla
config:manage     administración técnica protegida
```

`requests:close` puede existir físicamente como registro inactivo de compatibilidad, pero no autoriza cierre ni factura.

Para un usuario ordinario activo:

```text
effective_permissions =
    {requests:read}
  ∪ permisos propios de sus Roles globales activos
  ∪ permisos propios de sus Roles agrupados activos cuyo Grupo esté activo
  ∪ permisos de cada Grupo activo alcanzado por uno de esos Roles agrupados
  - {config:manage}
```

Para cada Rol agrupado, la operación es `RolePermission ∪ GroupPermission`: los duplicados se colapsan y un Permiso heredado no puede negarse desde el Rol. La mera existencia de `GroupMember` no participa en esta resolución.

`config:manage` solo es efectivo conforme a la política de `system_accounts`, aunque figure en un Grupo o Rol ordinario. `config:read` y `areas:manage` pueden llegar como Permiso propio de un Rol o por herencia de Grupo.

## 5. Accesos

`Configuración → Accesos` es la superficie administrativa de IAM. Su modelo visible es:

```text
Usuarios → Acceso por grupo → máximo un Rol por Grupo
         → Roles globales   → cero o más
Grupos   → Permisos heredables + Roles opcionales + miembros derivados (solo lectura)
Roles    → Permisos propios + herencia visible del Grupo
Permisos → catálogo de capacidades
```

No se muestran permisos individuales. Cargo no forma parte de la matriz de autorización de Accesos.

Toda edición de acceso se prepara localmente y se persiste únicamente mediante un botón explícito **Guardar cambios**. Marcar, desmarcar o seleccionar opciones no debe producir mutaciones por sí solo. Si se abandona una edición con cambios pendientes, la UI debe pedir confirmación.

La edición de un Rol puede actualizar el estado local con la respuesta del `PATCH`; no requiere un GET adicional para reflejar su nombre o estado.

Mover un Rol entre “global” y un Grupo no elimina sus asignaciones de Usuario ni sus `RolePermission`. La aplicación debe recalcular la membresía derivada y rechazar el cambio si produciría dos Roles del mismo Grupo para un mismo Usuario. Al quedar global, el Rol deja de recibir `GroupPermission`; al vincularse a otro Grupo, suma la herencia de ese Grupo a sus Permisos propios.

## 6. Configuración

- `config:read`: lectura de recursos de Configuración. Puede satisfacer guards de `config:manage` únicamente para `GET`/`HEAD`.
- `config:manage`: mutaciones técnicas y de IAM; reservado a la política protegida del Administrador del sistema.
- `areas:manage`: mutaciones de Área, Categoría y relaciones; no concede administración IAM.

Una mutación nunca se autoriza por `config:read`.

## 7. Cargo

Cargo/Posición es metadato organizacional opcional, con cardinalidad `Usuario 0..1 Cargo`. Puede aparecer en comunicaciones y vistas organizacionales, pero cambiar Cargo no cambia los permisos efectivos.

Las notificaciones de creación/cambio pueden incluir el Cargo y siempre deben calcular los permisos desde el IAM vigente: Permisos propios de Roles globales o agrupados, más la herencia aditiva de sus Grupos activos.

## 8. Inicio y Seguimiento

### Inicio

Responde a: **“¿Qué tengo que atender yo?”**

- acciones pendientes asignadas al usuario;
- solicitudes creadas por ese usuario;
- métricas personales;
- acceso contextual a aprobación, votación, corrección o cierre cuando corresponda.

### Seguimiento

Responde a: **“¿Cómo está la carga del equipo?”**

- Grupos activos;
- miembros derivados de Roles agrupados;
- Rol de cada miembro dentro del Grupo;
- cantidad de acciones pendientes por usuario y por Grupo;
- búsqueda por usuario/grupo/rol;
- filtro de usuarios con pendientes.

Los Roles globales no crean filas de membresía en Seguimiento. Es de solo lectura y no modifica accesos.

## 9. Sesión y rutas privadas

Toda pantalla protegida requiere sesión válida. Abrir directamente una ruta/hash privado sin token debe volver al Login sin montar una vista parcial. Un `401` con token almacenado invalida la sesión local y retorna al Login.

La regla aplica al menos a Accesos y Seguimiento y debe extenderse a cualquier nueva superficie privada.

## 10. Política de requests del frontend

La aplicación no debe producir tráfico continuo por re-render, efectos React o temporizadores accidentales.

Reglas:

- carga inicial al entrar;
- recarga por mutación real, navegación relevante o acción explícita;
- no polling sub-segundo;
- GET idénticos concurrentes comparten una sola llamada;
- repeticiones automáticas pueden reutilizar una respuesta reciente durante una ventana corta;
- POST/PUT/PATCH/DELETE invalidan la caché de lectura;
- una acción humana explícita puede solicitar datos frescos;
- autenticación, archivos y URLs tokenizadas no se cachean con el gobernador general.

Si una feature futura necesita polling, debe documentar propósito y frecuencia y no puede usar un intervalo agresivo por defecto.

## 11. Solicitudes y clasificación

Contrato canónico:

```text
expense_area
expense_category
```

Área y Categoría son catálogos independientes con relación N:M configurable.

El formulario **Nueva solicitud / Registrar gasto** solo se ofrece a usuarios con `requests:create`. `requests:read` permite consultar, pero no crear.

Tipos de solicitud:

```text
SIMPLE
MULTI_QUOTE
```

Una corrección conserva el tipo:

```text
SIMPLE      → SIMPLE
MULTI_QUOTE → MULTI_QUOTE
```

Una ronda `MULTI_QUOTE` congela como participantes a usuarios activos con permiso efectivo `requests:approve`, excluye al solicitante y exige soporte válido en cada opción. Cada invitado mantiene un voto activo y todo cambio conserva evento. La ronda espera a todos los invitados: un ganador único lleva a `APPROVED`; un empate permanece en `QUOTATION_VOTING`.

## 12. Acciones pendientes

Tipos actuales:

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

Son tareas contextuales, no Permisos IAM.

## 13. Aprobación, revisión y corrección

Una decisión de aprobación puede ser `APPROVED`, `REJECTED` o `REVISION_REQUESTED`.

Una revisión válida:

```text
approval actual       → REVISION_REQUESTED
solicitud             → NEEDS_REVISION
otras PENDING/WAITING → EXPIRED
solicitante           → CORRECT_REQUEST
```

El aprobador no obtiene capacidad de edición. Corregir corresponde al solicitante original o al Administrador del sistema cuando la solicitud es corregible.

## 14. Cancelación, cierre y factura

Capacidades por recurso:

```text
can_cancel
can_correct
can_close
can_delegate_close
```

Cerrar/facturar requiere estado compatible y una de estas relaciones:

```text
solicitante original
OR system_accounts
OR delegado activo de esa solicitud
```

`requests:close` no participa.

## 15. Cuenta técnica

La identidad técnica se persiste en `system_accounts`; no se deriva de nombre, correo, Cargo o `UserRole`.

`Administrador del sistema` es un **Rol global técnico** (`system_managed`) y no pertenece a ningún Grupo. El bootstrap lo asigna a la cuenta técnica para representar su responsabilidad, pero esa asignación no sustituye la política protegida de `system_accounts`.

En producción, la política técnica vigente es:

```text
requests:read
areas:manage
config:manage
```

No participa en aprobación ni votación. Conserva excepciones administrativas por recurso donde el backend las define. El Rol global técnico no puede asignarse, quitarse ni modificarse desde la consola ordinaria.

## 16. Persistencia y Neon

Base de datos de aplicación:

```text
ph_torre_delta
└── administracion
```

`DATABASE_SCHEMA=administracion` es obligatorio. `public` no se usa como schema de aplicación.

Compatibilidad Neon pooled:

- SQLAlchemy usa `MetaData(schema=DATABASE_SCHEMA)`;
- Alembic usa schema explícito y `version_table_schema`;
- no se envía `options=-csearch_path=...` como parámetro de startup al pooler;
- las migraciones crean el schema si falta.
- los tipos Enum ORM heredan el schema de metadata;
- SQL crudo usa nombres de tabla calificados derivados de metadata.

Cadena Alembic vigente:

```text
20260820_0001_initial_schema
→ 20260820_0002_group_scoped_roles
→ 20260821_0003_single_user_position
→ 20260821_0004_allow_global_roles
→ 20260821_0005_activity_periods
→ 20260821_0006_period_snapshot_values
→ 20260821_0007_period_audit_metadata
→ 20260821_0008_normalize_period_timestamps
→ 20260824_0009_group_permission_inheritance
```

`20260824_0009_group_permission_inheritance` agrega `group_permissions` vacía para no alterar accesos existentes durante la migración. La tabla relaciona Grupo y Permiso de forma única; no introduce denegaciones ni modifica `role_permissions`.

Usuarios, Áreas, Roles y Grupos mantienen historial temporal versionado. Cada
alta crea una fila cuyo `active_from` coincide con `created_at`; toda modificación
relevante cierra la versión vigente y abre otra con una instantánea JSON. Siempre
existe como máximo una versión abierta, también cuando `active=false`; el valor
JSON permite distinguir períodos activos e inactivos. Usuario conserva cédula,
contacto, nombre y Roles; Rol conserva el Grupo asociado. Las restricciones
físicas impiden fechas invertidas y más de una versión abierta por entidad.
Cada versión identifica además quién realizó el cambio, cuándo ocurrió, el tipo
de evento, los campos modificados y el valor anterior/nuevo. Las acciones
autenticadas registran ID, correo y cédula del actor; procesos sin sesión usan
un identificador `SYSTEM:*`. La auditoría nunca almacena contraseñas o secretos.

Las pantallas operativas y de configuración no muestran entidades inactivas.
Intentar crear nuevamente un Usuario por cédula, o un Área/Rol/Grupo por su
clave o nombre normalizado, debe ofrecer recuperar la entidad inactiva: el
backend devuelve su ID y datos, la UI completa el formulario con confirmación y
la reactivación conserva la identidad y el historial en vez de insertar un duplicado.

La baseline `0001` permanece congelada después de desplegarse; los cambios físicos posteriores se agregan como nuevas revisiones.

## 17. Seguridad operativa

- contraseñas nuevas con Argon2 mediante `pwdlib`;
- sesiones JWT con versión revocable e inactividad;
- CORS explícito en producción;
- documentos privados servidos por backend autorizado;
- respuestas API sensibles con `Cache-Control: no-store`;
- rate limiting por usuario autenticado;
- secretos solo en variables de entorno/plataformas, nunca frontend o repositorio.

## 18. Definition of Done

Todo cambio relevante debe revisar y actualizar, según aplique:

```text
.specify/memory/constitution.md
specs/**/spec.md
specs/**/plan.md
specs/**/checklists/acceptance.md
PROMPT_RECONSTRUCCION.md
README.md
docs/
docs/HISTORY.md
CHANGELOG.md
```

Validaciones mínimas:

```text
cd backend
alembic heads
# esperado: 20260824_0009
\.venv\Scripts\python.exe -m unittest discover -s tests -v

cd ..
docker compose up -d --build
docker compose exec -T backend python -m app.demo_monitoring

cd frontend
npm ci
npm run build
```

Para cambios IAM, la aceptación debe cubrir además la unión aditiva Rol ∪ Grupo, ausencia de `DENY`, conservación de `RolePermission` al editar o desvincular, ausencia de autoridad por `GroupMember` aislado y exclusión de `config:manage` para usuarios ordinarios.

GitHub Actions puede ser un gate adicional cuando exista cuota disponible; su indisponibilidad no convierte un run sin steps en evidencia de fallo del código.
