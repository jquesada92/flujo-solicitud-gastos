# Plan 009 — Fronteras de Configuración

1. Mantener `config:read` como permiso de lectura ordinario.
2. En `require_permission`, permitir `config:read` como sustituto de `config:manage` solo para GET/HEAD.
3. Mantener mutaciones IAM bajo `config:manage`.
4. Mantener mutaciones de catálogos bajo `areas:manage`.
5. Evitar inferencia por Cargo/nombre/flags legacy.
6. Cubrir lectura y escrituras 403 con `test_configuration_read_access.py`.
