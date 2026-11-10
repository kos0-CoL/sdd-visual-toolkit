# Estado de ejemplo creado con 0.1.0

Fixture de compatibilidad: `.specify/` y los artefactos tal como los escribió
el tag `v0.1.0` (commit `10cf434`), sin retocar. La prueba
`tests/test_compatibilidad_formato.py` lo copia a un directorio temporal y lo
abre con la CLI actual para detectar cualquier ruptura de esquema.

Se generó recorriendo el ciclo completo con esa versión: `init`, `enrich`,
`specify`, las 25 aclaraciones, `plan`, `tasks`, `analyze`, `build`, `test` y
el cierre de `TASK-001`.

## Qué incluye

- `.specify/specs.json`, `planes.json`, `tareas.json`, `requerimientos.json`,
  `current_task.json`: los índices del estado.
- `.specify/planes/PLAN-001.json` y `.specify/tareas/TASKS-PLAN-001.json`:
  plan técnico y desglose.
- `specs/SPEC-001.json`: la SPEC aprobada.
- `.specify/memory/execution_history.jsonl`: el historial, que es lo que lleva
  el tablero a la fase 🧪.
- `.specify/pines/TASK-001.json`: pin de la tarea cerrada.

## Qué se dejó fuera, y por qué

`clarifications.json`, `enriquecimientos.json`, `informes.json`, `cache/`,
`checkpoints/`, `snapshots/` y los `.md` gemelos. No hacen falta para leer el
estado y sumaban más de la mitad del peso. La consecuencia: `validate` sale
con «sin línea base previa», porque los archivos de la tarea no están. Si una
prueba futura necesita ese camino, hay que regenerar el fixture completo con
`v0.1.0` y recortarlo otra vez.

No se regenera en CI a propósito: si lo generara la versión actual dejaría de
probar compatibilidad, que es justo lo que se quiere vigilar.
