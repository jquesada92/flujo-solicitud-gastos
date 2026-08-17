# Historial funcional y técnico

## 2026-08-17 — IAM configurable y segregación de la cuenta técnica

### Decisión

Se abandona `UserRole`/`can_*` como fuente de autorización y se adopta un modelo IAM persistido:

```text
Usuario → Grupo → Rol → Permiso
       ↘ Rol directo
       ↘ Permiso directo
       ↘ Cargo descriptivo
```

Los cinco permisos iniciales son:

- `requests:read`;
- `requests:create`;
- `requests:approve`;
- `requests:close`;
- `config:manage`.

Los Grupos, Roles, Cargos, membresías y asignaciones son configurables desde la interfaz. Los nombres de estructuras organizacionales no se utilizan en condiciones de autorización.

### Cuenta técnica

La cuenta de bootstrap del administrador del sistema queda identificada mediante `system_accounts` y restringida defensivamente a:

- `config:manage`;
- `requests:read`.

No puede crear, aprobar ni cerrar solicitudes aunque se le asigne accidentalmente un permiso financiero.

### Motivo

El administrador técnico de la plataforma no debe formar parte del proceso financiero. Además, el producto debe soportar empresas con estructuras distintas sin despliegues de código.

---

## 2026-08-17 — Hardening FastAPI

### Decisiones

- configuración centralizada con Pydantic Settings;
- nuevos hashes Argon2 mediante `pwdlib`;
- migración transparente de PBKDF2 legacy durante login;
- Alembic como mecanismo de migración;
- DDL/backfills retirados del lifespan;
- `app/main.py` reducido a alias de `app.application`;
- modelos de clasificación movidos fuera del router;
- rutas canónicas de documentos/cierre con `def` porque SQLAlchemy/filesystem son síncronos;
- `FastAPI TestClient` agregado para la matriz IAM;
- application factory y routers canónicos registrados antes de compatibilidad legacy.

### Despliegue Render

Se evaluó `preDeployCommand`. Aunque Render lo recomienda para migraciones, está asociado a servicios pagos. Para mantener compatibilidad con un despliegue económico, el contenedor ejecuta Alembic + bootstrap antes de `uvicorn` mediante `scripts/start.sh`. En un futuro despliegue con múltiples réplicas, la migración debe moverse a una etapa única de release/pre-deploy.

---

## 2026-08-17 — Consola gráfica de Accesos

Se agrega una consola modular `Configuración → Accesos` para administrar:

- Usuarios;
- Grupos;
- Roles;
- Permisos;
- Cargos;
- membresías;
- roles/permisos directos;
- permisos efectivos.

La consola consume `/api/iam/*` y no depende de los perfiles/cargos hardcodeados del frontend monolítico.

---

## 2026-08-17 — Deuda funcional mantenida explícitamente

El refactor IAM/FastAPI no modifica silenciosamente semánticas de negocio no definidas para esta feature.

Pendientes separados:

- fórmula exacta del motor de aprobación para cumplir la Constitución 2.2.0;
- regla de quorum/empate de votación de cotizaciones;
- retiro completo de `UserRole`, `can_*`, `/api/users` legacy y ramas legacy de `api/expenses.py`;
- modularización completa de `frontend/src/main.jsx`.

---

## 2026-08-17 — Documentación como parte del Definition of Done

### Decisión

Se establece como regla transversal que ningún cambio funcional o técnico se considera terminado si deja desactualizadas las fuentes documentales afectadas.

Se incorporan como artefactos obligatorios de gobierno:

- `.specify/memory/constitution.md`;
- especificaciones por feature en `specs/`;
- planes técnicos;
- criterios de aceptación;
- `docs/DOCUMENTATION_POLICY.md`.

Cada feature debe revisar además README, prompt maestro, terminología, historial y changelog según corresponda.

### Motivo

El proyecto está evolucionando desde un MVP con términos y estructuras legacy. Sin una regla explícita de sincronización, el código puede avanzar mientras prompts, README o criterios de aceptación continúan reconstruyendo comportamiento obsoleto.

La discrepancia código-documentación pasa a considerarse un defecto de la feature.

---

## 2026-08-17 — Terminología Usuario / Usuarios

El término canónico para el dominio de cuentas es **Usuario / Usuarios**. La UI no debe utilizar **Persona / Personas** como nombre del módulo de administración de cuentas.

---

## 2026-08-17 — Clasificación Área + Categoría

### Decisión funcional

- **Área**: parte de la organización asociada al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.

Área y Categoría son catálogos independientes y una Categoría puede estar disponible para múltiples Áreas.

### Compatibilidad histórica

- `expenses.expense_type` → Área;
- `expenses.expense_subcategory` → Categoría;
- `expense_categories` → almacenamiento legacy de Áreas;
- `expense_subcategories` → puente de compatibilidad;
- `expense_category_catalog` → catálogo canónico de Categorías;
- `expense_area_categories` → relaciones canónicas.

---

## 2026-08-17 — Retiro del dominio inmobiliario

Se inició el retiro del dominio específico de propiedad horizontal del núcleo de la aplicación. Se retiraron del modelo activo conceptos como `Apartment`, `UserApartment`, `ApartmentChangeEvent`, `OwnershipRole`, `PersonType`, `apartment_number` y endpoints específicos de apartamentos.

La eliminación física de datos legacy requiere respaldo previo.
