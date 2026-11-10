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
- `.specify/pines/TASK-001.json`: la línea base del pin —hash, símbolos
  públicos, imports y foto del árbol— tal como la escribió 0.1.0 al empezar
  `TASK-001`.
- `.specify/snapshots/TASK-001/0` y `/1`: dos instantáneas de la tarea
  (`archivos.txt` más la copia de sus archivos), la del estado previo a
  implementarla y la de un intento fallido.

## Qué se dejó fuera, y por qué

`clarifications.json`, `enriquecimientos.json`, `informes.json`, `cache/`,
`checkpoints/` y los `.md` gemelos. Tampoco están `src/` ni `tests/` del
proyecto, que sumaban la mayor parte del peso: se materializan restaurando un
snapshot, y por eso `rollback --restore TASK-001` funciona sobre el fixture
recién copiado.

Sin esos archivos `validate` no tiene qué comparar, pero conserva la línea
base y no la rehace. Con el snapshot 0 restaurado —el estado exacto que
fotografió la línea base— la validación sale limpia; con el 1, que añadía
`Caja.descuento`, avisa de un cambio de cuerpo en `src/productos.py`. Ese es
el comportamiento de 0.1.0 y lo que la prueba comprueba.

## Cómo se generaron el pin y los snapshots

No salen del ciclo original: aquel proyecto se creó en un temporal y no se
conservó su código. Se generaron con el código del tag `v0.1.0` en un
worktree limpio, llamando a sus propias funciones —`pin.asegurar_baseline`
y `rollback.tomar`— sobre un `src/productos.py` mínimo, con las entidades de
§6 (productos, ventas, movimientos y caja) y los cuerpos sin implementar.
Lo que importa es el formato, que es el de 0.1.0; el contenido de ese archivo
no es el del proyecto original, que se perdió.

No se regenera en CI a propósito: si lo generara la versión actual dejaría de
probar compatibilidad, que es justo lo que se quiere vigilar.
