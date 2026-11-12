# SDD Visual Toolkit v0.1.6

Versión de mantenimiento centrada en el IDE: la extensión ya arranca en una
carpeta vacía, la paleta avisa y se puede cortar, y la pasada manual quedó
registrada casilla por casilla. Es compatible con proyectos creados con 0.1.0
a 0.1.5: no cambian el formato de `.specify/` ni el protocolo MCP.

Cada release adjunta `sdd-visual-toolkit-0.1.6.vsix`, empaquetado con `vsce`
desde el mismo commit que el tag:

```bash
code --install-extension sdd-visual-toolkit-0.1.6.vsix
```

## Corregido

- **`SDD: Inicializar proyecto` arranca en una carpeta vacía.** Con el
  `cliPath` por defecto (`cli/main.py`, relativo a la carpeta abierta) python
  respondía `can't open file '<carpeta>/cli/main.py'`, justo en el caso en el
  que todavía no hay proyecto ni copia del toolkit a la que apuntar. Ahora la
  CLI se resuelve en tres pasos: la ruta configurada, el paquete instalado con
  `pip install -e .` (`python -m cli.main`) y, si tampoco, un aviso que dice
  qué ajustar en `sddToolkit.cliPath` en vez del traceback.
- **Dos filas de `Fases y tareas` ejecutaban una orden imposible**:
  `Progreso` pasaba el SPEC-ID a `tasks` (que pide PLAN-ID) y `Pruebas`
  llamaba a `reporte` sin argumento. Ahora son `tasks --list PLAN-001` y
  `reporte TASK-001` (o `--history PLAN-001` si la etiqueta no trae tarea), y
  el arnés comprueba el argv de esas filas, no solo su etiqueta.
- **El clic derecho sobre `📍 Fase`** no ofrecía *Abrir artefacto de la fase*:
  la fila comparaba `🧪 Pruebas` contra las claves de `flujo`. Ahora compara
  sin emoji, tildes ni mayúsculas.
- **`SDD: Aclarar SPEC` valida el SPEC antes de abrir el terminal**: con un
  `SPEC-999` inexistente la notificación trae el `⛔` y `Ver salida`, en lugar
  de dejarlo al fondo de una terminal que se abre para nada.
- **`init` deja de sembrar restos**: no crea `plans/` ni `tasks/` en la raíz
  (nadie escribía ahí), no deja `current_task.json` ni
  `execution_history.jsonl` vacíos, respeta `--root` como el resto de comandos
  y se niega a anidar un `.specify/` cuando ya hay un proyecto por encima.
- **`specify` y `restricciones` avisan con `⛔`** cuando el ID no existe, en
  vez de terminar con un traceback.

## Añadido

- **La paleta se puede seguir y cortar**: cada comando muestra una
  notificación de progreso con la orden, se puede cancelar (SIGTERM, para que
  el estado JSON quede entero) y tiene un tope configurable en
  `sddToolkit.timeoutMinutos` que corta también a los procesos hijos.
- **`toolkit comandos --verificar`** revisa lo ya generado sin reescribirlo y
  **`--regenerar`** rehace solo los clientes que ya tenían comandos; `status`
  y la vista avisan cuando las skills instaladas apuntan a una ruta que ya no
  existe.
- **Herramientas para la pasada manual**: `scripts/preparar-manual.sh` deja el
  entorno listo en un paso (con `--solo-verificar` para mirarlo sin
  rehacerlo), `scripts/verificar_vsix.py` revisa el paquete de la extensión y
  `tests/js/arnes_extension.js` carga el `extension.js` real contra un stub de
  `vscode`.
- **La primera pasada dentro de un editor quedó registrada** en
  `ide/COMPATIBILIDAD.md` y `ide/PRUEBA-MANUAL.md`: 23 de 29 casillas de la
  extensión marcadas con lo observado en VS Code 1.142.0, más los hallazgos
  que todavía no se arreglan (el modo restringido desactiva la extensión en
  carpetas nuevas y los comandos de barra siguen sin probarse dentro de un
  chat).

## Verificación

- `python3 -m pytest tests/ -q` → 448 passed, 48 subtests passed.
- `node tests/js/arnes_extension.js` → 46/46 comprobaciones en verde.
- CI en verde en Python 3.11, 3.12, 3.13 y 3.14, más la instalación editable.
- `python3 scripts/verificar_release.py --previo 0.1.6` en verde antes de
  crear el tag.
- En el editor, con perfil aislado y carpeta vacía: `SDD: Inicializar
  proyecto` respondió `SDD: PROYECTO INICIALIZADO` y dejó `.specify/`,
  `.vscode/` y `specs/`; con un intérprete sin el paquete salió el aviso de
  qué ajustar.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.6/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.6/docs/RELEASES.md)
- Compatibilidad por entorno: [`ide/COMPATIBILIDAD.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.6/ide/COMPATIBILIDAD.md)
- Checklist de prueba manual: [`ide/PRUEBA-MANUAL.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.6/ide/PRUEBA-MANUAL.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.6/CONTRIBUTING.md)
