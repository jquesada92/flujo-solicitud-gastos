# Spec 017 — Restablecimiento de contraseña mediante enlace

**Estado:** Implementada
**Constitución:** 2.18.0

## Objetivo

Permitir que el Administrador del sistema ayude a un Usuario que olvidó su
contraseña sin generar, conocer ni enviar una contraseña nueva.

## Emisión administrativa

Desde la ficha de un Usuario en Accesos, **Regenerar contraseña** envía un enlace
de restablecimiento mediante una acción inmediata después de una confirmación
explícita. No forma parte del borrador de Roles y no espera **Guardar cambios**.

La operación exige `config:manage` efectivo conforme a la política protegida de
`system_accounts`. El destinatario debe existir, estar activo y no ser una cuenta
técnica. La respuesta confirma el envío sin devolver el token ni información
sensible.

La ruta administrativa compatible es:

```text
POST /api/users/{user_id}/regenerate-password
```

## Token

El enlace contiene un token de propósito exclusivo para restablecimiento de
contraseña. No es un JWT de sesión ni puede aceptarse en endpoints autenticados.

Reglas:

- expira después de `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, 30 minutos por defecto;
- solo puede consumirse una vez;
- emitir un enlace nuevo incrementa `password_reset_version` e invalida todos los anteriores del Usuario;
- cambiar el correo o el estado `active` incrementa la versión e invalida todos los enlaces;
- emitirlo no cambia la contraseña, `must_change_password` ni las sesiones vigentes;
- el token nunca se devuelve en la respuesta administrativa ni se guarda o registra en claro; los logs ordinarios no lo incluyen y `EMAIL_MODE=console` es la excepción local sensible porque imprime el correo.

El correo apunta a:

```text
{PUBLIC_URL}/reset-password#token=...
```

El mensaje explica la vigencia y permite ignorarlo si no fue solicitado. Incluye
el enlace, pero nunca una contraseña temporal, una contraseña nueva ni el hash.
El fragmento `#token=...` no se envía con la solicitud HTTP ni queda en logs
HTTP/CDN.

## Consumo público

La pantalla `/reset-password#token=...` está disponible sin sesión. La SPA
captura el fragmento en memoria y lo retira de la URL al cargar, sin guardarlo en
`localStorage` o `sessionStorage`; después envía la nueva contraseña a:

```text
POST /api/auth/reset-password
```

El backend valida propósito, integridad, expiración, uso único, coincidencia de
`password_reset_version`, Usuario activo y exclusión de cuentas técnicas. Un
token inválido, expirado, reemplazado o ya consumido no cambia datos.

Al aceptar una contraseña válida:

1. se almacena mediante Argon2;
2. se establece `must_change_password=false`;
3. se incrementa `session_version` para revocar sesiones anteriores;
4. se incrementa `password_reset_version` para invalidar todos los enlaces;
5. se registra la acción sin token, contraseña ni hash;
6. se muestra confirmación y se vuelve al Login sin auto-login;
7. después del commit se intenta enviar una notificación best-effort de
   contraseña cambiada, sin incluir token ni contraseña.

## Transacción, auditoría y límites

Correo y base de datos no son una transacción atómica. Si el proveedor reporta
un fallo antes del commit, se revierte la emisión y ningún enlace anterior pierde
vigencia. Si el proveedor acepta el mensaje pero el commit posterior falla, el
destinatario puede recibir un enlace inútil; la contraseña, las sesiones y el
acceso no cambian, y el Administrador puede reintentar. Resolver entrega
exactamente-una-vez exige un outbox transaccional.

La notificación posterior al cambio se intenta después del commit. Su fallo no
revierte la contraseña ya confirmada y se registra sin incluir secretos. La
auditoría identifica al Administrador que emitió el enlace y el consumo
correspondiente sin almacenar token, contraseña o hash.

La emisión usa la política sensible por usuario autenticado. El consumo público
permite 5 intentos por 15 minutos por dirección IP y por proceso, con limpieza
TTL de entradas inactivas. Es una defensa local, no una cuota global coordinada
entre réplicas, y su precisión depende de que el proxy entregue una IP cliente
confiable. Las pruebas emplean mocks o `EMAIL_MODE=console`; nunca envían correo
real y tratan como sensible cualquier log local que contenga el enlace.
