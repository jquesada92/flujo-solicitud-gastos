# Inicio, acciones pendientes y Seguimiento

## Separación de responsabilidades

### Inicio = mi trabajo

`HomeDashboard` consume `/api/expenses/dashboard` y muestra datos personales:

- acciones que esperan al usuario;
- solicitudes propias en proceso;
- métricas de sus solicitudes;
- modal de acción contextual.

### Seguimiento = trabajo del equipo

`user-tracking.jsx` consume `/api/organization/groups` y muestra Grupos, miembros, Roles y pendientes. Es informativo y no expone controles de IAM.

## Acciones pendientes

```text
APPROVAL_DECISION
QUOTATION_VOTE
CORRECT_REQUEST
CLOSE_REQUEST
```

Una acción existe solo si el backend confirma que sigue vigente.

### APPROVAL_DECISION
`requests:approve` + aprobación PENDING asignada + solicitud en `PENDING_APPROVAL`.

### QUOTATION_VOTE
`requests:approve` + invitación vigente + solicitud en `QUOTATION_VOTING`.

La invitación es una instantánea de la ronda. Después de votar la acción
permanece como **Votar o cambiar voto**. Solo desaparece cuando la factura cierra
la ronda; un empate la mantiene abierta para que un participante cambie su voto.
Un gasto directo nunca crea `QUOTATION_VOTE` ni otra acción pendiente.

### CORRECT_REQUEST
Solicitud propia en `NEEDS_REVISION`.

### CLOSE_REQUEST
Solicitud `SIMPLE` en `APPROVED`, o `MULTI_QUOTE` en `QUOTATION_VOTING` con
líder único y actor habilitado. Con política, quórum habilita cierre anticipado
solo al Solicitante; sin política deben votar todos y entonces aplican
Solicitante, `system_accounts` o delegado activo. El endpoint revalida población,
quórum y ausencia de empate antes de persistir la factura.

### Monto de solicitudes con múltiples cotizaciones

La columna **Monto** usa `tracking_amount` como valor operativo. Sin votos es el
máximo presentado; con un líder único es el monto de esa opción; si hay empate
es el máximo de todas las opciones. Este dato no selecciona proveedor ni altera
el monto financiero canónico de la solicitud.

## Seguimiento de usuarios

KPIs:

```text
miembros activos
usuarios con pendientes
acciones pendientes totales
```

Por Grupo se muestra:

```text
nombre/descripcion
miembros visibles
Rol(es) del miembro en ese Grupo
pending_actions por miembro
total del Grupo
```

La UI permite buscar por usuario, Grupo o Rol y filtrar solo miembros con pendientes.

## Privacidad y autorización

Seguimiento requiere sesión. No contiene controles de edición y no sustituye Accesos.

## Refresco

Inicio carga al montar/cambiar `refreshKey`. Seguimiento carga al montar y cuando el usuario pulsa Recargar. Ninguna vista usa polling continuo.

Los gastos directos no forman parte de las métricas, estados o pendientes de
Solicitudes. Su listado privado existe en `GET /api/direct-expenses`; la pantalla
actual de **Registro directo** confirma el ID creado, pero no renderiza ese
listado.
