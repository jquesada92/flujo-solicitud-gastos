# Plan de implementación — Configuración técnica vs gestión de Áreas

**Feature:** 009  
**Constitución:** 2.8.0

## 1. IAM

- añadir `areas:manage` al catálogo de permisos activos;
- reservar `config:manage` como `SYSTEM_ONLY_PERMISSION_CODES`;
- para usuarios ordinarios, eliminar permisos system-only de la unión efectiva aunque existan relaciones legacy;
- para `system_accounts`, resolver permisos conforme a la política del ambiente;
- en producción conservar `requests:read + areas:manage + config:manage` para la cuenta técnica;
- fuera de producción conservar todos los permisos atómicos activos para testing E2E.

## 2. Identidad técnica de sesión

- extender `UserOut` con `is_system_account`;
- calcularlo en backend desde `system_accounts`;
- devolverlo en login y `/auth/me`;
- no inferirlo por `role`, `title`, email o nombre.

## 3. API de Áreas

Cambiar mutaciones/configuración de `/api/areas` para usar `areas:manage`:

```text
POST   /api/areas
PATCH  /api/areas/{id}
POST   /api/areas/categories
PATCH  /api/areas/categories/{id}
POST   /api/areas/{id}/categories
POST   /api/areas/{id}/categories/{category_id}
DELETE /api/areas/{id}/categories/{category_id}
```

`include_inactive=true` solo expone inactivos al actor con `areas:manage`.

La lectura activa necesaria para crear/consultar solicitudes permanece disponible al usuario autenticado.

## 4. Configuración técnica

Mantener Usuarios/IAM/Organigrama/Reglas/Auditoría detrás de `config:manage`.

Como el resolver hace `config:manage` efectivo solo para `system_accounts`, un usuario ordinario no puede cruzar esta frontera aunque tenga una asignación histórica.

## 5. Frontend

Mientras `main.jsx` siga legacy, Vite aplica un bridge explícito:

```text
isSystemAdmin = user.is_system_account === true
canManageAreas = isSystemAdmin OR permission_codes includes areas:manage
```

Visibilidad:

```text
Usuarios       → isSystemAdmin
Organigrama    → isSystemAdmin
Accesos        → isSystemAdmin
Áreas          → canManageAreas
Reglas/Audit   → isSystemAdmin
```

El menú Configuración existe si hay al menos una opción visible.

`iam-admin.jsx` solo inyecta **Accesos** cuando el menú está marcado `data-system-admin=true`.

Mientras esa inyección siga implementada mediante el bridge Vite temporal, la transformación debe localizar el guard de `injectAccessMenu()` mediante una expresión regular tolerante a espacios y finales de línea LF/CRLF. Debe exigir exactamente una coincidencia y abortar el build si encuentra cero o múltiples guards; no puede depender de una secuencia literal de indentación/saltos de línea.

## 6. Migración

Crear `0006` después de `0005`:

- upsert `areas:manage`;
- actualizar descripción de `config:manage`;
- crear Rol `area-manager / Gestor de áreas`;
- asociar `areas:manage`;
- no asignar a grupos/cargos por nombre.

## 7. Configuración operativa posterior

Después de aplicar `0006`, el Administrador del sistema entra en **Accesos** y asocia el Rol **Gestor de áreas** a los Grupos o Cargos definidos por la organización.

Ejemplo de configuración de cliente, no regla del producto:

```text
Grupo Administración → Gestor de áreas
Grupo Junta Directiva → Gestor de áreas
```

Estos nombres no aparecen en lógica backend ni migración.

## 8. Pruebas

Backend:

- `areas:manage` directo funciona para usuario ordinario;
- usuario con `areas:manage` no administra IAM;
- `config:manage` asignado a usuario ordinario se ignora;
- System Admin conserva configuración técnica;
- `/auth/me` expone `is_system_account`;
- producción limita la cuenta técnica a read/areas/config.

Frontend contract:

- Usuarios/Organigrama/Accesos usan system identity;
- Áreas usa `areas:manage`;
- Accesos no se inyecta a menú no técnico;
- el bridge de Accesos es tolerante a whitespace/LF/CRLF, conserva fail-fast y no usa `replaceRequired()` con un bloque multilinea literal para ese guard.

Migración:

- un solo head `0006`;
- `0006 → 0005`;
- no contiene asignaciones a nombres organizacionales.

## 9. Gates locales

Mientras GitHub Actions no tenga cuota:

```text
python -m unittest discover -s tests -v
npm run build
docker compose build --no-cache
docker compose up -d
```

No hacer deploy productivo de `0006` hasta completar el smoke local/PostgreSQL y la validación manual del menú.
