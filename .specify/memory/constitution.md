# Constitución del proyecto

**Proyecto:** Flujo de Control de Gastos  
**Versión:** 2.1.0  
**Vigente desde:** 2026-08-17

## 1. Evolucionar, no reconstruir sin necesidad

El producto existente debe evolucionar sobre el repositorio actual. Se reutiliza el código correcto y se migra o reemplaza únicamente lo que contradiga esta constitución, las especificaciones vigentes o los criterios de aceptación.

## 2. Producto neutral respecto al tipo de organización

El sistema debe poder utilizarse en empresas, PH y otras organizaciones sin introducir en el núcleo conceptos exclusivos de un dominio particular.

No forman parte del modelo canónico:

- apartamentos;
- propietarios o copropietarios;
- residentes o arrendatarios;
- `PersonType`;
- `OwnershipRole`;
- relaciones usuario-apartamento.

## 3. Terminología canónica

La terminología funcional vigente es:

- **Usuario**: cuenta que interactúa con el sistema. No utilizar Persona/Personas como nombre del dominio de cuentas.
- **Área**: unidad, departamento o función organizacional asociada al gasto.
- **Categoría**: naturaleza del bien o servicio adquirido.

Área y Categoría son catálogos independientes. Una Categoría puede habilitarse para múltiples Áreas mediante una relación configurable.

## 4. Configuración sobre código

Roles, cargos, perfiles, permisos, niveles o scopes de permiso, áreas, categorías, grupos de aprobación y políticas deben persistirse en PostgreSQL y gobernar el comportamiento en runtime.

No autorizar por:

- nombre de rol o cargo hardcodeado;
- correo fijo;
- ID mágico;
- listas fijas de perfiles;
- conceptos de propiedad inmobiliaria.

El administrador técnico inicial puede existir como bootstrap, pero sus permisos efectivos deben representarse en datos persistidos.

## 5. Backend como autoridad

El frontend puede ocultar o mostrar acciones por conveniencia de UX, pero el backend es la autoridad final para autorización, transiciones, acceso a documentos y decisiones.

## 6. Historial y trazabilidad

Toda acción significativa debe poder reconstruirse con:

- actor;
- fecha y hora;
- entidad afectada;
- estado anterior y nuevo cuando aplique;
- campos modificados;
- comentario, motivo o evidencia cuando corresponda.

Los eventos históricos relevantes son append-only y no deben modificarse silenciosamente.

## 7. Evidencia documental

Los documentos son evidencia privada. Deben:

- validarse por contenido real;
- almacenarse fuera del acceso público directo;
- descargarse únicamente con autorización del backend;
- conservar versiones anteriores cuando se sustituyan;
- registrar actor, fecha, motivo y relación con el expediente.

## 8. Solicitudes y clasificación

Cada solicitud debe clasificarse al menos por:

- Área;
- Categoría.

La clasificación histórica de una solicitud no se modifica retroactivamente porque un catálogo o relación sea renombrado, desactivado o cambiado posteriormente.

La solicitud simple contiene una opción de compra/cotización. La solicitud `MULTI_QUOTE` mantiene la selección de cotización separada del proceso de aprobación.

## 9. Decisiones y aprobaciones

Los participantes elegibles de cada ronda deben quedar congelados o versionados.

Para una ronda de aprobación:

- `response_rate = valid_responses / eligible_participants`;
- solo puede resolverse cuando `response_rate > 0.50`;
- `approval_rate = approvals / valid_decision_responses`;
- `rejection_rate = rejections / valid_decision_responses`;
- se aprueba si `approval_rate > 0.50`;
- se rechaza si `rejection_rate > 0.50`;
- empate o falta de mayoría permanece pendiente;
- solicitar corrección es una transición explícita y separada.

Las reglas de selección de cotización no se presumen iguales a las reglas de aprobación y deben especificarse por separado.

## 10. Aprobado no significa cerrado

Una solicitud aprobada permanece en proceso hasta completar los requisitos de ejecución/cierre.

El cierre de una solicitud aprobada requiere factura y autorización explícita. La generación de orden de compra debe ser idempotente. Una solicitud rechazada puede terminar sin factura ni orden de compra.

## 11. Migraciones y protección de datos

Los cambios estructurales deben utilizar migraciones versionadas. No se deben introducir nuevas migraciones destructivas ad-hoc durante el startup.

Antes de retirar datos o estructuras productivas:

1. respaldo;
2. inventario de dependencias y datos;
3. migración versionada;
4. validación;
5. procedimiento real de recuperación/rollback.

Un `downgrade()` que solo recrea tablas no se considera recuperación de datos eliminados.

## 12. Seguridad y rendimiento

Como mínimo:

- JWT con expiración absoluta;
- timeout de inactividad;
- revocación por versión de sesión;
- rate limiting diferenciado;
- límites de abuso para enlaces públicos firmados;
- CORS restrictivo;
- secretos fuera del frontend y logs;
- consultas parametrizadas/ORM;
- paginación backend para colecciones crecientes, default 25 y máximo 100;
- evitar N+1;
- pool de base de datos acotado y query timeout configurable.

## 13. Calidad y pruebas

Los cambios deben incluir pruebas proporcionales al riesgo. Como mínimo, cuando aplique:

- pruebas negativas de autorización;
- pruebas de transición de estados;
- integridad histórica;
- migraciones y compatibilidad de datos;
- concurrencia e idempotencia;
- backend regression tests;
- `npm run build` para frontend;
- construcción de imágenes Docker en CI.

## 14. Documentación es parte del código

**Ningún cambio funcional, de dominio, UX, API, modelo de datos, seguridad, migración o arquitectura se considera terminado si la documentación afectada no queda actualizada en el mismo PR.**

Para cada cambio se debe revisar y actualizar, cuando aplique:

- `.specify/memory/constitution.md`;
- `specs/<feature>/spec.md`;
- `specs/<feature>/plan.md`;
- criterios de aceptación de la feature;
- `README.md`;
- `PROMPT_RECONSTRUCCION.md` y otros prompts maestros;
- `docs/` funcionales y técnicos;
- `docs/TERMINOLOGY.md` si cambia lenguaje del producto;
- `docs/HISTORY.md` para decisiones funcionales/técnicas relevantes;
- `CHANGELOG.md` para cambios entregables;
- contratos/API y comentarios técnicos cuando su semántica cambie.

Si un documento no aplica al cambio, no es obligatorio modificarlo, pero debe evaluarse explícitamente.

## 15. Consistencia entre artefactos

La prioridad es:

1. Constitución vigente.
2. Especificación funcional de la feature.
3. Aclaraciones/criterios de aceptación aprobados.
4. Plan técnico.
5. Tareas y código.
6. README, prompts y documentación derivada.

Si el código y la documentación discrepan, la discrepancia es un defecto que debe resolverse antes de considerar la feature completa.

## 16. Definition of Done documental

Una feature está documentariamente terminada cuando:

- términos visibles coinciden con `docs/TERMINOLOGY.md`;
- requisitos y criterios de aceptación describen el comportamiento implementado;
- el plan técnico refleja modelos, endpoints, migraciones y compatibilidad reales;
- README no enseña conceptos retirados como si siguieran vigentes;
- prompts no reconstruyen comportamiento obsoleto;
- HISTORY explica las decisiones relevantes;
- CHANGELOG registra el cambio entregable;
- CI/pruebas referenciadas por la documentación realmente existen.
