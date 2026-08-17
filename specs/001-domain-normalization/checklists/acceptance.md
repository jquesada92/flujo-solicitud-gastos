# Acceptance Checklist — 001 Domain Normalization

## Terminología

- [ ] La navegación muestra **Usuarios**, no Personas.
- [ ] Formularios, placeholders, títulos y acciones visibles usan Usuario/Usuarios.
- [ ] El formulario de solicitud muestra **Área** y **Categoría**.
- [ ] El segundo selector no se presenta como Subárea.
- [ ] `docs/TERMINOLOGY.md` coincide con la UI.

## Clasificación

- [ ] Área representa una unidad/departamento/función organizacional.
- [ ] Categoría representa la naturaleza del bien o servicio.
- [ ] Área y Categoría son catálogos independientes.
- [ ] Una Categoría puede estar vinculada a más de un Área.
- [ ] No se crean duplicados lógicos de una Categoría solo porque se use en varias Áreas.
- [ ] El formulario solo ofrece Categorías habilitadas para el Área seleccionada.
- [ ] Desactivar/desvincular una relación no reescribe solicitudes históricas.

## Dominio inmobiliario

- [ ] El backend activo no requiere Apartment.
- [ ] El backend activo no requiere UserApartment.
- [ ] El backend activo no requiere ApartmentChangeEvent.
- [ ] El backend activo no requiere OwnershipRole.
- [ ] El backend activo no requiere PersonType.
- [ ] El modelo activo de User no requiere apartment_number.
- [ ] No existen endpoints activos de apartamentos.
- [ ] La limpieza física destructiva está separada del startup y exige backup.

## Compatibilidad

- [ ] Solicitudes existentes conservan los valores históricos de Área y Categoría.
- [ ] La compatibilidad legacy no altera autorización.
- [ ] Los contratos canónicos nuevos están documentados bajo `/api/areas`.
- [ ] Los nombres físicos legacy pendientes están declarados como deuda/transición, no como modelo funcional vigente.

## Seguridad

- [ ] El backend continúa validando permisos para operaciones de configuración.
- [ ] La normalización visual del frontend no concede permisos.
- [ ] No se introducen secretos en frontend o logs.

## Pruebas y build

- [ ] `python -m compileall -q app` pasa.
- [ ] `python -m unittest discover -s tests -v` pasa.
- [ ] `npm ci` pasa.
- [ ] `npm run build` pasa.
- [ ] Docker backend construye.
- [ ] Docker frontend construye.

## Documentación

- [ ] Constitución actualizada.
- [ ] `spec.md` actualizado.
- [ ] `plan.md` actualizado.
- [ ] Criterios de aceptación actualizados.
- [ ] README actualizado.
- [ ] PROMPT_RECONSTRUCCION actualizado.
- [ ] Modelo de clasificación actualizado.
- [ ] Terminología actualizada.
- [ ] HISTORY actualizado.
- [ ] CHANGELOG actualizado.
- [ ] PR describe el cambio funcional, técnico, compatibilidad y validación.

## Definition of Done

La feature no se considera terminada mientras exista una discrepancia conocida entre comportamiento implementado y documentación vigente sin quedar explícitamente marcada como deuda/transición.
