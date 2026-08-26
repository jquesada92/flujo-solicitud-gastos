# Aceptación — Spec 019

- [x] Un Rol agrupado con permiso propio `requests:approve` entra en la ronda.
- [x] Un Rol agrupado hereda `requests:approve` de su Grupo activo y entra en la ronda.
- [x] Un Rol global con `requests:approve` entra en la ronda.
- [x] La ronda `SIMPLE` se crea sin requerir una `ApprovalPolicy`.
- [x] Sin participantes elegibles, crear con URL responde 422 y no persiste la solicitud.
- [x] Sin participantes elegibles, subir el soporte responde 422 y elimina solicitud y archivo.
- [x] Código y origen del permiso se muestran separados en Accesos.
- [x] Suite backend, build frontend y contrato documental pasan en local.
