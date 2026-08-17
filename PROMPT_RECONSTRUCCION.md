# Prompt maestro de reconstrucción

Reconstruye una aplicación web lista para producción llamada **Flujo de Control de Gastos**, destinada a solicitar, evaluar, aprobar, ejecutar y documentar gastos con evidencia verificable.

## Autoridad documental

Lee y respeta en este orden:

1. `.specify/memory/constitution.md`
2. `specs/**/spec.md`
3. checklists/criterios de aceptación
4. `specs/**/plan.md`
5. este prompt
6. `README.md`
7. `docs/`
8. código existente

Si existe discrepancia, prevalece el artefacto de mayor prioridad.

## 1. Producto neutral

La aplicación debe servir para PH, empresas y otras organizaciones. No introduzcas como dominio canónico apartamentos, propietarios, residentes, arrendatarios ni estructuras exclusivas de un cliente.

Tampoco hardcodees estructuras organizacionales. Nombres como Junta Directiva, Administradora, Presidente, Tesorero, Procurement, Finance, IT o Gerente pueden existir como datos configurados por un cliente, nunca como condiciones de runtime.

## 2. Terminología

Usa:

- **Usuario**: cuenta del sistema.
- **Grupo**: conjunto configurable de usuarios.
- **Rol**: conjunto configurable de permisos.
- **Permiso**: capacidad atómica implementada por el producto.
- **Cargo/Posición**: metadato descriptivo que no concede permisos.
- **Área**: unidad organizacional asociada al gasto.
- **Categoría**: naturaleza del bien/servicio.

No uses Persona/Personas como nombre del módulo de cuentas. No uses Subárea para representar Categoría.

## 3. IAM configurable

Implementa:

```text
Usuario → Grupo → Rol → Permiso
       ↘ Rol directo
       ↘ Permiso directo
       ↘ Cargo/Posición descriptivo
```

Persistencia:

- `permissions`
- `roles`
- `role_permissions`
- `user_groups`
- `group_members`
- `group_roles`
- `user_role_assignments`
- `user_permissions`
- `positions`
- `user_positions`
- `system_accounts`

Permisos iniciales:

- `requests:read`
- `requests:create`
- `requests:approve`
- `requests:close`
- `config:manage`

Los permisos atómicos son capacidades del producto. La organización configura desde la UI grupos, roles, cargos, membresías y asignaciones.

Default: DENY si una capacidad no está permitida explícitamente.

### Prohibiciones

