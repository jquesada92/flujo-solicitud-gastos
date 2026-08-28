# Aceptación 023

- [ ] `POST`, `PUT`, `PATCH` y `DELETE` del API muestran **Procesando…** antes del envío.
- [ ] El overlay queda por encima de topbar, Accesos y modales y no es descartable.
- [ ] El resto de la aplicación queda `inert` para mouse, touch y teclado.
- [ ] El contador conserva el bloqueo hasta finalizar la última mutación concurrente.
- [ ] Éxito, HTTP error, aborto y fallo de red liberan el bloqueo sin descartar el borrador.
- [ ] `GET`/`HEAD` y `/api/auth/activity` no muestran el overlay.
- [ ] Desde 320 px no hay overflow, recortes ni pérdida del mensaje o spinner.
- [ ] Un `POST` exitoso de Rol actualiza la lista y deja el editor vacío y sin selección.
- [ ] Dos Roles consecutivos se crean con dos `POST`; el segundo no sobrescribe el primero.
- [ ] Un error conserva el borrador y edición/reactivación continúan con `PATCH` e ID original.
- [ ] Contratos, suite backend, build frontend y prueba de navegador pasan.
