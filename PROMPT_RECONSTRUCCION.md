# Prompt maestro de reconstrucción

Reconstruye una aplicación web lista para producción llamada **Flujo de Control de Gastos**, destinada a solicitar, evaluar, aprobar, ejecutar y documentar gastos con evidencia verificable de cada decisión.

## Autoridad de documentos

Antes de implementar, lee y respeta en este orden:

1. `.specify/memory/constitution.md`
2. `specs/**/spec.md`
3. criterios/checklists de aceptación
4. `specs/**/plan.md`
5. este `PROMPT_RECONSTRUCCION.md`
6. `README.md`
7. documentación de `docs/`
8. código existente

Si existe una discrepancia, la constitución y las especificaciones vigentes prevalecen.

## 1. Principio de producto

El sistema debe convertir cada solicitud de gasto en un expediente digital, trazable y auditable que permita demostrar:

- quién creó la solicitud y cuándo;
- Área y Categoría asociadas;
- opciones, proveedores y cotizaciones evaluadas;
- participantes y decisiones;
- comentarios y motivos;
- documentos disponibles;
- opción seleccionada;
- factura y cierre;
- evolución histórica del expediente.

El producto debe ser neutral respecto al tipo de organización.

## 2. Dominio excluido

No reconstruyas como conceptos canónicos:

- apartamentos;
- `Apartment`;
- `UserApartment`;
- `ApartmentChangeEvent`;
- propietarios/copropietarios;
- residentes/arrendatarios;
- `OwnershipRole`;
- `PersonType`;
- `apartment_number`;
- endpoints o pantallas de apartamentos.

La autorización y los flujos no pueden depender de conceptos inmobiliarios.

## 3. Terminología canónica

### Usuario

Usa **Usuario / Usuarios** para el dominio de cuentas.

No uses **Persona / Personas** como nombre del módulo de administración de cuentas.

El backend usa `User` y `/api/users`.

### Área

Representa una unidad, departamento o función organizacional asociada al gasto.

Ejemplos:

- Administración
- Operaciones
- IT
- Mantenimiento
- Marketing

### Categoría

Representa la naturaleza del bien o servicio adquirido.

Ejemplos:

- Equipos
- Servicios / Consultoría
- Insumos
- Software / Licencias
- Mobiliario

Área y Categoría son catálogos independientes.

Una Categoría puede habilitarse para múltiples Áreas mediante una relación configurable.

El formulario debe mostrar:

```text
Área
Categoría
```

No debe mostrar `Subárea` para el segundo selector.

## 4. Arquitectura

Mantén el stack actual:

- Frontend: React + Vite, Vercel.
- Backend: FastAPI + SQLAlchemy, Docker, Render.
- Base de datos: PostgreSQL / Neon.
- Correo: Brevo HTTPS API.
- Documentos: disco persistente privado de Render.
- Autenticación: JWT.

Toda lectura o modificación sensible pasa por el backend. El frontend nunca es autoridad de permisos.

## 5. Usuarios y autorización

Los usuarios pueden incluir:

- documento de identidad;
- nombres y apellidos;
- correo;
- teléfono opcional;
- cargo/perfil;
- estado activo/inactivo.

Permite buscar usuarios por documento, nombre, apellido o correo.

El modelo objetivo de autorización debe persistir en PostgreSQL:

- roles;
- cargos/perfiles;
- permisos;
- niveles/scopes;
- asignaciones;
- grupos y políticas de aprobación.

No autorices por:

- nombre de cargo hardcodeado;
- correo fijo;
- ID mágico;
- concepto inmobiliario.

El administrador técnico inicial puede crearse mediante `ADMIN_*`, pero sus privilegios efectivos deben representarse en datos persistidos.

## 6. Sesiones y contraseñas

Implementa:

