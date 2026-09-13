---
name: planificar-incremento
description: Planifica un incremento de trabajo para TaskFlow contra el contrato y las decisiones de ingeniería del repositorio, y escribe el plan en docs/. Solo planifica: no implementa código, no instala dependencias ni toca la base de datos.
---

# planificar-incremento

Produce un documento de plan en `docs/`, siguiendo el mismo procedimiento con
el que se armó `docs/plan-persistencia.md`. No ejecuta el plan: esta skill
planifica, no implementa.

## Contra qué documentos se planifica

Antes de escribir una sola línea del plan, leer y citar explícitamente:

- `docs/contrato-api.md` — fija el comportamiento observable (endpoints,
  códigos de estado, esquemas, orden de listas, normalización de texto) que
  el incremento debe respetar o implementar. Citar la sección exacta
  (`## Salud`, `## Estados`, `## Proyectos`, `## Tareas v1`,
  `## Tareas v2: Fechas Límite`, `## Esquemas de Respuesta`, etc.) de la que
  depende cada parte del plan.
- `docs/decisiones-ingenieria.md` — fija decisiones de ingeniería del equipo
  no deducibles del código (base de datos, migraciones, pruebas, datos
  locales). Ningún incremento puede proponer algo que lo contradiga.
- `CLAUDE.md` — fija los comandos canónicos y las reglas no negociables del
  repositorio (Postgres real para tests de persistencia, nunca `.env`, nunca
  debilitar un test existente).
- El estado real del código y del repositorio en el momento de planificar
  (qué existe ya, qué falta), nunca supuesto de memoria: revisar con
  `git log --oneline`, el árbol de archivos relevante y, si aplica,
  `uv run alembic current` para saber en qué revisión está la base, sin
  aplicar ninguna migración durante la planificación.

## Dónde y cómo se escribe el resultado

- El plan se escribe como un archivo nuevo en `docs/`, nunca en la raíz del
  repositorio ni en `evidencias/`.
- El nombre del archivo dice de qué es el plan, con el mismo patrón que
  `docs/plan-persistencia.md`: `docs/plan-<tema-en-kebab-case>.md`. El tema
  es el sustantivo del incremento a planificar (por ejemplo,
  `docs/plan-proyectos.md` para un plan sobre el recurso Proyectos), nunca
  un nombre genérico como `plan.md` o `plan-nuevo.md`.
- Si ya existe un plan para ese mismo tema, se continúa o se actualiza ese
  archivo en vez de crear uno paralelo; no coexisten dos planes para el
  mismo tema.

## Forma del plan

El documento resultante declara, en este orden:

1. **Fuentes**: lista explícita de los documentos citados arriba, igual que
   hace `docs/plan-persistencia.md` en su sección "Fuentes".
2. **Estado de partida**: qué existe hoy en código, infraestructura y tests,
   verificado contra el repositorio real, no supuesto.
3. **Fuera de alcance**: declarado de forma explícita y nombrando lo que
   queda afuera, no como omisión silenciosa. Si el ticket o el encargo no
   menciona algo que podría parecer parte del incremento, se nombra aquí
   como excluido en vez de dejarlo ambiguo.
4. **Incrementos numerados**: cada incremento es confirmable por sí solo y
   no se encadena el siguiente sin aprobación explícita (misma regla de
   ejecución que `docs/plan-persistencia.md`). Cada incremento declara:
   - Qué cambia, en términos concretos de código/infraestructura/tests.
   - **Su propia comprobación ejecutable**: un comando o secuencia de
     comandos real del repositorio (`uv run pytest -q`, `uv run ruff check .`,
     `uv run alembic current`, etc.) que otra persona pueda correr para
     verificar ese incremento puntual, no una descripción en prosa de cómo
     se vería el éxito.
5. **Reglas de ejecución**: las mismas tres reglas de `docs/plan-persistencia.md`
   (cada incremento es confirmable por sí solo; no se encadena el siguiente
   sin aprobación explícita; no se modifican `docs/contrato-api.md`,
   `docs/decisiones-ingenieria.md`, `CLAUDE.md`, `.gitignore` ni `.env`, y no
   se abre `.env`), ajustadas si el encargo lo pide explícitamente.

## Ninguna decisión queda aplazada

Si para escribir un incremento hace falta decidir algo que no se puede
resolver con lo que ya hay en el repositorio (el contrato, las decisiones de
ingeniería, el código existente), esa decisión **se pregunta al usuario en
este momento**, antes de seguir escribiendo el plan. Nunca se redacta en
condicional ("se podría hacer X o Y", "probablemente convenga Z") ni se deja
como nota abierta para más adelante dentro del mismo plan. Cada decisión que
el plan declare debe venir acompañada de la razón por la que encaja con el
estado actual del repositorio, igual que hace
`docs/plan-persistencia.md` en el Incremento 2.

## Límite de la skill

Esta skill **planifica y no implementa**:

- No crea ni modifica archivos de código de la aplicación (`app/`, `tests/`).
- No instala ni agrega dependencias (no corre `uv add`, `uv sync`, ni edita
  `pyproject.toml` o `uv.lock`).
- No toca la base de datos: no crea, aplica ni revierte migraciones de
  Alembic, y no modifica datos.
- Su único artefacto de salida es el archivo de plan en `docs/`. Cualquier
  comando que se ejecute durante la planificación es de solo lectura
  (`git log`, `git status`, lectura de archivos, `uv run alembic current`),
  nunca uno que cambie el estado del repositorio o de la base.

## Procedimiento al invocarla

1. Pedir o confirmar el tema del incremento a planificar si no viene dado.
2. Leer `docs/contrato-api.md`, `docs/decisiones-ingenieria.md`, `CLAUDE.md`
   y el estado real del repositorio (historial, árbol de archivos, revisión
   de Alembic) relacionados con ese tema.
3. Identificar toda decisión que el plan necesite y que no se resuelva con
   esas fuentes; preguntarlas todas antes de escribir el documento.
4. Redactar el plan en `docs/plan-<tema>.md` con la forma descrita arriba:
   fuentes, estado de partida, fuera de alcance, incrementos numerados con
   comprobación ejecutable cada uno, y reglas de ejecución.
5. Mostrar el documento completo al usuario antes de guardarlo.
6. Guardar el archivo solo tras su confirmación. No tocar código,
   dependencias ni la base de datos en ningún paso.
