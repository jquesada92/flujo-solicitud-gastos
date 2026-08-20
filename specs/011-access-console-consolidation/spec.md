# Especificación funcional — Consolidación de Usuarios y Organigrama en Accesos

**Feature:** 011  
**Constitución:** 2.9.0

## Objetivo

Eliminar pantallas y entradas de navegación redundantes para la administración de identidades y estructura organizacional. **Accesos** pasa a ser la única superficie administrativa para Usuarios, Grupos, Roles, Permisos y Cargos/Posiciones.

La consolidación es de UX y arquitectura de navegación. No elimina el modelo de Usuario, Cargo/Posición, Grupo, Rol, Permiso ni sus relaciones persistidas.

## F-011-01 — Navegación administrativa única

Para un Administrador del sistema, el menú de Configuración no debe presentar entradas independientes llamadas **Usuarios**, **Personas** u **Organigrama**.

La navegación objetivo es:

```text
Configuración
├─ Accesos
├─ Áreas
├─ Reglas
└─ Auditoría / demás configuración técnica
```

Un usuario ordinario con `areas:manage` conserva únicamente la superficie de Áreas que le corresponda.

## F-011-02 — Accesos como fuente única de administración

`Configuración → Accesos` administra:

- creación, activación e inactivación de usuarios;
- datos básicos del usuario necesarios para acceso;
- Grupos y membresías;
- Roles y sus Permisos;
- Cargos/Posiciones;
- asignación de Cargos/Posiciones a Usuarios;
- Roles directos;
- Permisos directos;
- permisos efectivos y sus fuentes.

No se debe requerir una pantalla independiente de Usuarios u Organigrama para completar ninguna de esas operaciones.

## F-011-03 — Lectura de configuración

Cuando un actor tenga `config:read` pero no `config:manage`, cualquier consulta de Usuarios, Grupos, Roles, Permisos o Cargos debe resolverse desde la experiencia de **Accesos en modo solo lectura**.

No se deben reintroducir Usuarios u Organigrama como pantallas separadas para resolver el caso de solo lectura.

El backend sigue siendo la autoridad: `config:read` no autoriza mutaciones.

## F-011-04 — Compatibilidad transitoria

Código o vistas legacy de `people` / `organization` pueden permanecer temporalmente mientras se completa la migración, pero:

- no deben aparecer en navegación normal;
- no deben convertirse nuevamente en fuente de verdad administrativa;
- no deben duplicar lógica nueva;
- deben poder eliminarse en una limpieza posterior sin pérdida funcional.

Las APIs IAM y modelos persistidos no se eliminan por este cambio.

## F-011-05 — Terminología canónica de clasificación

La solicitud usa como contrato canónico:

```text
expense_area
expense_category
```

`expense_type` y `expense_subcategory` son nombres legacy y no deben volver a utilizarse como contrato nuevo de API, modelo o documentación funcional.

Área y Categoría continúan siendo dimensiones independientes y configurables.

## F-011-06 — No hardcode organizacional

La consolidación no autoriza por nombres como Presidente, Tesorero, Junta Directiva, Administración u otros. Cargos, Grupos, Roles y niveles de acceso continúan definidos como datos persistidos.

## F-011-07 — Navegación global desde Accesos

Mientras la consola de **Accesos** esté abierta, la barra superior del producto continúa siendo funcional.

Desde Accesos deben responder normalmente:

```text
Inicio
Solicitudes
Facturas
Auditoría
Configuración
Salir
```

Al seleccionar una pantalla de destino distinta de Accesos, la consola IAM debe cerrarse y la navegación del shell principal debe continuar en el mismo clic.

Esta regla también aplica cuando el destino solicitado ya era la pestaña subyacente activa antes de abrir Accesos. Por ejemplo: si Accesos se abrió desde Inicio, pulsar **Inicio** debe cerrar Accesos aunque el estado React subyacente ya sea `home`.

Abrir/cerrar el menú **Configuración** por sí solo no cierra Accesos; seleccionar una opción navegable dentro de ese menú sí debe cerrarlo.

La implementación no puede depender únicamente del cambio de estado React del shell, porque la consola de Accesos se monta mediante `#access-management` y debe retirar ese hash explícitamente al abandonar la consola.

## Seguridad

- `config:manage` continúa siendo system-only;
- `config:read` continúa siendo lectura sin mutaciones;
- ocultar entradas del menú no sustituye autorización backend;
- las cuentas técnicas continúan identificándose mediante `system_accounts`.

## Fuera de alcance

- eliminar tablas o relaciones IAM;
- rediseñar el motor de permisos efectivos;
- convertir Organigrama en un nuevo modelo persistido;
- modificar la política de aprobación o cierre de solicitudes;
- revertir `expense_area` / `expense_category` a terminología legacy.
