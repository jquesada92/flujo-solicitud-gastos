# Constitución del proyecto

**Proyecto:** Flujo de Control de Gastos  
**Versión:** 2.2.0  
**Vigente desde:** 2026-08-17

## 1. Evolucionar, no reconstruir sin necesidad

El producto existente debe evolucionar sobre el repositorio actual. Se reutiliza el código correcto y se migra o reemplaza únicamente lo que contradiga esta constitución, las especificaciones vigentes o los criterios de aceptación.

## 2. Producto neutral respecto al tipo de organización

El sistema debe poder utilizarse en empresas, PH y otras organizaciones sin introducir en el núcleo conceptos exclusivos de un dominio particular.

No forman parte del modelo canónico:

- apartamentos;
- propietarios o copropietarios;
- residentes o arrendatarios;
- `PersonType`;
- `OwnershipRole`;
- relaciones usuario-apartamento.

La estructura organizacional tampoco puede quedar codificada mediante nombres como Junta Directiva, Administradora, Presidente, Tesorero, Finanzas, IT u otros. Esos nombres pueden existir como **datos configurados por cada organización**, nunca como condiciones de autorización en runtime.

## 3. Terminología canónica

- **Usuario**: cuenta que interactúa con el sistema.
- **Grupo**: conjunto configurable de usuarios.
- **Rol**: conjunto configurable de permisos.
- **Permiso**: capacidad atómica implementada por el producto.
- **Cargo / Posición**: metadato organizacional descriptivo; no concede permisos.
- **Área**: unidad, departamento o función organizacional asociada al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.

Área y Categoría son catálogos independientes. Una Categoría puede habilitarse para múltiples Áreas mediante una relación configurable.

## 4. IAM configurable: permisos sobre nombres

La autorización canónica se resuelve mediante permisos efectivos persistidos en PostgreSQL.

Modelo:

```text
Usuario → Grupo → Rol → Permiso
       ↘ Rol directo
       ↘ Permiso directo
       ↘ Cargo/Posición (descriptivo solamente)
```

Los permisos efectivos son la unión de:

1. permisos directos del usuario;
2. permisos de roles asignados directamente;
3. permisos de roles heredados a través de grupos activos.

Si una capacidad no está permitida explícitamente, el resultado es **DENY**.

El producto define las capacidades atómicas disponibles. Cada organización configura desde la interfaz sus grupos, roles, cargos, membresías y asignaciones.

Permisos funcionales iniciales:

- `requests:read`;
- `requests:create`;
- `requests:approve`;
- `requests:close`;
- `config:manage`.

