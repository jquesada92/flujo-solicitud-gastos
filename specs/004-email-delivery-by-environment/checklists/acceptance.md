# Aceptación 004

- [x] producción soporta Brevo HTTPS API.
- [ ] Settings rechaza `EMAIL_MODE=console` y `PUBLIC_URL` no HTTPS en producción.
- [x] local soporta SMTP configurable.
- [x] Docker local usa console por defecto y no entrega correo accidentalmente.
- [x] modo console no pretende entrega real.
- [x] secretos no viven en frontend.
- [x] existe comando de diagnóstico de correo.
- [x] invitaciones IAM incluyen contexto de Cargo/permisos sin derivar acceso desde Cargo.
- [x] restablecimiento usa un template propio con enlace y sin contraseña.
- [x] el correo informa la vigencia configurable del enlace.
- [x] un fallo de entrega revierte la emisión y conserva el enlace anterior.