- `TOKEN_EXPIRE_MINUTES=480` como expiración absoluta inicial;
- `SESSION_IDLE_MINUTES=30` para inactividad humana;
- versión de sesión por usuario para revocación;
- `POST /api/auth/activity` para actividad humana;
- rate limiting de login;
- mensajes de autenticación que no revelen si un correo existe;
- cambio obligatorio de contraseña temporal cuando corresponda.

El polling no debe mantener viva la sesión.

## 7. Clasificación Área + Categoría

El modelo funcional canónico es:

```text
Área + Categoría
```

API canónica:

```text
GET    /api/areas
POST   /api/areas
PATCH  /api/areas/{area_id}
GET    /api/areas/categories
POST   /api/areas/categories
PATCH  /api/areas/categories/{category_id}
POST   /api/areas/{area_id}/categories
POST   /api/areas/{area_id}/categories/{category_id}
DELETE /api/areas/{area_id}/categories/{category_id}
```

Una misma Categoría debe poder relacionarse con múltiples Áreas.

Al seleccionar un Área, ofrece únicamente Categorías habilitadas para ella.

Desactivar una relación o catálogo no debe alterar solicitudes históricas.

### Compatibilidad temporal

Mientras exista deuda legacy, puede conservarse:

```text
expenses.expense_type        -> Área
expenses.expense_subcategory -> Categoría
expense_categories           -> almacenamiento legacy de Áreas
expense_subcategories        -> puente temporal Área-Categoría
```

Las estructuras canónicas nuevas incluyen:

```text
expense_category_catalog
expense_area_categories
```

No presentes los nombres físicos legacy como modelo funcional vigente.

## 8. Solicitudes de gasto

Cada solicitud debe conservar:

- identificador interno;
- identificador visible;
- flow ID;
- vínculo a versión previa cuando sea corrección;
- solicitante;
- Área;
- Categoría;
- título y descripción/justificación;
- urgencia;
- tipo de solicitud;
- estado;
- documentos;
- decisiones e historial.

Tipos:

- `SIMPLE`
- `MULTI_QUOTE`

Estados principales:

```text
QUOTATION_VOTING
SUBMITTED
PENDING_APPROVAL
APPROVED
REJECTED
CANCELLED
CLOSED
NEEDS_REVISION
```

Una solicitud simple contiene una opción/cotización.

Una solicitud `MULTI_QUOTE` mantiene la selección de cotización separada de la aprobación.

## 9. Votación de cotizaciones

Debe existir una ronda explícita de votación/selección.

- congelar/versionar participantes elegibles;
- permitir voto vigente por participante;
- registrar cambios de voto como eventos;
- no seleccionar automáticamente por URL;
- definir empate y regla de ganador en la especificación de esa feature;
- no asumir que el quórum de aprobación aplica también a votación.

La opción ganadora no significa solicitud aprobada.

## 10. Aprobaciones

Los participantes elegibles de cada ronda deben quedar congelados/versionados.

Regla de resolución:

```text
response_rate = valid_responses / eligible_participants
```

Solo puede resolverse cuando:

```text
response_rate > 0.50
```

Luego:

```text
approval_rate = approvals / valid_decision_responses
rejection_rate = rejections / valid_decision_responses
```

Resultado:

- aprobar si `approval_rate > 0.50`;
- rechazar si `rejection_rate > 0.50`;
- empate o ausencia de mayoría permanece pendiente;
- solicitar corrección es una transición separada.

No permitas autoaprobación cuando la política lo prohíba.

## 11. Correcciones y versiones

Una corrección debe crear una nueva versión enlazada, no sobrescribir silenciosamente el expediente anterior.

Preserva:

- clasificación histórica;
- documentos;
- decisiones anteriores;
- comentarios;
- relación entre versiones.

## 12. Aprobado, factura y cierre

`APPROVED` no equivale a `CLOSED`.

Una solicitud aprobada permanece en proceso hasta cumplir requisitos de cierre.

Para cerrar una solicitud aprobada:

