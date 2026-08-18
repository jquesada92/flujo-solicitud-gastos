# Criterios de aceptación — Cierre/factura por propiedad o delegación

**Feature:** 008  
**Constitución:** 2.7.0

## Backend / autorización

- [x] `ExpenseOut` expone `can_close` y `can_delegate_close`.
- [x] solicitante original `APPROVED` obtiene `can_close=true` sin depender de `requests:close`.
- [x] Administrador del sistema obtiene `can_close=true` como excepción por `system_accounts`.
- [x] delegado activo obtiene `can_close=true` para esa solicitud.
- [x] tercero con `requests:close` legacy no obtiene `can_close` sobre solicitud ajena.
- [x] `POST /close` vuelve a validar backend-authoritative.
- [x] `PUT /invoice` vuelve a validar backend-authoritative.
- [x] delegado inactivo no obtiene autoridad.

## Delegación

- [x] existe `expense_closure_delegations`.
- [x] existe índice único parcial para una delegación activa por solicitud.
- [x] solo el solicitante puede crear delegación.
- [x] solo el solicitante puede cambiar/revocar delegación.
- [x] solicitante no puede delegarse a sí mismo.
- [x] no se delega a `system_accounts`.
- [x] cambiar delegado revoca/flush primero el anterior.
- [x] revocación conserva actor/timestamp.
- [x] historial no se borra físicamente.
- [x] la delegación se ofrece únicamente en `APPROVED`/`CLOSED`.

## Dashboard

- [x] solicitante recibe `CLOSE_REQUEST` para solicitud `APPROVED` propia.
- [x] delegado activo recibe `CLOSE_REQUEST` para esa solicitud.
- [x] usuario con `requests:close` legacy sin delegación no recibe `CLOSE_REQUEST`.
- [x] Administrador del sistema no recibe automáticamente todas las solicitudes aprobadas como tareas personales.

## Frontend

- [x] existe componente modular `closure-delegation.jsx`.
- [x] la tabla usa `x.can_close` para **Registrar factura y cerrar**.
- [x] la tabla usa `x.can_close` para **Corregir factura**.
- [x] la tabla usa `x.can_delegate_close` para abrir la delegación.
- [x] el modal muestra delegado actual y candidatos.
- [x] el modal permite delegar/cambiar/revocar.
- [ ] validar manualmente que un tercero no vea cierre/corrección factura.
- [ ] validar manualmente que el solicitante sí vea cierre y delegación.
- [ ] validar manualmente que el Administrador del sistema sí pueda cerrar/corregir factura.
- [ ] validar manualmente que un delegado vea cierre pero no pueda administrar la delegación.
- [ ] validar manualmente revocación inmediata del delegado.

## Migración

- [x] Alembic `0005` depende de `0004`.
- [x] `0005` crea tabla e índices.
- [x] `0005` marca `requests:close` como inactivo/legacy.
- [x] test de topología exige `0005` como único head.
- [ ] smoke `alembic upgrade head` en PostgreSQL/Neon preview/copia.
- [ ] confirmar en DB productiva después del deploy que `requests:close.active=false`.

## Pruebas

- [x] `test_closure_delegation.py` agregado y corregido para sembrar baseline `requests:read`.
- [x] `test_pending_actions.py` actualizado a requester/delegate.
- [x] `test_universal_tracking.py` prueba que lectura no concede cierre ajeno.
- [x] `test_frontend_closure_contract.py` protege capacidades por recurso.
- [x] `test_migrations.py` protege `0005`.
- [ ] suite backend completa ejecutada localmente en head final.
- [ ] `npm run build` ejecutado localmente en head final.
- [ ] Docker build/smoke ejecutado localmente en head final.
- [ ] CI remoto verde cuando vuelva la cuota de GitHub Actions.

## Documentación

- [x] Constitución actualizada a 2.7.0.
- [x] Feature 008 spec/plan/checklist creados.
- [x] README actualizado.
- [x] PROMPT_RECONSTRUCCION actualizado.
- [x] `docs/CLOSURE_DELEGATION.md` creado.
- [x] `docs/FASTAPI_ARCHITECTURE.md` actualizado.
- [x] `docs/IAM_MODEL.md` actualizado.
- [x] `docs/REQUEST_TRACKING.md` actualizado.
- [x] `docs/TERMINOLOGY.md` actualizado.
- [x] `docs/README.md` actualizado.
- [x] Feature 005 revisada para `CLOSE_REQUEST` por propiedad/delegación.
- [x] HISTORY actualizado.
- [x] CHANGELOG actualizado.
- [ ] PR #9 actualizado.
