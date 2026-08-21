# Runtime del frontend: sesión, navegación y requests

## Objetivo

Evitar vistas privadas parciales, loops de red y mutaciones implícitas.

## Guard de sesión

`auth-route-guard.js` protege las superficies privadas basadas en hash. Regla:

```text
sin access_token + hash privado
→ limpiar hash
→ renderizar Login
```

Si una llamada autenticada devuelve 401 con token almacenado:

```text
limpiar sesión local
limpiar ruta privada
volver a Login
```

El login fallido no debe crear un loop de redirección.

## Gobernador de requests

`request-governor.js` protege GET del API frente a duplicación accidental:

- una llamada idéntica en vuelo se comparte;
- repeticiones automáticas recientes pueden reutilizar JSON;
- mutaciones invalidan la caché;
- una interacción humana reciente puede forzar lectura fresca;
- auth, adjuntos y enlaces tokenizados quedan excluidos cuando la reutilización sería incorrecta.

La ventana de caché es una optimización de frontend, no una garantía de consistencia del backend.

## Política de polling

No usar `setInterval`/`setTimeout` como mecanismo de sincronización por defecto. Si una feature necesita polling:

1. justificarlo en su Spec;
2. usar frecuencia razonable;
3. detenerlo al desmontar;
4. deduplicar requests;
5. no mutar datos como efecto del polling.

## Formularios de administración

Las selecciones son estado local. Un click/select no debe emitir PATCH/PUT/POST. El usuario confirma con Guardar cambios.

## Recargar

Un botón explícito de Recargar debe poder consultar al servidor aunque exista una respuesta automática reciente.
