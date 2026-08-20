# Plan de implementación — Configuración técnica vs gestión de Áreas

**Feature:** 009  
**Constitución vigente:** 2.9.0  
**Nota:** Feature 011 evolucionó la navegación de esta feature consolidando Usuarios/Organigrama dentro de Accesos.

## 1. IAM

- mantener `areas:manage` como permiso organizacional configurable;
- mantener `config:manage` en `SYSTEM_ONLY_PERMISSION_CODES`;
- mantener `config:read` como permiso de lectura configurable;
- para usuarios ordinarios, retirar `config:manage` de la unión efectiva aunque existan relaciones legacy;
- resolver `system_accounts` conforme a la política de ambiente.

Producción vigente del System Admin:

```text
requests:read + areas:manage + config:read + config:manage
```

## 2. Identidad técnica de sesión

- `UserOut.is_system_account` se calcula desde `system_accounts`;
- `permission_codes` expone permisos efectivos;
- login y `/auth/me` entregan ambos;
- nunca inferir identidad técnica por `role`, `title`, email o nombre.

## 3. API de Áreas

Mutaciones de `/api/areas` usan `areas:manage`.

`config:read` puede permitir lectura de configuración según el contrato actual, pero no mutación.

La lectura activa necesaria para crear/consultar solicitudes permanece disponible a usuarios autenticados.

## 4. Configuración técnica

Estado vigente:

```text
Accesos        → escritura: System Admin / lectura: config:read
Áreas          → escritura: areas:manage / lectura: configuración autorizada
Reglas         → escritura técnica / lectura config:read
Auditoría      → lectura según config:read/política técnica
```

Usuarios/Personas y Organigrama no son pantallas independientes después de Feature 011.

## 5. Frontend

Bridge/capacidades del shell:

```text
isSystemAdmin = user.is_system_account === true
canReadConfiguration = isSystemAdmin OR permission_codes includes config:read
canManageAreas = isSystemAdmin OR permission_codes includes areas:manage
canConfigure = isSystemAdmin
```

Visibilidad vigente:

```text
Accesos      → canReadConfiguration
Áreas        → canReadConfiguration OR canManageAreas
Reglas/Audit → canReadConfiguration
```

Accesos editable se reserva al System Admin; `config-readonly.js` protege modo de lectura.

Feature 011 protege además la navegación desde `#access-management` mediante `access-navigation-bridge.js`.

## 6. Migraciones

```text
0006 → areas:manage + Gestor de áreas
0007 → config:read + Visor de configuración
0008 → expense_area / expense_category físicos
```

No asignar capacidades runtime por nombres organizacionales.

## 7. Configuración operativa

El Administrador del sistema utiliza **Accesos** para asociar Roles a Grupos/Cargos/Usuarios.

Ejemplos de nombres de cliente pueden existir como datos, pero nunca como lógica backend.

## 8. Pruebas

Backend:

- `areas:manage` ordinario funciona;
- `areas:manage` no administra IAM;
- `config:manage` ordinario se ignora;
- `config:read` permite lectura y no escritura;
- System Admin conserva administración técnica;
- sesión expone `is_system_account`.

Frontend:

- Accesos usa `canReadConfiguration` para visibilidad;
- no existen Usuarios/Organigrama como entradas independientes;
- Áreas respeta `areas:manage`;
- modo read-only bloquea mutaciones;
- integración de navegación de Accesos se delega a contratos de Feature 011.

## 9. Gates locales

```text
cd backend
alembic heads
alembic current
python -m unittest discover -s tests -v

cd ../frontend
npm run build
```

Además validar manualmente los perfiles de acceso y la navegación descrita por Feature 011.

## 10. Relación con Feature 011

Feature 009 sigue siendo la fuente de la separación **config técnica vs Área/Categoría**. Feature 011 es la fuente vigente para la **superficie de navegación de Accesos**.

No reintroducir:

```text
Configuración → Usuarios
Configuración → Organigrama
```
