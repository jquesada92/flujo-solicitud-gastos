# Aceptación 011

- [x] seleccionar acceso de Usuario no produce PATCH inmediato.
- [x] Guardar cambios persiste el acceso staged.
- [x] máximo un Rol por Grupo.
- [x] un Usuario puede seleccionar varios Roles globales ordinarios.
- [x] un Grupo puede existir sin Roles.
- [x] un Rol puede ser global o pertenecer a máximo un Grupo.
- [x] miembros de Grupo son solo lectura y derivan únicamente de Roles agrupados.
- [x] permisos se configuran solo en Roles.
- [x] nombre de Rol guardado se refleja sin GET adicional obligatorio.
- [x] Administrador del sistema aparece como Rol global técnico protegido.
- [x] rutas privadas sin sesión vuelven a Login.
- [x] 401 invalida sesión local.
- [x] no existe polling cada segundo/sub-segundo.
- [x] GET idénticos concurrentes se deduplican.
- [x] botón Recargar puede obtener datos frescos.
