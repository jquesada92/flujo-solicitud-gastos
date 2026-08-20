# Especificación funcional — Herencia de permisos por Cargo y Grupo

**Feature:** 006  
**Constitución vigente:** 2.9.0

## Objetivo

Permitir que una organización configure acceso por estructura organizacional sin hardcodear nombres de Cargos o Grupos.

```text
Usuario → Cargo/Posición → Rol → Permiso
Usuario → Grupo          → Rol → Permiso
Usuario → Rol directo    → Permiso
Usuario → Permiso directo
```

Los caminos son acumulativos, sujetos a políticas system-only como `config:manage`.

## F-006-01 — Cargo puede heredar Roles

Cada Cargo/Posición activo puede tener cero o más Roles activos.

El sistema nunca autoriza con comparaciones de nombres de Cargo.

## F-006-02 — Grupo puede heredar Roles

Grupo → Rol → Permiso continúa siendo canónico.

## F-006-03 — Rol reutilizable

Un mismo Rol puede asociarse a múltiples Cargos, Grupos y Usuarios sin duplicar la definición del permiso.

## F-006-04 — Unión de permisos efectivos

Para usuario activo ordinario:

```text
effective = {requests:read}
          ∪ permisos directos
          ∪ roles directos
          ∪ roles por grupos activos
          ∪ roles por cargos activos
          - permisos system-only no aplicables
```

Actualmente `config:manage` es system-only; `config:read` y `areas:manage` sí pueden heredarse por estas fuentes.

## F-006-05 — Inactivos

Cargo inactivo o Rol inactivo no concede permisos.

## F-006-06 — Poblaciones de workflow

`users_with_permission(permission_code)` usa las mismas fuentes efectivas.

Un usuario con `requests:approve` por Cargo/Grupo es elegible salvo exclusiones intrínsecas, como solicitante propio o cuenta técnica en producción.

## F-006-07 — Origen visible

Accesos puede explicar:

```text
Cargo Tesorero → Aprobador
Grupo Junta Directiva → Aprobador
Rol directo: Comprador
Asignación directa
```

Los nombres son ejemplos de datos, no reglas.

## F-006-08 — Configuración gráfica vigente

En **Configuración → Accesos**:

- pestaña **Cargos** administra Roles heredados;
- pestaña **Grupos** administra Roles + Miembros;
- pestaña **Usuarios** administra Cargos, Grupos, Roles/permisos directos;
- permisos efectivos muestran sus fuentes.

La palabra **Usuarios** aquí identifica una pestaña interna de Accesos, no una pantalla independiente del menú Configuración. Feature 011 retiró la pantalla independiente de Usuarios/Organigrama.

## F-006-09 — Cuenta técnica

La política de `system_accounts` prevalece sobre asignaciones organizacionales accidentales.

Producción no adquiere permisos financieros por Cargo/Grupo/Rol.

## Migración 0004

`20260818_0004_position_role_inheritance.py` crea `position_roles` y migra una sola vez configuración legacy hacia IAM canónico.

Runtime posterior no consulta `can_approve`, `BOARD_CODES` o nombres de Cargo para decidir autorización.

## Relación con features posteriores

- Feature 009: `areas:manage`, `config:read`, `config:manage` system-only.
- Feature 010: notificaciones de Cargo/permisos efectivos.
- Feature 011: Accesos como superficie única de administración de Usuarios/IAM.

## Fuera de alcance

- DENY explícito por usuario;
- jerarquía Cargo padre/hijo;
- grupos anidados;
- scopes multi-tenant;
- autorización por nombre de Cargo;
- AccessProfile legacy como fuente autoritativa.
