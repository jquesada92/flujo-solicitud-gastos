# Spec 022 — Registro directo de gastos sin aprobación

**Estado:** Implementada  
**Constitución:** 2.30.0
**Fecha:** 2026-08-28

## Objetivo

Permitir que un Solicitante registre proveedor, ítem, monto y factura cuando una
banda configurada determina que el gasto no requiere aprobación, sin crear una
Solicitud, una fila `Expense` ni artefactos de workflow.

Esta Spec amplía las bandas y la precedencia de la Spec 021. No sustituye los
flujos `SIMPLE` o `MULTI_QUOTE`: define un registro final independiente para la
modalidad `NO_APPROVAL`.

## Configuración

1. `ApprovalPolicy.approval_mode` admite `NO_APPROVAL` además de `ANY`,
   `MAJORITY` y `ALL`.
2. Una regla `NO_APPROVAL` pertenece a un Área concreta o a `ALL` y usa la misma
   semántica `(min_amount,max_amount]`, precedencia y validación de overlap de la
   Spec 021.
3. La prohibición de overlap considera todas las reglas activas del mismo scope,
   independientemente de su modalidad.
4. Una regla `NO_APPROVAL` debe guardar vacíos `approver_role_ids` y
   `approver_group_ids`. No selecciona personas, no concede
   `requests:approve` y no calcula quórum.
5. Una regla `ANY`, `MAJORITY` o `ALL` conserva al menos un target válido de Rol
   o Grupo conforme a la Spec 021.

## Pantalla y elegibilidad

La navegación privada muestra **Registro directo** únicamente a Usuarios con
`requests:create`. La pantalla **Gasto sin aprobación** obtiene del backend las
bandas `NO_APPROVAL` activas que puede usar como orientación y solicita:

```text
Área
Proveedor
Ítem / descripción
Monto
Factura
```

La validación frontend de `(min,max]` no autoriza ni congela una política. El
`POST` vuelve a comprobar el Área activa, el monto positivo, la precedencia del
Área concreta sobre `ALL` y la existencia de una regla `NO_APPROVAL` aplicable.
Un cambio concurrente de configuración puede hacer que una banda antes mostrada
deje de ser válida y el backend debe rechazar el registro.

Si el Usuario intenta crear una Solicitud con un Área y un monto que corresponden
a una banda `NO_APPROVAL`, el formulario conserva el borrador y presenta: **El área y
el monto seleccionados no requieren un proceso de aprobación. Usa Registro
directo para registrar el gasto y adjuntar la factura.** El aviso no expone
rutas internas y señala de forma visual y accesible el botón **Registro
directo**, sin navegar automáticamente ni marcar esa pantalla como activa antes
de que el Usuario la elija. En la banda móvil desplazable, el control se lleva a
la porción visible sin mover el foco ni ocultar el aviso.

### Layout para teléfonos y tabletas

La pantalla conserva todos los datos y acciones sin scroll horizontal:

- entre 320 y 720 px, introducción, campos y lista de bandas se apilan en una
  columna;
- hasta 440 px, cada banda apila nombre/descripción y rango;
- en 768, 820 y 1024 px puede usar dos columnas para formulario y bandas siempre
  que cada control siga completo y legible;
- inputs, selects y botones tienen al menos 44 px de alto y foco visible;
- textos, nombres de archivo y rangos extensos envuelven sin salir del viewport.

La aceptación visual específica se ejecuta en 320, 360, 390, 412, 440, 600,
640, 768, 820 y 1024 px. El build y una prueba estática no sustituyen esta
comprobación de navegador.

## Persistencia independiente

Un alta válida crea un `DirectExpense` en `direct_expenses` con:

```text
record_id / display_id
expense_area
supplier
item_description
amount
requester_user_id / requester_analytics_id / requester_email
invoice_original_name / invoice_stored_name / invoice_content_type / invoice_size
approval_policy_id
created_at
```

`approval_policy_id` conserva identidad histórica sin FK destructiva. El alta
no crea `Expense`, `Approval`, `QuotationVotingInvitation`, voto, acción
pendiente, `flow_id` ni estado de Solicitud. El gasto directo tampoco entra en
corrección, cancelación, delegación o cierre de Solicitudes.

La factura es obligatoria, privada y admite PDF, JPEG, PNG o WEBP de hasta
10 MB, con validación de firma, tipo y tamaño. La escritura del archivo y el
commit de la fila forman una sola unidad: cualquier fallo elimina el archivo
parcial y revierte la fila.

## Autorización y consulta

- crear, consultar bandas elegibles y acceder a la pantalla requiere
  `requests:create`;
- un Usuario ordinario lista únicamente sus propios registros;
- solo el autor puede descargar la factura de su registro;
- `system_accounts` puede listar todos y descargar cualquier factura;
- conocer `record_id` no amplía acceso;
- la factura siempre se sirve por FastAPI autorizado, nunca como archivo
  público.

API canónica:

```text
GET  /api/direct-expenses/eligible-policies
POST /api/direct-expenses
GET  /api/direct-expenses
GET  /api/direct-expenses/{record_id}/invoice
```

## Persistencia física

La revisión `20260828_0013` se agrega sobre `20260827_0012`, crea
`direct_expenses` dentro de `DATABASE_SCHEMA` y no modifica revisiones
históricas. SQLite cubre lógica aislada; la existencia del schema, FK, checks e
índices requiere validación adicional contra PostgreSQL local de Compose.
