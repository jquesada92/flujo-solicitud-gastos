# Changelog

## 2026-08-21

### Documentación / contrato 2.11.0

- se actualiza Constitución, README y prompt maestro al modelo vigente;
- se reescriben Specs 001–012 y se reemplaza Spec 006 por `006-group-scoped-role-access`;
- se agrega `docs/CURRENT_PRODUCT_CONTRACT.md`;
- se agrega `docs/FRONTEND_RUNTIME.md`;
- se alinean IAM, Configuración, Terminología, Seguimiento, Neon, FastAPI, Correo, Clasificación, Correcciones y Cierre;
- se eliminan de documentación normativa modelos, ramas y cadenas de migración ya sustituidos.

### Cargo

- contrato funcional: máximo un Cargo por Usuario;
- Cargo es metadato organizacional y no concede acceso;
- revisión Alembic `20260821_0003_single_user_position`.

## 2026-08-20

### IAM

- un Rol pertenece a un Grupo;
- un Usuario tiene máximo un Rol por Grupo;
- membresía de Grupo derivada;
- permisos solo en Roles;
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
