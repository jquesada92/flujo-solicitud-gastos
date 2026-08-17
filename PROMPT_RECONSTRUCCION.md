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

Para usuarios operativos, default DENY si una capacidad no está permitida explícitamente.

### Prohibiciones

No autorices por:

- `UserRole.ADMIN`, `REQUESTER`, `APPROVER`, `VIEWER`;
- `can_request`, `can_approve`, `can_view`, `can_configure` como fuente de verdad;
- nombres de grupos/roles/cargos;
- emails fijos;
- IDs mágicos;
- listas como `BOARD_CODES`.

Los campos legacy pueden existir solo como puente de compatibilidad y deben derivarse de IAM, no al revés.

## 4. Cuenta técnica y política por ambiente

La cuenta creada con `ADMIN_*` debe quedar identificada como `TECHNICAL_ADMIN` en `system_accounts`.

La política se decide por `SystemAccount + ENVIRONMENT`, nunca por email/nombre/cargo/rol legacy.

### Producción

Solo cuando:

```env
ENVIRONMENT=production
```

la cuenta técnica queda restringida a:

```text
config:manage
requests:read
```

En producción debe ser imposible que ejerza:

```text
requests:create
requests:approve
requests:close
```

incluso si alguien intenta asignarlos accidentalmente mediante un grupo, rol o permiso directo. Tampoco debe participar en poblaciones financieras de aprobación o votación.

### No producción

Para cualquier `ENVIRONMENT` distinto de `production`, incluidos local, development/dev, test, staging y preview, la cuenta técnica debe recibir **todos los permisos atómicos activos del producto** para probar el sistema end-to-end.

Debe poder:

- crear/corregir solicitudes;
- consultar;
- aprobar y votar;
- entrar en poblaciones de aprobación/votación cuando corresponda;
- subir/reemplazar factura y cerrar;
- administrar configuración.

No persistas físicamente todos esos permisos solo para testing si puede resolverse como política ambiental; el mismo dataset debe volverse restrictivo al ejecutar con `ENVIRONMENT=production`.

`RENDER=true` puede activar validaciones fuertes de secretos y CORS, pero no debe activar por sí mismo la política funcional de producción. Separa `is_production_environment` de validaciones de runtime alojado.

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

La cuenta técnica debe aparecer identificada y la UI IAM debe poder explicar si un permiso proviene de política productiva o de acceso de prueba no-productivo.

No requieras editar archivos o variables para crear una estructura empresarial nueva.

## 6. Contrato del usuario autenticado

Expón los permisos efectivos actuales en:

```text
permission_codes
```

Durante la transición del frontend legacy deriva también:

```text
can_request   <- requests:create
can_approve   <- requests:approve
can_view      <- requests:read
can_configure <- config:manage
can_close     <- requests:close
```

Estos aliases nunca autorizan el backend.

El login debe calcular y serializar los permisos efectivos antes del primer render. `current_user()` debe volver a calcularlos por request para reflejar cambios inmediatos.

Migra progresivamente el frontend a `permission_codes`; retira bypasses visuales como `user.role === "ADMIN"` y `canClose={true}`.

## 7. Clasificación Área + Categoría

Área y Categoría son catálogos independientes con relación N:M configurable.

```text
Área: Administración, Operaciones, IT, Marketing
Categoría: Equipos, Servicios/Consultoría, Insumos, Licencias
```

Una categoría `Equipos` puede habilitarse para múltiples áreas sin duplicarse.

## 8. Solicitudes

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

## 9. Cotizaciones

SIMPLE exige proveedor, monto y soporte.

MULTI_QUOTE mantiene varias opciones. La población de votación se obtiene desde usuarios efectivos con `requests:approve`, excluyendo al solicitante.

- Producción: cuenta técnica excluida de permisos financieros.
- No producción: cuenta técnica puede participar para pruebas si no queda excluida por otra regla del flujo.

Congela/versiona los participantes de cada ronda. No inventes reglas de quorum/empate no especificadas.

## 10. Aprobaciones

Los participantes se seleccionan por permisos/políticas persistidas, nunca por cargo hardcodeado.

La Constitución vigente define la regla funcional objetivo de quorum y mayoría. Si el motor legacy todavía difiere, documenta la deuda y no afirmes que está resuelta por cambios IAM.

## 11. Cierre y factura

`APPROVED` no significa `CLOSED`.

Subir/reemplazar factura y cerrar requiere `requests:close`.

- Producción: cuenta técnica debe recibir 403.
- No producción: cuenta técnica puede cerrar para pruebas end-to-end.