- exigir factura;
- exigir autorización explícita;
- registrar actor, fecha/hora y notas;
- generar orden de compra de manera idempotente cuando corresponda.

Una solicitud rechazada puede terminar sin factura ni orden de compra.

## 13. Documentos privados

Admite PDF, JPEG, PNG y WEBP.

Valida:

- MIME;
- firma real;
- tamaño;
- cuota de almacenamiento.

Usa nombres internos impredecibles.

Cada descarga requiere autorización del backend.

Si se reemplaza un documento, conserva versión anterior, motivo, actor y fecha.

## 14. Auditoría

Registra eventos inmutables para acciones relevantes:

- solicitudes/transiciones;
- aprobaciones;
- votos;
- documentos;
- facturas;
- usuarios/permisos;
- catálogos;
- políticas;
- exports cuando aplique.

Cada evento debe incluir actor, timestamp, entidad, cambio y motivo/comentario cuando corresponda.

Los eventos críticos son append-only.

## 15. Seguridad y rendimiento

Incluye:

- JWT seguro;
- expiración absoluta;
- inactividad;
- revocación;
- CORS restrictivo;
- secrets fuera de frontend/logs;
- ORM/consultas parametrizadas;
- rate limiting diferenciado;
- protección por IP de enlaces públicos firmados;
- paginación backend default 25 y máximo 100;
- ordering estable;
- evitar N+1;
- pool acotado;
- query timeout configurable.

## 16. Migraciones

Usa migraciones versionadas.

No introduzcas nuevos DROP/ALTER destructivos grandes en startup.

Antes de destruir datos:

1. backup/snapshot;
2. inventario de dependencias y conteos;
3. migración en staging/test;
4. validación;
5. plan real de recuperación;
6. producción.

Recrear estructura no recupera datos eliminados.

## 17. UI

La navegación y pantallas deben usar terminología canónica.

Módulos principales según permisos:

- Inicio
- Solicitudes
- Facturas
- Auditoría
- Usuarios
- configuración organizacional
- Áreas/Categorías
- Reglas/políticas

Cada pantalla debe contemplar carga, vacío, error, éxito y comportamiento responsive.

## 18. CI y pruebas

CI debe ejecutar al menos:

```text
python -m compileall -q app
python -m unittest discover -s tests -v
npm ci
npm run build
Docker build backend
Docker build frontend
```

Agrega pruebas negativas de autorización y pruebas de migración, historia, transiciones, concurrencia e idempotencia cuando la feature lo requiera.

## 19. Documentación obligatoria

La documentación forma parte del código.

Para cada feature evalúa y actualiza en el mismo PR, cuando aplique:

- `.specify/memory/constitution.md`;
- `specs/<feature>/spec.md`;
- `specs/<feature>/plan.md`;
- criterios de aceptación;
- `README.md`;
- este prompt maestro;
- `docs/TERMINOLOGY.md`;
- documentación funcional/técnica relevante;
- `docs/HISTORY.md`;
- `CHANGELOG.md`;
- descripción del PR.

No declares una feature completa con documentación obsoleta.

## 20. Criterios de aceptación globales

Como mínimo demuestra que:

- el producto no requiere dominio inmobiliario activo;
- la UI usa Usuario/Usuarios;
- el formulario usa Área + Categoría;
- una Categoría puede relacionarse con varias Áreas;
- historia de clasificación no se reescribe;
- backend valida permisos;
- documentos privados requieren autorización;
- correcciones preservan historia;
- votación y aprobación son procesos separados;
- aprobación aplica quórum y mayoría definidos;
- aprobado no se cierra automáticamente;
- cierre aprobado requiere factura;
- eventos relevantes son trazables;
- backend regression tests pasan;
- frontend build pasa;
- imágenes Docker construyen;
- constitución, specs, plan, criterios, README, prompt, history y changelog están sincronizados.

Consulta `docs/README.md` para el índice documental completo.
