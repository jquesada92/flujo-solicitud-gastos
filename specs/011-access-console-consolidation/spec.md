# Especificación funcional — Consolidación de Usuarios y Organigrama en Accesos

**Feature:** 011  
**Constitución:** 2.9.0

## Objetivo

Eliminar superficies redundantes para administración de identidades y estructura organizacional. **Accesos** pasa a ser la única superficie administrativa para Usuarios, Grupos, Roles, Permisos y Cargos/Posiciones.

La consolidación es de UX, navegación y fuente de verdad administrativa. No elimina el modelo persistido de Usuario, Cargo/Posición, Grupo, Rol, Permiso ni sus relaciones.

## Actores

### Administrador del sistema

Cuenta protegida identificada mediante `system_accounts`. Puede administrar Accesos y demás configuración técnica según los permisos/políticas vigentes.

### Visor de configuración

Usuario ordinario con `config:read`. Puede consultar Configuración en modo solo lectura, pero no mutarla.

### Gestor de Áreas

Usuario con `areas:manage`. Puede administrar Área + Categoría sin obtener administración IAM.

## F-011-01 — Navegación administrativa única

Para el Administrador del sistema, Configuración no debe presentar entradas independientes llamadas **Usuarios**, **Personas** u **Organigrama**.

Navegación objetivo:

```text
Configuración
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría / demás configuración técnica
```

## F-011-02 — Accesos como fuente única

`Configuración → Accesos` administra:

- creación de Usuarios;
- activación/inactivación;
- datos básicos necesarios para acceso;
- Grupos y membresías;
- Roles;
- Permisos;
- Cargos/Posiciones;
- Cargos asignados a Usuarios;
- Roles heredados por Grupo;
- Roles heredados por Cargo;
- Roles directos;
- Permisos directos;
- permisos efectivos y sus fuentes.

Ninguna de estas operaciones debe requerir una pantalla independiente de Usuarios u Organigrama.

## F-011-03 — Lectura de configuración

Cuando el actor tenga `config:read` pero no administración técnica:

- Usuarios, Grupos, Roles, Permisos y Cargos se consultan desde **Accesos en modo solo lectura**;
- Áreas se consultan sin mutación salvo que además tenga `areas:manage`;
- Reglas y Auditoría se consultan según el contrato de `config:read`;
- no se reintroducen Usuarios/Personas u Organigrama como pantallas separadas.

`config:read` no autoriza mutaciones.

## F-011-04 — Gestión de Áreas independiente

Un actor con `areas:manage` sin `config:read` obtiene únicamente la superficie de Área + Categoría que le corresponde.

`areas:manage` no concede administración de Accesos, Usuarios, Roles, Permisos, Cargos, Reglas o Auditoría técnica.

## F-011-05 — Compatibilidad transitoria

Código/vistas legacy de `people` / `organization` pueden permanecer temporalmente mientras se completa la modularización, pero:

- no aparecen en navegación normal;
- no son fuente de verdad administrativa;
- no duplican lógica nueva;
- deben poder eliminarse posteriormente sin pérdida funcional.

Las APIs IAM y modelos persistidos no se eliminan por esta feature.

## F-011-06 — Terminología canónica de clasificación

La solicitud usa como contrato canónico:

```text
expense_area
expense_category
```

`expense_type` y `expense_subcategory` son aliases legacy y no deben volver a utilizarse como contrato nuevo de API, ORM, DB o documentación funcional.

Alembic `20260819_0008_expense_area_category_columns.py` representa la transición física vigente.

## F-011-07 — No hardcode organizacional

La consolidación no autoriza por nombres como Presidente, Tesorero, Junta Directiva, Administración u otros.

Cargos, Grupos, Roles, Permisos y niveles de acceso continúan definidos como datos persistidos.

## F-011-08 — Navegación global desde Accesos

Mientras la consola de **Accesos** esté abierta, la barra superior del producto continúa siendo funcional.

Deben responder normalmente:

```text
Inicio
Solicitudes
Facturas
Auditoría
Configuración
Salir
```

Al seleccionar una pantalla distinta de Accesos:

1. se retira `#access-management`;
2. se desmonta la consola IAM;
3. la navegación del shell continúa en el mismo clic.

