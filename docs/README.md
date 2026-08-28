# Índice de documentación

## Empieza aquí

1. [Reglas operativas para agentes e IA](../AGENTS.md), incluidos límites de
   alcance, protección de datos y guardrails de IAM/restablecimiento.
2. [Constitución](../.specify/memory/constitution.md)
3. [Specs vigentes](../specs/)
4. [Contrato vigente](CURRENT_PRODUCT_CONTRACT.md)
5. [Prompt de reconstrucción](../PROMPT_RECONSTRUCCION.md)
6. [README principal](../README.md)
7. [Riesgos y divergencias conocidas](KNOWN_RISKS.md)

## Producto y UX

- [Guía de uso para Solicitantes y Junta Directiva](GUIA_USUARIO_FINAL.md)
- [Terminología](TERMINOLOGY.md)
- [Inicio y Seguimiento](REQUEST_TRACKING.md)
- [Runtime frontend](FRONTEND_RUNTIME.md)
- [Correcciones](REQUEST_CORRECTIONS.md)
- [Solicitudes múltiples y votación](MULTI_QUOTE_VOTING.md)
- [Registro directo sin aprobación](DIRECT_EXPENSES.md)
- [Delegación de cierre](CLOSURE_DELEGATION.md)
- [Clasificación Área + Categoría](CLASSIFICATION_MODEL.md)

## Acceso y configuración

- [Modelo IAM](IAM_MODEL.md)
- [Configuración y Accesos](CONFIGURATION_ACCESS.md)
- [Correo](EMAIL_CONFIGURATION.md)

## Arquitectura / operación

- [FastAPI](FASTAPI_ARCHITECTURE.md)
- [Neon](NEON_SETUP.md)
- [Validación local con Docker](VALIDACION_LOCAL.md)
- [Validación de producción](VALIDACION_PRODUCCION.md)
- [Política documental](DOCUMENTATION_POLICY.md)
- [Riesgos y divergencias conocidas](KNOWN_RISKS.md)
- [Historia](HISTORY.md)

## Specs

Las Specs vigentes están en `specs/` y deben leerse como contrato actual de cada feature. Si una feature cambia de arquitectura, su Spec se actualiza o reemplaza; no se mantiene un diseño sustituido como opción vigente.

Para cambios asistidos por IA, `AGENTS.md` es la política operativa y
`DOCUMENTATION_POLICY.md` define la matriz de sincronización y sus pruebas. No
usar HISTORY, CHANGELOG, código legacy o una captura de pantalla como sustituto
de Constitución + Spec vigente.
