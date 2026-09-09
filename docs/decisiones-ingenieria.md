# Decisiones de Ingeniería de TaskFlow

Estas decisiones pertenecen al equipo. No todas pueden deducirse del código.

## Fuentes de verdad

- `docs/contrato-api.md` define el comportamiento observable. Una tarea solo lo
  modifica cuando el ticket dice explícitamente que cambia el contrato.
- `README.md` contiene los comandos canónicos del repositorio.

## Base de datos

- Los tests que ejercitan persistencia corren contra PostgreSQL. SQLite queda
  fuera porque no reproduce las mismas restricciones, tipos ni migraciones.
- El esquema cambia mediante migraciones de Alembic. No se crea con efectos al
  importar módulos.
- Cada migración implementa `upgrade` y `downgrade`, y se prueba en ambos
  sentidos antes de integrarse.

## Pruebas

- Una capacidad nueva comienza con un caso que falla por la ausencia de esa
  capacidad.
- No se debilita ni elimina un test existente para conseguir verde. Si el
  comportamiento acordado cambió, primero cambia el contrato y después el test,
  en un commit separado.

## Datos locales

- `.env` puede contener secretos. Claude no debe abrirlo, mostrarlo, editarlo ni
  añadirlo a Git.
- `.env.example` es la fuente permitida para conocer nombres de variables. Los
  valores reales se configuran fuera de la conversación.