No autorizar por:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER` o `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure` como fuente de verdad;
- nombre de rol, grupo, cargo o perfil;
- correo fijo;
- ID mágico;
- listas de cargos como PRESIDENTE/TESORERO/etc.;
- conceptos inmobiliarios.

Los campos legacy pueden existir temporalmente durante una migración, pero no pueden ser autoridad de autorización.

## 5. Separación de funciones de la cuenta técnica

El administrador técnico de bootstrap es una **cuenta de sistema protegida**, no un superusuario financiero.

Su conjunto efectivo permitido es:

- `config:manage`;
- `requests:read`.

Una cuenta técnica no puede obtener `requests:create`, `requests:approve` ni `requests:close`, incluso si una configuración posterior intenta otorgárselos accidentalmente.

El bootstrap puede usar variables `ADMIN_*` únicamente para crear o recuperar la cuenta técnica inicial. Después del bootstrap, su autorización se representa mediante datos IAM persistidos.

## 6. Configuración gráfica sobre código

La interfaz debe permitir administrar, sin despliegue de código:

- usuarios;
- grupos;
- roles;
- cargos/posiciones;
- membresías de grupos;
- roles de grupos;
- roles directos de usuario;
- permisos directos de usuario;
- visualización de permisos efectivos y su origen;
- Áreas y Categorías;
- políticas de aprobación y demás configuración organizacional cuando corresponda.

Una organización futura puede tener estructuras completamente distintas a la configuración inicial del PH.

## 7. Backend como autoridad

El frontend puede ocultar o mostrar acciones por UX, pero el backend es la autoridad final para:

- autorización;
- transiciones;
- población de participantes;
- acceso a documentos;
- decisiones;
- configuración IAM.

Una operación sensible debe declarar una dependencia de permiso explícita o pasar por un servicio que la aplique.

## 8. Arquitectura FastAPI

El backend sigue estas reglas:

- `APIRouter` por dominio/capacidad;
- modelos SQLAlchemy fuera de routers;
- esquemas Pydantic fuera de routers cuando son contratos reutilizables;
- servicios para lógica de negocio reutilizable;
- dependencia `get_db()` con `yield`/contexto por request;
- configuración centralizada mediante Pydantic Settings;
- `lifespan` reservado a recursos de ciclo de vida, no a migraciones de esquema;
- migraciones versionadas con Alembic antes de levantar el proceso ASGI;
- response models explícitos para contratos sensibles;
- SQLAlchemy síncrono se usa desde path operations `def` para que FastAPI ejecute I/O bloqueante en su threadpool;
- pruebas HTTP con `TestClient` para autorización y contratos críticos.

`app/main.py` no debe volver a convertirse en un archivo de migraciones, seeds o lógica de dominio.

## 9. Contraseñas y sesiones

- nuevos hashes: Argon2 mediante `pwdlib` recomendado;
- hashes PBKDF2 legacy pueden verificarse temporalmente y deben migrar transparentemente a Argon2 después de un login correcto;
- JWT con expiración absoluta;
- timeout de inactividad;
- revocación por versión de sesión;
- fallos de autenticación no revelan si el usuario existe.

## 10. Historial y trazabilidad

Toda acción significativa debe poder reconstruirse con actor, fecha/hora, entidad, cambios, estado anterior/nuevo y motivo cuando aplique. Los eventos históricos relevantes son append-only.

Los cambios futuros de membresías, roles y permisos deben incorporarse al modelo de auditoría de acceso; una asignación de autorización no debe cambiar silenciosamente.

## 11. Evidencia documental

Los documentos son evidencia privada. Deben validarse por contenido real, almacenarse fuera del acceso público directo, descargarse con autorización backend, conservar versiones al sustituirse y registrar actor/fecha/motivo.

## 12. Solicitudes y clasificación

Cada solicitud se clasifica por **Área + Categoría**. La clasificación histórica no cambia retroactivamente porque un catálogo se renombre, desactive o cambie.

La solicitud simple contiene una opción/cotización. `MULTI_QUOTE` mantiene la selección de cotización separada conceptualmente del proceso de aprobación.

## 13. Participantes y decisiones

La población elegible de una ronda debe congelarse/versionarse. Para votación de cotizaciones, las invitaciones de la ronda representan el snapshot de participantes hasta que exista un modelo explícito de rondas.

Para una ronda de aprobación:

- `response_rate = valid_responses / eligible_participants`;
- solo se resuelve cuando `response_rate > 0.50`;
- `approval_rate = approvals / valid_decision_responses`;
- `rejection_rate = rejections / valid_decision_responses`;
- aprobar si `approval_rate > 0.50`;
- rechazar si `rejection_rate > 0.50`;
- empate o falta de mayoría permanece pendiente;
- solicitar corrección es una transición separada.

Las reglas de selección de cotización no se presumen iguales a las reglas de aprobación. Si el código legacy aún difiere de esta regla, debe documentarse como deuda funcional y no presentarse como resuelto por un refactor de arquitectura.

## 14. Aprobado no significa cerrado

Una solicitud aprobada permanece en proceso hasta cumplir el cierre. El cierre requiere factura y `requests:close`. Una cuenta de sistema no puede cerrar solicitudes.

## 15. Migraciones y protección de datos

Los cambios estructurales utilizan migraciones versionadas. No se permiten nuevas migraciones destructivas ad-hoc en FastAPI startup.

Orden de despliegue:

1. construir artefacto;
2. ejecutar `alembic upgrade head`;
3. ejecutar bootstrap idempotente cuando aplique;
4. iniciar `uvicorn`;
5. ejecutar health checks.

En Render económico, estos pasos pueden ejecutarse en el entrypoint Docker antes de `uvicorn`; en plataformas con pre-deploy separado, se prefiere ese mecanismo para múltiples réplicas.

Antes de retirar datos: respaldo, inventario, migración versionada, validación y recuperación real.

## 16. Seguridad y rendimiento

Como mínimo:

- default deny;
- backend authoritative;
- rate limiting diferenciado;
- CORS restrictivo;
- secretos fuera del frontend/logs;
- ORM/consultas parametrizadas;
- validación real de archivos;
- paginación backend para colecciones crecientes, default 25 y máximo 100;
- evitar N+1;
- pool y query timeout configurables antes de escalar;
- una futura capa de scope debe limitar permisos por organización/área/recurso sin reutilizar cargos como autorización.

## 17. Calidad y pruebas

Los cambios incluyen pruebas proporcionales al riesgo. Para IAM son obligatorias pruebas positivas y negativas de:

- permisos directos;
- herencia Grupo → Rol → Permiso;
- restricción de cuentas técnicas;
- endpoints `config:manage`;
- operaciones financieras negadas a la cuenta técnica;
- cambios de permisos efectivos sin reiniciar la app.

CI debe ejecutar backend tests, compilación frontend y construcción de imágenes Docker.

## 18. Documentación es parte del código

Ningún cambio funcional, de dominio, UX, API, modelo de datos, seguridad, migración o arquitectura se considera terminado si la documentación afectada no queda actualizada en el mismo PR.

Revisar cuando aplique:

- `.specify/memory/constitution.md`;
- `specs/<feature>/spec.md`;
- `specs/<feature>/plan.md`;
- criterios de aceptación;
- `README.md`;
- `PROMPT_RECONSTRUCCION.md`;
- `docs/` funcionales/técnicos;
- `docs/TERMINOLOGY.md`;
- `docs/HISTORY.md`;
- `CHANGELOG.md`;
- contratos/API y comentarios técnicos.

## 19. Consistencia entre artefactos

Prioridad:

1. Constitución vigente.
2. Especificación funcional.
3. Aclaraciones/criterios de aceptación.
4. Plan técnico.
5. Tareas y código.
6. README, prompts y documentación derivada.

Una discrepancia código-documentación es un defecto salvo que esté expresamente marcada como deuda/transición.

## 20. Definition of Done

Una feature está terminada cuando:

- comportamiento implementado coincide con requisitos y criterios;
- autorización no depende de nombres organizacionales hardcodeados;
- migraciones son versionadas y desplegables;
- términos visibles coinciden con `docs/TERMINOLOGY.md`;
- README/prompt no reconstruyen conceptos retirados;
- HISTORY explica decisiones relevantes;
- CHANGELOG registra el entregable;
- CI y pruebas mencionadas realmente existen y pasan;
- deuda temporal queda explícita, con ruta de retiro.
