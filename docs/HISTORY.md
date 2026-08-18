# Historial funcional y técnico

## 2026-08-17 — Docker local expone fragilidad del parche de montaje de ExpenseForm

### Incidente confirmado

Al reconstruir el frontend local con `docker compose build --no-cache frontend`, Vite falló con:

```text
[plugin modular-expense-form]
Legacy main.jsx extraction could not find: ExpenseForm mount
```

La extracción estructural sí podía localizar la definición legacy completa de `ExpenseForm`, pero luego intentaba encontrar el punto de montaje JSX mediante una cadena exacta de espacios y saltos de línea. Ese reemplazo era innecesario y frágil.

### Corrección

`vite.config.js` conserva únicamente la transformación estructural necesaria:

1. importar `ExpenseForm` desde `./expense-form.jsx`;
2. eliminar del bundle la definición legacy entre `function ExpenseForm` y `function ClosurePanel`;
3. no tocar el JSX donde se monta `<ExpenseForm>`.

`expense-form.jsx` ya rehidrata el draft cuando cambian `draft.request_id` o `draft.flow_id`, por lo que no requiere una `key` inyectada durante build.

Se actualiza `test_frontend_revision_contract.py` para impedir que vuelva a introducirse el marcador/parche `ExpenseForm mount`. CI inspecciona además el `dist/` final para comprobar que el formulario modular está realmente presente.

La Constitución 2.3.3 fue revisada y no requiere una nueva regla: el invariant funcional ya exige que la corrección derive el tipo desde la solicitud y que CI/pruebas protejan el comportamiento. Este cambio corrige el mecanismo de implementación, no el contrato funcional.

---

## 2026-08-17 — ExpenseForm modular elimina la ruta visual SIMPLE en correcciones MULTI_QUOTE

### Incidente confirmado

La prueba manual volvió a mostrar una solicitud en **Votación de cotizaciones** que, al pulsar **Corregir / reenviar**, renderizaba el formulario sencillo. Esto confirmó que mantener el source real de `ExpenseForm` como legacy y depender de sustituciones granulares de Vite no era una frontera suficientemente confiable para una regla de negocio.

### Decisión

Se crea un formulario canónico mantenible en:

```text
frontend/src/expense-form.jsx
```

El componente usa `resolveRequestType(draft)` y un único `effectiveRequestType`. Cuando existe `draft`, el tipo efectivo se deriva exclusivamente de evidencia persistida:

```text
request_type == MULTI_QUOTE
OR status == QUOTATION_VOTING
OR quotation_options >= 2
```

Para una corrección MULTI_QUOTE, el layout sencillo deja de ser una ruta válida: el componente renderiza directamente **Opciones para votación**, restaura las opciones existentes y conserva metadata de soportes.

`vite.config.js` deja de parchear condiciones internas del formulario. Durante la transición solo importa el componente modular y elimina del bundle la función `ExpenseForm` legacy completa.

### Protección

`test_frontend_revision_contract.py` exige la existencia del componente modular, la autoridad de `effectiveRequestType`, restauración de opciones/soportes y la extracción completa del ExpenseForm legacy durante build.

---

## 2026-08-17 — Corrección MULTI_QUOTE: el tipo efectivo pasa a ser autoritativo

### Incidente observado

Una nueva reproducción manual mostró que la solicitud estaba claramente en **Votación de cotizaciones**, pero al pulsar **Corregir / reenviar** aparecía el formulario SIMPLE con `Monto`, `Proveedor` y un solo soporte. El backend luego rechazaba el reenvío porque el payload intentaba degradar el flujo múltiple a sencillo.

La primera corrección había restaurado `requestType` desde el draft, pero eso no era suficiente: el formulario legacy seguía usando directamente el estado React `requestType` en render, validaciones y construcción del payload.

### Corrección consolidada

Se introduce el concepto frontend temporal `effectiveRequestType`:

```text
si existe draft:
    tipo efectivo = tipo canónico/inferido de la solicitud
si es nueva solicitud:
    tipo efectivo = pestaña seleccionada
```

Durante una corrección ese tipo efectivo gobierna:

- qué editor se renderiza;
- validación de soportes;
- `request_type` enviado al backend;
- `quotation_options`;
- carga de archivos.

El tipo de la solicitud se muestra como dato de solo lectura durante la corrección. No se permite cambiar SIMPLE ↔ MULTI_QUOTE dentro de **Corregir / reenviar**.

---

## 2026-08-17 — Enlaces de correo local alineados con Docker Compose

Se corrigió la desalineación entre `PUBLIC_URL` y el frontend Docker local: Compose usa `http://localhost:3000` para enlaces nuevos de correo y mantiene `localhost:5173` solo como origen permitido para Vite directo.

---

## 2026-08-17 — Google SMTP local y Brevo en producción

Se formaliza Google/Gmail SMTP para local/desarrollo y Brevo HTTPS API para producción. Las credenciales viven únicamente en backend y existe `python -m scripts.test_email --to <correo>` para diagnosticar transporte.

---

## 2026-08-17 — Aislamiento del estado de corrección y reparación de request_type

La pestaña SIMPLE/MULTI_QUOTE solo representa intención al crear una nueva solicitud. Al corregir, el editor deriva el tipo desde la solicitud/evidencia durable. Alembic `0003` repara filas legacy con evidencia MULTI_QUOTE y flag SIMPLE.

---

## 2026-08-17 — Administrador del sistema con política por ambiente

`ENVIRONMENT=production` limita la cuenta técnica a `config:manage` + `requests:read`; fuera de producción obtiene todos los permisos atómicos activos para pruebas end-to-end.

---

## 2026-08-17 — IAM configurable y segregación de la cuenta técnica

Se adopta el modelo Usuario → Grupo → Rol → Permiso con roles/permisos directos y cargos descriptivos. Los cinco permisos iniciales son `requests:read`, `requests:create`, `requests:approve`, `requests:close` y `config:manage`.

---

## 2026-08-17 — Hardening FastAPI

Se centraliza configuración con Pydantic Settings, Argon2, Alembic fuera del lifespan, `TestClient`, separación de modelos/routers y entrypoint Docker con migración/bootstrap antes de Uvicorn.

---

## 2026-08-17 — Consola gráfica de Accesos

Se agrega Configuración → Accesos para Usuarios, Grupos, Roles, Permisos, Cargos, asignaciones y permisos efectivos.

---

## 2026-08-17 — Deuda funcional mantenida explícitamente

Pendientes separados:

- fórmula exacta del motor de aprobación;
- quorum/empate de votación de cotizaciones;
- edición estructural de rondas MULTI_QUOTE;
- retiro de `UserRole`, `can_*`, `/api/users` legacy y ramas legacy;
- modularización completa de `frontend/src/main.jsx`;
- outbox/retry persistente de correo.

---

## 2026-08-17 — Documentación como parte del Definition of Done

Constitución, specs, planes, criterios, README, prompt maestro, docs, HISTORY y CHANGELOG son artefactos gobernados.

---

## 2026-08-17 — Terminología Usuario / Usuarios

El término canónico del módulo de cuentas es **Usuario / Usuarios**.

---

## 2026-08-17 — Clasificación Área + Categoría

Área representa la unidad organizacional asociada al gasto y Categoría la naturaleza del bien/servicio. Son catálogos independientes.

---

## 2026-08-17 — Retiro del dominio inmobiliario

Se retiraron del modelo activo conceptos específicos de apartamentos, propiedad y relaciones usuario-apartamento.
