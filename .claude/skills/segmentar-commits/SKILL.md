---
name: segmentar-commits
description: Propone cómo repartir los cambios pendientes del repositorio en commits de una sola intención cada uno, con Conventional Commits y en un orden verificable, a partir del estado real del repositorio (git status y git diff --stat). No ejecuta ningún commit: muestra la propuesta y espera aprobación explícita.
---

# segmentar-commits

Propone un reparto de los cambios pendientes en commits, siguiendo el mismo
criterio con el que se repartió la implementación del recurso Proyectos. No
ejecuta el reparto: esta skill propone, no confirma nada por sí sola.

## Punto de partida: el estado real del repositorio

- Primer paso, siempre: correr `git status --short` y `git diff --stat`.
  Ambos son de solo lectura. El primero da la lista de archivos tocados
  (nuevos, modificados, borrados); el segundo da el resumen por archivo
  (líneas agregadas/quitadas), no el contenido.
- Se usa exclusivamente esa salida como mapa del cambio. No se asume qué
  cambió a partir de lo dicho antes en la conversación ni de memoria: si el
  estado real difiere de lo recordado, manda el estado real.
- Esta skill no corre `git diff` sin `--stat` (el diff completo) como parte
  de su procedimiento: el mapa de archivos alcanza para decidir el reparto.
  Si hace falta ver el contenido de un archivo puntual para decidir en qué
  commit va un fragmento ambiguo, se lee ese archivo con la herramienta de
  lectura de archivos, no con un diff completo de todo el repositorio.

## Reparto en commits

- Cada commit tiene una sola intención: agrupa los archivos (o fragmentos de
  archivo) que juntos implementan un único cambio de comportamiento o una
  única tarea de mantenimiento. Dos cambios de intención distinta no
  comparten commit aunque toquen el mismo archivo.
- El orden de los commits importa: cada uno, aplicado en la secuencia
  propuesta, deja el repositorio en un estado comprobable — corren limpio
  (o al menos no rompen) los comandos canónicos del repositorio
  (`uv run pytest -q`, `uv run ruff check .`) tal como quedarían después de
  ese commit puntual, no solo al final de la serie completa. Si dos cambios
  son interdependientes de forma que ninguno deja el repositorio en un
  estado consistente por sí solo, van en el mismo commit.
- Cuando un mismo archivo mezcla código de más de una intención, el reparto
  lo dice explícitamente: no alcanza con nombrar el archivo, hay que decir
  qué fragmento (función, clase, bloque) va en cada commit.

## Elección del prefijo (Conventional Commits)

- El prefijo se elige por lo que el commit **hace** — su efecto observable
  puntual —, nunca por el tipo de archivo que toca. Por ejemplo:
  - Agregar un test nuevo para una capacidad que **ya existe** en el
    código: `test:`.
  - Agregar código de producción nuevo, aunque venga acompañado de sus
    propios tests (como es la norma en este repositorio): `feat:` o `fix:`
    según corresponda, no `test:` solo porque también toca `tests/`.
  - Reorganizar código existente sin cambiar comportamiento observable
    (por ejemplo, mover un helper duplicado a un módulo compartido):
    `refactor:`.
  - Tocar solo documentación (`docs/`, o `CLAUDE.md` cuando el ticket lo
    permite explícitamente): `docs:`.
  - Cambios de configuración, dependencias o infraestructura sin efecto en
    el comportamiento de la API: `build:` o `chore:` según corresponda.
- Un commit que mezcla, por ejemplo, un archivo de test y uno de código de
  producción para la misma intención no se dispersa en dos prefijos: se
  elige el prefijo de la intención principal (normalmente `feat`/`fix`),
  igual que ya hace el historial de este repositorio (por ejemplo, el
  commit `0eb905e`, `feat: conecta GET /states a Postgres`, que toca tanto
  `app/main.py` y `app/db.py` como `tests/test_states.py`).

## Mostrar y esperar aprobación

- El resultado de esta skill es una propuesta: para cada commit, la lista
  de archivos (o fragmentos) y el mensaje completo en Conventional Commits.
- Se muestra la propuesta completa al usuario y se espera su aprobación
  explícita antes de ejecutar ningún `git add` ni `git commit`.
- Aprobar el reparto no equivale a pedir que se ejecute: si el usuario
  aprueba la propuesta pero no pide explícitamente que se confirmen los
  commits, la skill se detiene después de mostrarla.

## Límite de la skill

- Esta skill propone el reparto; no lo ejecuta por sí sola. `git add` y
  `git commit` solo corren después de una instrucción explícita del
  usuario para hacerlo, nunca antes de haber mostrado el mensaje completo
  de cada commit.
- No modifica el contenido de ningún archivo: si un archivo mezcla
  intenciones, el reparto se logra con staging parcial (`git add -p`, o un
  patch extraído a mano) sobre el contenido ya existente, no reescribiendo
  el archivo.
- No corre `git push`.

## Procedimiento al invocarla

1. Correr `git status --short` y `git diff --stat`. Usar exclusivamente
   esa salida como estado de partida.
2. Agrupar los archivos y fragmentos por intención única, y ordenar los
   grupos de forma que cada uno, aplicado en ese orden, deje el
   repositorio en un estado comprobable.
3. Para cada grupo, elegir el prefijo de Conventional Commits según lo que
   ese commit hace, no según qué archivos toca.
4. Redactar el mensaje completo de cada commit.
5. Mostrar al usuario el reparto completo: por cada commit, los
   archivos/fragmentos que incluye y el mensaje propuesto.
6. Esperar aprobación explícita para ejecutar. No correr `git add` ni
   `git commit` hasta obtenerla.