Esto también aplica si el destino ya era la pestaña React subyacente activa antes de abrir Accesos.

Ejemplo:

```text
Inicio
→ abrir Accesos
→ pulsar Inicio
→ Accesos se cierra y queda Inicio visible
```

Abrir/cerrar solamente el dropdown **Configuración** no cierra Accesos. Seleccionar una opción navegable dentro del dropdown sí.

La implementación no puede depender únicamente de que cambie el estado React del shell.

## F-011-09 — Integración con el shell legacy

Mientras Accesos se monte por hash, el bridge dedicado es:

```text
frontend/src/access-navigation-bridge.js
```

Debe cargarse antes de `main.jsx` y manejar la salida desde la topbar en capture phase.

Los bridges temporales deben ser fail-fast cuando transformen source legacy y no depender de indentación exacta o finales de línea específicos.

## F-011-10 — Migraciones y compatibilidad de rama

La rama activa debe contener todas las revisiones Alembic que la base pueda referenciar.

Cadena vigente:

```text
0000 → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008
```

Si PostgreSQL está en `0008`, una rama sin `0008` no es compatible.

No se debe usar `alembic stamp` para ocultar una discrepancia de esquema. Debe sincronizarse la rama/migración correcta y luego validar `alembic current` / `alembic heads`.

## F-011-11 — Documentación como parte del entregable

La feature no está completa hasta sincronizar:

```text
.specify/memory/constitution.md
specs/011-access-console-consolidation/spec.md
specs/011-access-console-consolidation/plan.md
specs/011-access-console-consolidation/checklists/acceptance.md
README.md
PROMPT_RECONSTRUCCION.md
docs/CONFIGURATION_ACCESS.md
docs/IAM_MODEL.md
docs/CLASSIFICATION_MODEL.md
docs/TERMINOLOGY.md
docs/FASTAPI_ARCHITECTURE.md
docs/README.md
docs/DOCUMENTATION_POLICY.md
docs/HISTORY.md
CHANGELOG.md
```

## Seguridad

- `config:manage` continúa siendo system-only;
- `config:read` continúa siendo lectura sin mutaciones;
- `areas:manage` no concede IAM técnico;
- ocultar entradas del menú no sustituye autorización backend;
- las cuentas técnicas continúan identificándose mediante `system_accounts`;
- ninguna ruta sensible confía exclusivamente en estado del frontend.

## Escenarios de aceptación

### Escenario A — System Admin

```text
Dado un System Admin
Cuando abre Configuración
Entonces ve Accesos, Áreas, Reglas y Auditoría según política
Y no ve Usuarios/Personas ni Organigrama como entradas independientes
```

### Escenario B — Crear usuario

```text
Dado un System Admin dentro de Accesos
Cuando crea un Usuario
Entonces no necesita abandonar Accesos ni abrir una pantalla Usuarios separada
```

### Escenario C — `config:read`

```text
Dado un usuario con config:read
Cuando abre Accesos
Entonces puede consultar Usuarios/Grupos/Roles/Permisos/Cargos
Pero no puede persistir mutaciones
```

### Escenario D — navegación desde Accesos

```text
Dado que Accesos está abierto
Cuando el usuario pulsa Solicitudes
Entonces #access-management se elimina
Y Solicitudes queda visible en el mismo clic
```

### Escenario E — misma pestaña subyacente

```text
Dado que Accesos fue abierto desde Inicio
Cuando el usuario pulsa Inicio
Entonces Accesos se cierra aunque React ya estuviera en home
```

### Escenario F — dropdown Configuración

```text
Dado que Accesos está abierto
Cuando el usuario solo abre/cierra Configuración
Entonces permanece en Accesos
Cuando selecciona otra pantalla del dropdown
Entonces Accesos se cierra y navega
```

### Escenario G — clasificación

```text
Dado código nuevo de solicitud
Entonces usa expense_area y expense_category
Y no serializa expense_type/expense_subcategory como contrato canónico
```

## Fuera de alcance

- eliminar tablas o relaciones IAM;
- rediseñar el motor de permisos efectivos;
- convertir Organigrama en un nuevo modelo persistido;
- modificar política de aprobación/cierre;
- revertir `expense_area` / `expense_category`;
- eliminar todo el shell legacy en esta feature.
