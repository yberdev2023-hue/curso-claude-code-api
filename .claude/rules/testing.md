# Convenciones de testing de TaskFlow

## Dónde viven los tests

Los tests viven todos juntos, separados del código de la aplicación, en un
único directorio de pruebas. Hay un archivo por recurso o por tema (salud,
catálogo de estados, migraciones, proyectos, tareas) — nunca un archivo por
endpoint, ni un solo archivo para todo. Las fixtures que comparten varios
archivos (la conexión a la base, el helper para invocar Alembic como lo
haría alguien desde la terminal, y el borrado de las tablas gestionadas
entre pruebas) viven centralizadas en un único módulo de fixtures, para que
ningún archivo de test duplique esa lógica.

## Cómo se nombran

- El archivo: `test_<recurso o tema>`, con el sustantivo de lo que cubre.
- La función: `test_<acción>_<recurso>_<condición>_<resultado esperado>`,
  siempre en español, siempre describiendo las tres cosas en el nombre —
  qué se hace, bajo qué condición, y qué debería pasar — para que el
  nombre solo ya diga qué se rompió, sin tener que leer el cuerpo. Ejemplos
  reales del patrón: crear una tarea con el título vacío y esperar `422`;
  borrar un proyecto que tiene tareas y esperar `409`; pedir una tarea por
  un id inexistente y esperar `404`.
- Las funciones casi nunca llevan docstring propio: el nombre alcanza. Los
  docstrings se reservan para el encabezado del archivo (contra qué corre,
  qué decisión de ingeniería sigue) y para las fixtures compartidas.

## Cómo se prepara y se revierte la base entre pruebas

- Los tests que ejercitan persistencia corren siempre contra Postgres real,
  nunca contra SQLite ni mocks.
- Cada archivo de test que ejercita la API declara una fixture de alcance
  por-test, marcada `autouse`, que antes de cada test: descarta el engine
  cacheado de la aplicación (una conexión asíncrona queda atada al event
  loop en el que se creó, y el runner de tests abre uno nuevo por test),
  borra todas las tablas gestionadas por las migraciones más la tabla de
  versiones de Alembic, y migra hasta la cabeza actual invocando Alembic
  como un proceso aparte. Al terminar el test, la misma fixture revierte:
  vuelve a borrar esas tablas y vuelve a descartar el engine, para que el
  test siguiente arranque de una base vacía y no herede nada del anterior.
- El archivo de test dedicado a las migraciones es la excepción: su
  fixture solo borra y no migra automáticamente, porque lo que cada uno de
  sus tests prueba es justamente el propio proceso de subir o bajar una
  revisión puntual — migrar antes de tiempo escondería lo que se quiere
  verificar.
- Una conexión de vida corta, una por test, da acceso directo a la base
  cuando hace falta preparar un dato que la API todavía no expone (por
  ejemplo, insertar una fila para probar una restricción antes de que
  exista el endpoint que la crearía) o verificar el estado real de una
  tabla o columna.
- Consecuencia práctica y ya comprobada varias veces: correr la suite
  completa dos veces seguidas, o simplemente correrla una vez, deja la
  base sin ninguna migración aplicada al terminar — el último test en
  ejecutarse también revierte lo suyo. Antes de usar la API a mano contra
  un servidor corriendo, después de haber corrido los tests, hay que
  volver a migrar.

## Invariantes del contrato que ningún test puede dejar de cubrir

La matriz mínima de tests que fija el contrato de la API exige, como
mínimo:

- Salud del servicio.
- CRUD feliz de proyectos y de tareas.
- Búsqueda por id inexistente.
- Título vacío y con solo espacios ASCII, y un invisible Unicode que
  atraviesa un simple recorte de espacios.
- Referencia a un proyecto o a un estado inexistente al crear una tarea.
- Borrado de un proyecto que todavía tiene tareas.
- Filtros de listado solos y combinados entre sí.
- Orden estable: dos llamadas idénticas devuelven los ids en la misma
  posición.
- Esquema de respuesta exacto: los campos declarados, ni uno de más.
- Migración desde una base vacía, y el rollback de cada incremento
  posterior al primero.
- Que el catálogo cerrado exista después de migrar, y que migrar dos
  veces no lo duplique.
- Una fecha límite omitida, válida, sin zona horaria, vencida, futura, y
  sobre una tarea ya completada.
- Un valor de prioridad omitido, válido dentro del rango permitido, y
  fuera de ese rango.

Los tests pueden cubrir casos adicionales a estos. Lo que no pueden es
debilitar ninguna de estas invariantes para conseguir un resultado verde.

## Una que se aprendió a la fuerza

Un test que existe para probar que algo falla —un valor inválido que debe
rechazarse, una restricción que debe impedir un borrado, una migración que
debe revertirse limpio— no se toca para que un cambio nuevo lo deje pasar.
Si el comportamiento que ese test protege de verdad cambió a propósito, el
orden es siempre el mismo: primero se actualiza el documento que fija el
contrato, después se ajusta el test para reflejar el nuevo comportamiento
acordado, y los dos cambios van en commits separados. Ajustar el test
primero, o en el mismo commit que el código que lo hace pasar, es
exactamente el atajo que deja pasar una regresión sin que nadie la note.
