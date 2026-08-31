# Aceptación 022

- [x] `NO_APPROVAL` usa bandas `(min,max]`, precedencia Área sobre `ALL` y la misma protección de overlap de la Spec 021.
- [x] Una regla `NO_APPROVAL` guarda targets vacíos y una modalidad con ronda exige al menos un Rol/Grupo válido.
- [x] **Registro directo** solo aparece y responde para Usuarios con `requests:create`.
- [x] Una creación de Solicitud dentro de una banda `NO_APPROVAL` conserva el borrador, muestra una guía sin rutas internas y mantiene visible/resaltado **Registro directo** sin navegar automáticamente.
- [x] El formulario exige Área, proveedor, ítem/descripción, monto positivo y factura.
- [x] En teléfonos hasta 720 px, introducción, campos y bandas se apilan sin perder información; hasta 440 px cada banda también apila su rango.
- [x] En tabletas de 768, 820 y 1024 px, las dos columnas permanecen legibles y todos los controles táctiles miden al menos 44 px.
- [x] FastAPI revalida la política aplicable; la selección o validación frontend no concede elegibilidad.
- [x] El límite mínimo es excluyente, el máximo es inclusivo y un hueco o monto fuera de banda se rechaza.
- [x] El alta crea `DirectExpense` y no crea `Expense`, aprobación, invitación, voto, acción pendiente ni estado de Solicitud.
- [x] Fila y factura son atómicas y no queda archivo físico huérfano ante fallo.
- [x] PDF/JPEG/PNG/WEBP válidos de hasta 10 MB se aceptan; firma, MIME, tamaño o extensión inválidos se rechazan.
- [x] Un Usuario ordinario lista y descarga solo sus propios registros; conocer otro `record_id` no amplía acceso.
- [x] `system_accounts` puede listar todos los registros y descargar sus facturas.
- [x] La migración `20260828_0013` aplica sobre `20260827_0012` y deja un solo head en PostgreSQL local.
- [x] Suite backend, prueba enfocada, build frontend, contrato documental y navegador a 320, 360, 390, 412, 440, 600, 640, 768, 820 y 1024 px pasan sin overflow, recortes o pérdida de foco.