Conserva versiones anteriores de facturas y registra motivo/actor/timestamp al sustituir.

## 12. Arquitectura FastAPI

Usa:

```text
app/
├── api/
├── core/
├── models/
├── schemas/
├── services/
├── application.py
└── main.py
```

Reglas:

- Pydantic Settings centralizado.
- `get_db()` entrega una sesión por request y siempre la cierra.
- modelos SQLAlchemy fuera de routers.
- schemas reutilizables fuera de routers.
- response models explícitos para respuestas sensibles.
- dependencias FastAPI para autorización.
- `lifespan` nunca ejecuta DDL/backfills/seeds de negocio.
- Alembic para migraciones versionadas.
- SQLAlchemy síncrono: rutas con DB/filesystem bloqueante deben ser `def` o hacer offload explícito.

## 13. Passwords y JWT

- Argon2 mediante `pwdlib.PasswordHash.recommended()` para hashes nuevos.
- Compatibilidad temporal con PBKDF2 legacy.
- Login PBKDF2 exitoso migra el hash a Argon2.
- JWT con `sub`, versión de sesión, `iat`, `exp`.
- timeout de inactividad.
- cambios sensibles pueden revocar sesiones.

## 14. Documentos

Admite PDF/JPEG/PNG/WEBP. Valida MIME, firma real, tamaño, cuota total y nombre interno impredecible. El disco es privado y la descarga pasa por autorización backend.

## 15. Correo

Centraliza configuración en Settings. Producción usa preferiblemente API HTTPS de Brevo. Mantén console/SMTP para desarrollo si existe. Branding base neutral.

## 16. Migraciones, Docker y despliegue

No uses `Base.metadata.create_all()` ni `migrate_schema()` en lifespan productivo.

Secuencia canónica:

```text
alembic upgrade head
python -m scripts.bootstrap_admin
uvicorn app.application:app
```

No ejecutes el bootstrap como `python scripts/bootstrap_admin.py`.

Portabilidad:

- `*.sh text eol=lf` en `.gitattributes`;
- normalización defensiva CRLF dentro de imagen;
- healthcheck real antes de Nginx;
- CI valida entrypoint e import de `scripts.bootstrap_admin`.

Producción debe declarar explícitamente:

```env
ENVIRONMENT=production
```

No uses ese valor en un entorno donde se pretenda probar todas las funciones con la cuenta técnica.

## 17. Testing

Usa tests unitarios y `FastAPI TestClient`.

Matriz IAM mínima:

- no-producción: admin técnico obtiene todos los permisos activos;
- no-producción: login expone `permission_codes` completos y `can_close=true` si el permiso está activo;
- no-producción: admin técnico puede entrar en población `requests:approve`;
- producción: admin técnico obtiene solo config/read;
- producción: asignarle close accidentalmente sigue resultando DENY;
- producción: endpoint de cierre devuelve 403;
- producción: admin técnico queda fuera de población de aprobación;
- usuario sin config obtiene 403 en IAM;
- Grupo→Rol→Permiso cambia acceso inmediatamente;
- permiso directo es aditivo;
- rol técnico no se edita desde UI.

CI ejecuta Python compile, backend tests, frontend build y builds/smoke tests Docker.

## 18. Seguridad

- backend authoritative;
- secretos fuera del frontend/logs/repositorio;
- CORS explícito;
- rate limiting diferenciado;
- ORM/consultas parametrizadas;
- archivos privados;
- default deny para usuarios operativos;
- no bypass por `UserRole.ADMIN`;
- no autorización por cargo;
- política ampliada de cuenta técnica únicamente fuera de producción y basada en ambiente.

## 19. Auditoría

Eventos significativos deben conservar actor, tiempo, entidad, cambios y motivo. La evolución del IAM debe incorporarse a auditoría para que cambios de roles/grupos/permisos no sean silenciosos.

## 20. Documentación obligatoria

Un cambio no está terminado hasta revisar y actualizar cuando aplique Constitución, spec, plan, criterios de aceptación, README, este prompt, documentación técnica/funcional, terminología, HISTORY, CHANGELOG y PR.

## 21. Deuda permitida solo si está explícita

Durante la transición pueden existir `UserRole`, `can_*`, router legacy `/api/users`, `main.jsx` monolítico y `domain-normalization.js`.

No los presentes como arquitectura objetivo. No deben ser fuente de autorización.

No reconstruyas funcionalidad inmobiliaria ni vuelvas a introducir roles/cargos organizacionales hardcodeados.
