# Terminología funcional

Este documento define los términos visibles que debe utilizar la aplicación para mantener un lenguaje consistente y neutral entre distintos tipos de organización.

## Usuario

La aplicación utiliza **Usuario** como término canónico para cualquier cuenta que interactúa con el sistema.

Ejemplos de uso correcto:

- Usuarios
- Crear usuario
- Editar usuario
- Buscar usuario
- Usuario activo
- Usuario inactivo
- Perfil del usuario
- Permisos del usuario

La interfaz no debe utilizar **Persona** o **Personas** como nombre del módulo de administración de cuentas.

A nivel técnico, el backend ya utiliza la entidad `User` y los endpoints `/api/users`, por lo que este cambio corresponde principalmente a la terminología funcional y de interfaz.

## Área

**Área** representa la unidad, departamento o función organizacional responsable de o relacionada con el gasto.

Ejemplos:

- Administración
- Operaciones
- IT
- Mantenimiento
- Marketing

## Categoría

**Categoría** representa la naturaleza del bien o servicio adquirido.

Ejemplos:

- Equipos
- Servicios / Consultoría
- Insumos
- Software / Licencias
- Mobiliario
- Capacitación

Área y Categoría son catálogos independientes y pueden relacionarse de forma configurable.

## Regla de consistencia

Los nuevos componentes, pantallas, documentación y mensajes deben utilizar estos términos canónicos:

- **Usuario**, no Persona.
- **Área**, para la unidad organizacional.
- **Categoría**, para la naturaleza del gasto.
