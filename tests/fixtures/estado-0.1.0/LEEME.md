# Estado de ejemplo creado con 0.1.0

Fixture de compatibilidad: `.specify/` y los artefactos tal como los escribió
el tag `v0.1.0` (commit `10cf434`), sin retocar. La prueba
`tests/test_compatibilidad_formato.py` lo copia a un directorio temporal y lo
abre con la CLI actual para detectar cualquier ruptura de esquema.

Se generó recorriendo el ciclo completo con esa versión: `init`, `enrich`,
`specify`, las 25 aclaraciones, `plan`, `tasks`, `analyze`, `build`, `test` y
el cierre de `TASK-001`.

## Qué incluye

- `.specify/specs.json`, `planes.json`, `tareas.json` y
  `requerimientos.json`: los índices del estado.
- `.specify/current_task.json`: legado de 0.1.0. `init` lo sembraba con
  `current_spec` y `current_phase` en `null` y nadie lo volvía a tocar; se
  conserva porque el fixture reproduce lo que escribió el tag, pero la CLI
  actual ya no lo crea ni lo lee. El estado vivo es
  `.specify/memory/current_task.json` (abajo).
- `.specify/planes/PLAN-001.json` y `.specify/tareas/TASKS-PLAN-001.json`:
  plan técnico y desglose, en el formato de 0.1.0 —solo JSON—. La CLI actual
  escribe ese JSON y además el `.md` legible al lado, igual que hace con la
  SPEC y el informe.
- `specs/SPEC-001.json` y su gemelo `SPEC-001.md`: la SPEC aprobada, en las
  dos formas que escribe 0.1.0 —máquina y legible—.
- `.specify/enriquecimientos.json`: el ENR validado del que salieron los 21
  requerimientos, con sus 22 elementos y la procedencia de cada uno.
- `.specify/clarifications.json`: las aclaraciones de `SPEC-001` con su
  estado, su respuesta y su historial.
- `.specify/memory/execution_history.jsonl`: el historial, que es lo que lleva
  el tablero a la fase 🧪.
- `.specify/memory/current_task.json`: el estado que `build` sincroniza al
  cerrar cada tarea: plan, SPEC, fase, total, índice del último éxito, tarea
  en curso, racha de fallos, último checkpoint y `run_id`.
- `.specify/checkpoints/TASK-001.json`: el checkpoint durable de la tarea
  cerrada (§13.4): fecha, SPEC, plan, fase, siguiente tarea, archivos con sus
  hashes, pruebas y decisiones.
- `.specify/pines/TASK-001.json`: la línea base del pin —hash, símbolos
  públicos, imports y foto del árbol— tal como la escribió 0.1.0 al empezar
  `TASK-001`.
- `.specify/snapshots/TASK-001/0` y `/1`: dos instantáneas de la tarea
  (`archivos.txt` más la copia de sus archivos), la del estado previo a
  implementarla y la de un intento fallido.

## Qué se dejó fuera, y por qué

`informes.json`, `cache/` y `spec_history/`. Tampoco están `src/` ni
`tests/` del proyecto, que sumaban la mayor parte del peso: se materializan
restaurando un snapshot, y por eso `rollback --restore TASK-001` funciona
sobre el fixture recién copiado.

`spec_history/` no está porque aparece al revisar una SPEC, y el fixture
conserva la 1.0.0 sin revisar; la prueba lo crea sobre su copia temporal.

Sin esos archivos `validate` no tiene qué comparar, pero conserva la línea
base y no la rehace. Con el snapshot 0 restaurado —el estado exacto que
fotografió la línea base— la validación sale limpia; con el 1, que añadía
`Caja.descuento`, avisa de un cambio de cuerpo en `src/productos.py`. Ese es
el comportamiento de 0.1.0 y lo que la prueba comprueba.

## Cómo se generó el enriquecimiento

`enriquecimientos.json` sí salió del ciclo real, no de una reconstrucción: el
mismo `enrich "Quiero un dashboard para gestionar un kiosco"` del tag
`v0.1.0` produce `ENR-001` con los 22 elementos —objetivo, 5 entidades, 5
funcionalidades, 4 mejoras, 3 faltantes y 4 exclusiones—, y `enrich --accept
ENR-001` los convierte en los 21 requerimientos del fixture: mismos
identificadores, textos, procedencias y estados, uno a uno. Se generó en un
proyecto aparte y solo se copió el archivo; el estado del fixture no se tocó.

Con él, `specify --revise SPEC-001 --motivo «…»` funciona. Conviene saber qué
hace 0.1.0: re-deriva la SPEC del ENR, así que una revisión sube la versión a
1.0.1 y conserva los 14 requerimientos, las 5 entidades y las 4 exclusiones,
pero deja atrás lo aclarado y la aceptación de los requerimientos. No es una
pérdida del fixture: es el diseño del comando, y la prueba lo deja escrito.

## Cómo se generaron las aclaraciones, el checkpoint y el estado

Estas piezas no venían en el fixture y se reconstruyeron con el código del tag
`v0.1.0`, que es el que fija el formato:

- `clarifications.json` salió de `core.clarify.detectar` sobre `SPEC-001` con
  sus supuestos, RNF, reglas y dependencias devueltos a «pendiente», y de
  `responder` aplicando la misma respuesta que la SPEC ya registraba («Sí,
  confirmado»). Al terminar, `SPEC-001.json` queda idéntico al original byte
  a byte: el registro cuadra con lo que ya estaba escrito en la SPEC. De las
  25 aclaraciones del ciclo original solo seis dejaron rastro (CLA-001 a
  CLA-006); las demás no se pueden reconstruir sin inventarlas.
- `checkpoints/TASK-001.json` es el evento `checkpoint` que ya estaba en el
  journal, pasado por `core.checkpoints.guardar`.
- `memory/current_task.json` lo escribió `build._sincronizar_estado` con el
  plan, la SPEC y las tareas del fixture.
- `specs/SPEC-001.md` y el `updated_at` del índice son los que escribió la
  propia acción de `clarify`, no se tocaron a mano.

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
