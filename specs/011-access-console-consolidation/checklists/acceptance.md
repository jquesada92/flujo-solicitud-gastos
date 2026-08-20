# Criterios de aceptación — Consolidación de Usuarios y Organigrama en Accesos

**Feature:** 011  
**Constitución:** 2.9.0

## Navegación

- [x] **Usuarios/Personas** deja de aparecer como entrada independiente de Configuración.
- [x] **Organigrama** deja de aparecer como entrada independiente de Configuración.
- [x] **Accesos** permanece como punto único de administración IAM.
- [ ] validar manualmente navegación final en Docker después del pull más reciente.

## Accesos

- [x] creación de Usuarios permanece dentro de Accesos.
- [x] Grupos permanecen dentro de Accesos.
- [x] Roles y Permisos permanecen dentro de Accesos.
- [x] Cargos/Posiciones permanecen dentro de Accesos.
- [x] asignaciones y permisos efectivos permanecen dentro de Accesos.
- [ ] validar manualmente edición de un usuario existente.

## Seguridad

- [x] `config:manage` continúa siendo system-only.
- [x] `config:read` no concede mutaciones.
- [x] `areas:manage` no concede administración IAM.
- [x] ocultar UI no reemplaza autorización backend.

## Clasificación canónica

- [x] `expense_area` es el nombre canónico de Área en solicitudes.
- [x] `expense_category` es el nombre canónico de Categoría en solicitudes.
- [x] Alembic `20260819_0008` está presente en la rama después de sincronizar `main`.
- [x] `expense_type` / `expense_subcategory` quedan únicamente como compatibilidad legacy cuando sea necesario.

## Integración

- [x] cambios faltantes de `main` integrados en `agent/consolidate-users-organigram-in-access`.
- [ ] `alembic current` ejecutado contra la base local final.
- [ ] `alembic heads` ejecutado en la rama final.
- [ ] suite backend ejecutada en head final.
- [ ] `npm run build` ejecutado en head final.

## Documentación

- [ ] Constitución actualizada a 2.9.0.
- [x] spec Feature 011 creado.
- [x] plan Feature 011 creado.
- [x] checklist Feature 011 creado.
- [ ] README principal actualizado.
- [ ] PROMPT_RECONSTRUCCION actualizado.
- [ ] CONFIGURATION_ACCESS actualizado.
- [ ] índice docs actualizado.
- [ ] HISTORY actualizado.
- [ ] CHANGELOG actualizado.