No autorices por:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure` como fuente de verdad;
- nombres de grupos/roles/cargos;
- emails fijos;
- IDs mágicos;
- listas como `BOARD_CODES`.

Los campos legacy pueden existir solo como puente de compatibilidad y deben derivarse de IAM, no al revés.

## 4. Cuenta técnica

La cuenta creada con `ADMIN_*` es una cuenta técnica protegida.

Permisos máximos efectivos:

```text
config:manage
requests:read
```

Debe ser imposible que obtenga:

```text
requests:create
requests:approve
requests:close
```

incluso si alguien intenta asignarlos accidentalmente mediante un grupo, rol o permiso directo.

No la conviertas en superusuario financiero.

## 5. Interfaz de Accesos

Dentro de Configuración debe existir una consola gráfica para:

- Usuarios;
- Grupos;
- Roles;
- Permisos;
- Cargos;
- membresías;
- roles de grupo;
- roles directos;
- permisos directos;
- cargos de usuario;
- permisos efectivos y su origen.

La cuenta técnica debe aparecer protegida.

No requieras editar archivos o variables para crear una estructura empresarial nueva.

## 6. Clasificación Área + Categoría

Área y Categoría son catálogos independientes con relación N:M configurable.

Ejemplos:

```text
Área: Administración, Operaciones, IT, Marketing
Categoría: Equipos, Servicios/Consultoría, Insumos, Licencias
```

Una categoría `Equipos` puede habilitarse para múltiples áreas sin duplicarse.

## 7. Solicitudes

Cada solicitud conserva como mínimo:

- `request_id` inmutable;
- `flow_id`;
- `display_id`;
- solicitante;
- Área;
- Categoría;
- título;
- descripción/justificación;
- urgencia;
- tipo SIMPLE/MULTI_QUOTE;
- estado;
- documentos;
- historial;
- decisiones;
- timestamps.

Crear/corregir/cargar soporte requiere `requests:create`.

## 8. Cotizaciones

SIMPLE exige proveedor, monto y soporte.

MULTI_QUOTE mantiene varias opciones. La población de votación se obtiene desde usuarios efectivos con `requests:approve`, excluyendo al solicitante y cuentas técnicas.

Congela/versiona los participantes de cada ronda. Mientras no exista entidad explícita `QuotationVotingRound`, las invitaciones persistidas son el snapshot de la ronda.

No inventes reglas de quorum/empate no especificadas. La feature 002 mantiene explícitamente la semántica legacy hasta que exista una spec dedicada.

## 9. Aprobaciones

Los participantes se seleccionan por permisos/políticas persistidas, nunca por cargo hardcodeado.

La Constitución vigente define la regla funcional objetivo de quorum y mayoría. Si el motor legacy todavía difiere, documenta la deuda y no afirmes que está resuelta por cambios IAM.

## 10. Cierre y factura

`APPROVED` no significa `CLOSED`.

Subir/reemplazar factura y cerrar requiere `requests:close`.

La cuenta técnica jamás puede ejecutar estas acciones.

Conserva versiones anteriores de facturas y registra motivo/actor/timestamp al sustituir.

## 11. Arquitectura FastAPI

Usa:

```text
app/
├── api/          # APIRouter y capa HTTP
├── core/         # Settings, DB, security, rate limit
├── models/       # SQLAlchemy
├── schemas/      # Pydantic
├── services/     # negocio reutilizable
├── application.py
└── main.py       # alias mínimo si se requiere compatibilidad
```

Reglas:

- Pydantic Settings centralizado; no repartir `os.getenv()` por la aplicación.
- `get_db()` entrega una sesión por request y siempre la cierra.
- modelos SQLAlchemy fuera de routers.
- schemas reutilizables fuera de routers.
- response models explícitos para respuestas sensibles.
- dependencias FastAPI para autorización.
- `lifespan` solo para recursos de ciclo de vida; nunca DDL/backfills/seeds de negocio.
- Alembic para migraciones versionadas.
- SQLAlchemy actual es síncrono: rutas con DB/filesystem bloqueante deben ser `def` para ejecutarse en threadpool. No conviertas funciones en `async def` si internamente hacen I/O síncrono sin offloading.

## 12. Passwords y JWT

- Argon2 mediante `pwdlib.PasswordHash.recommended()` para hashes nuevos.
- Compatibilidad temporal con PBKDF2 legacy.
- Login PBKDF2 exitoso debe migrar el hash a Argon2.
- JWT con `sub`, versión de sesión, `iat`, `exp`.
- timeout de inactividad.
- regeneración/cambio que corresponda debe poder revocar sesiones.

## 13. Documentos

Admite PDF/JPEG/PNG/WEBP.

Valida:

- MIME;
- firma real del contenido;
- tamaño;
- cuota total;
- nombre interno impredecible.

El disco es privado y una descarga pasa por autorización backend.

## 14. Correo

Centraliza configuración en Settings.

Producción usa preferiblemente API HTTPS de Brevo. Mantén soporte console/SMTP para desarrollo si existe.

Mensajes y branding base deben ser neutrales respecto al tipo de organización.

## 15. Migraciones, Docker y despliegue

No uses `Base.metadata.create_all()` ni `migrate_schema()` en el lifespan productivo.

Secuencia:

```text
alembic upgrade head
python scripts/bootstrap_admin.py
uvicorn app.application:app
```

En Docker/Render económico puede ocurrir en el entrypoint antes de iniciar Uvicorn. En despliegues de múltiples réplicas usa una etapa única de release/pre-deploy.

Los scripts shell ejecutados dentro de imágenes Linux deben ser portables desde checkouts Windows:

- fuerza `*.sh text eol=lf` en `.gitattributes`;
- normaliza defensivamente CRLF dentro de la imagen antes de ejecutar el entrypoint;
- no asumas que `depends_on` simple significa que el backend está listo: usa healthcheck cuando Nginx u otro consumidor depende de FastAPI;
- si el backend falla durante Alembic/bootstrap/Uvicorn, deja visible ese error primario y evita que el frontend falle primero con `host not found in upstream`.

Antes de migraciones destructivas crea snapshot/backup real.

## 16. Testing

Usa tests unitarios y `FastAPI TestClient`.

Matriz IAM mínima:

- admin técnico obtiene config/read;
- admin técnico no obtiene create/approve/close;
- asignarle close accidentalmente sigue resultando DENY;
- usuario sin config obtiene 403 en administración IAM;
- Grupo→Rol→Permiso cambia acceso inmediatamente;
- permiso directo es aditivo;
- rol técnico no se edita desde UI.

Incluye una prueba de regresión de portabilidad de contenedores que verifique la política LF, la normalización defensiva de scripts y la dependencia por healthcheck del frontend local.

CI debe ejecutar:

- Python compile;
- backend tests;
- frontend build;
- Docker backend;
- Docker frontend.

## 17. Seguridad

- backend authoritative;
- secretos fuera del frontend/logs/repositorio;
- CORS explícito en producción;
- rate limiting diferenciado;
- ORM/consultas parametrizadas;
- archivos privados;
- default deny;
- no bypass por ADMIN;
- no autorización por cargo.

## 18. Auditoría

Eventos significativos deben conservar actor, tiempo, entidad, cambios y motivo. La evolución del IAM debe incorporarse a auditoría para que cambios de roles/grupos/permisos no sean silenciosos.

## 19. Documentación obligatoria

Un cambio no está terminado hasta revisar y actualizar cuando aplique:

- Constitución;
- spec;
- plan;
- criterios de aceptación;
- README;
- este prompt;
- documentación técnica/funcional;
- terminología;
- HISTORY;
- CHANGELOG;
- PR.

## 20. Deuda permitida solo si está explícita

Durante la transición pueden existir `UserRole`, `can_*`, router legacy `/api/users`, `main.jsx` monolítico y `domain-normalization.js`.

No los presentes como arquitectura objetivo. No deben ser fuente de autorización. Documenta dónde siguen activos y cuál es la ruta de retiro.

No reconstruyas funcionalidad inmobiliaria ni vuelvas a introducir roles/cargos organizacionales hardcodeados.
