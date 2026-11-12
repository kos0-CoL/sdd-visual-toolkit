# Compatibilidad por entorno (§30) — RF-40

La compatibilidad se comprueba individualmente; no se asume. Cada entorno
tiene dos superficies independientes: la **extensión** (`ide/vscode/`, RF-39)
y los **comandos de barra** (`toolkit comandos`, RF-36). Una puede estar verde
y la otra no.

## Estado

| Entorno | Extensión | Comandos de barra |
|---|---|---|
| VS Code | ✅ `node --check` + `tests/test_ide.py` + `tests/test_extension_headless.py`; **visto en editor el 2026-11-11 (17 de 29 casillas)** | ✅ `.github/prompts/`, 14 archivos con la ruta absoluta y `comandos --verificar` en verde; **sin abrir el chat** |
| Cursor | ✅ compatible por diseño; sin prueba manual | ✅ `.cursor/commands/`; sin probar |
| Windsurf | ✅ compatible por diseño; sin prueba manual | ✅ `.windsurf/workflows/`; sin probar |
| Antigravity | ⚠️ pendiente de verificación | ⚠️ `.agents/skills/`; sin probar |
| Claude Code (CLI) | — no aplica: no es un IDE | ✅ `.claude/skills/`; sin probar |
| Solo terminal / CLI | — | — la CLI es completa sin IDE (RF-36) |
| Vía MCP | — | ✅ `tests/test_mcp.py` |

Ningún ✅ de la columna de comandos significa «visto funcionando». Significa
que el archivo se escribe en la ruta y con el formato que ese cliente
documenta, y que `tests/test_agent_commands.py` lo comprueba. Abrirlo dentro
del cliente sigue pendiente en todos.

La extensión solo usa APIs estables (commands, TreeView, StatusBar,
Terminal); Cursor, Windsurf y los demás basados en VS Code heredan esa base,
pero eso es «compatible por diseño», no una prueba.

## Qué falta para cerrarlo

Cada entorno se cierra igual: generar, abrir, mirar y anotar. `ide/PRUEBA-MANUAL.md`
tiene la lista casilla por casilla de VS Code y Antigravity. Generar los
comandos una vez en el proyecto:

```bash
toolkit comandos --cliente <cliente>
```

### VS Code

1. Instalar el `.vsix` de la última release (*Extensiones → … → Instalar
   desde VSIX…*). `toolkit init` ya deja `sddToolkit.cliPath` y
   `sddToolkit.python` en `.vscode/settings.json`; en proyectos creados antes,
   configúrelos a mano con la ruta absoluta a `cli/main.py`.
2. Comprobar que la paleta `SDD: …` ejecuta el comando y deja su salida en el
   canal `SDD Toolkit` (con notificación si falla; `clarify`, que pregunta
   por stdin, sigue en la terminal), que la vista `SDD → Fases y tareas`
   muestra la fase y el progreso reales, que `SDD → Flujo SDD` lista las
   nueve fases con su skill y su artefacto, lanza el comando al hacer clic y
   abre ese artefacto con el clic derecho, y
   que la barra de estado aparece con un proyecto y se oculta sin `.specify/`.
3. `toolkit comandos --cliente copilot` y verificar que `/sdd-status` aparece
   al escribir `/` en el chat y devuelve la salida de la CLI tal cual.

### Cursor

1. `toolkit comandos --cliente cursor`; los archivos quedan en
   `.cursor/commands/`.
2. `/sdd` debe aparecer en el chat. Lo que se escriba detrás del comando no
   llega como `$ARGUMENTS`, sino dentro del prompt: el agente tiene que
   leerlo y ponerlo al final del comando.
3. La extensión se prueba igual que en VS Code si el editor la acepta.

### Windsurf

1. `toolkit comandos --cliente windsurf`; quedan en
   `.windsurf/workflows/`.
2. `/sdd-plan` debe invocarse desde Cascade y ejecutar `plan` con el ID que
   se escriba detrás.

### Antigravity

1. `toolkit comandos --cliente antigravity`; quedan en `.agents/skills/`.
   `toolkit init` deja además las tareas `SDD: …` en `.vscode/tasks.json`: si
   Antigravity lee las tareas de VS Code, aparecen sin instalar nada (sin
   verificar).
   No se generan *workflows*: ese mecanismo está deprecado y la migración es
   hacia skills.
2. Aquí no hay comandos de barra: el agente ve las skills por nombre y
   descripción y elige. El manifiesto solo documenta `name` y `description`,
   así que `argument-hint` se ignora; el ID se pasa como texto en el pedido.
3. Verificar que las skills aparecen en el agente y que la ejecución de shell
   les permite correr la CLI.
4. Mientras no se verifique: usar la CLI (RF-36) o el MCP.

### Claude Code

1. `toolkit comandos --cliente claude`; quedan en `.claude/skills/`.
2. `/sdd-specify ENR-001` debe sustituir `$ARGUMENTS` y ejecutar
   `specify ENR-001`.

## Cómo se anota un resultado

Cuando un entorno se pruebe de verdad, se cambia su fila: el ✅ pasa a
`✅ verificado` con la versión del cliente y la fecha, y se deja una línea en
el registro. Si falla, se anota el síntoma y se degrada a CLI + `export`,
nunca se inventa estado.

| Fecha | Entorno y versión | Superficie | Resultado |
|---|---|---|---|
| 2026-11-11 | VS Code 1.142.0 · `sdd-toolkit.sdd-visual-toolkit@0.1.5` · arnés sin editor | extensión | ⚠️ parcial: 41/41 del arnés sobre `/tmp/sdd-manual`; no se abrió el editor |
| 2026-11-11 | VS Code 1.142.0 · perfil aislado con la extensión `0.1.5`, proyecto `/tmp/sdd-manual` recién preparado | extensión | ⚠️ parcial: **6 de 29 casillas** — barra de estado y su tooltip, `Fases y tareas`, `Flujo SDD` con tooltip, clic derecho→`Preview PLAN-001.md`, paleta `SDD: Estado + siguiente` (canal `SDD Toolkit`, código 0) y fallo `build PLAN-999` (`⛔ SDD: plan inexistente: PLAN-999`), clic derecho en el flujo (`Arquitectura`→`PLAN-001.md`, `Especificación`→`SPEC-001.md`) y en `📍 Fase`. **Hallazgo**: ese último no ofrecía nada, porque la fila comparaba `🧪 Pruebas` con las claves del flujo (`Pruebas`); arreglado en la misma pasada. Faltan: progreso/«Cancelar», tope, `pin` de dos datos (solo se vio el primer cuadro), vacíos y `Escape`, estado vacío, CLI rota |
| 2026-11-11 | VS Code 1.142.0 · perfil aislado con la `0.1.5` reempaquetada · `/tmp/sdd-manual` | `Fases y tareas` | ⚠️ parcial: **dos hallazgos** de la pasada manual — `Progreso` ejecutaba `tasks SPEC-001` (SPEC donde va PLAN-ID) y `Pruebas` llamaba `reporte` sin ID; el documento `export` además trae `plan_id` solo a veces. Arreglado con `tasks --list PLAN-001` y `reporte TASK-001`, tomando el plan de la navegación cuando falta. Tras reinstalar: los dos clics dan código 0 y escriben en el canal `SDD Toolkit`. El arnés no los vio porque solo comparaba etiquetas; ahora comprueba el argv de esas filas (46/46). Queda sin observar la píldora bloqueada: en este estado no hay ninguna |
| 2026-11-11 | VS Code 1.142.0 · perfil aislado, `0.1.5` reempaquetada · `/tmp/sdd-manual` con un intérprete envoltorio que duerme | extensión | ⚠️ parcial: **progreso y «Cancelar»** — `SDD: tablero` mostró la notificación a los ~400 ms (`SDD: tablero`) y desapareció con `(código 0)`; los clics rápidos no la muestran. `SDD: Correr pruebas` + `TASK-001` mostró `SDD: test TASK-001` con botón («Cancel» con la IU en inglés); al pulsarlo salieron `SDD: test cancelado`, la línea `(cancelado)` en el canal, ninguna notificación de error y la vista se refrescó sola. **Dos casillas más (10 de 29)**. Queda sin observar el corte con `pytest` en marcha: el `test` de este proyecto no lanza subproceso de pytest, así que la cancelación se probó con un envoltorio que duerme |
| 2026-11-11 | VS Code 1.142.0 · perfil aislado, `0.1.5` reempaquetada · `/tmp/sdd-manual` con `pytest` lento | extensión | ⚠️ parcial: **tope `timeoutMinutos`** — con el ajuste en 1 minuto y `test TASK-001` sobre un `pytest` que duerme 90 s, apareció `SDD: test excedió 1 minuto(s) y se cortó` con `Ver salida`; al pulsarlo el canal guardó `(tiempo agotado)` y no quedaron vivos ni el `pytest` ni la CLI. **Once casillas (11 de 29)**. Faltan `pin` de dos datos, vacíos y `Escape`, el «Cancelar» con `pytest` en marcha y las de comandos de barra |
| 2026-11-11 | VS Code 1.142.0 · perfil aislado, `0.1.5` reempaquetada · `/tmp/sdd-manual` | extensión | ⚠️ parcial: **`pin` de dos datos, vacío obligatorio y `Escape`** — los cuadros piden `SDD: PLAN-ID` y luego `SDD: TASK-ID`, y la corrida deja `pin PLAN-001 --task TASK-001 (código 0)` en el canal; `Escape` en el segundo cierra sin sumar líneas ni notificar; con el segundo vacío sale «SDD: falta el identificador pedido.» y no se ejecuta nada. **Tres casillas más (14 de 29)**. Falta el vacío de los comandos opcionales, el primer cuadro de un comando de un solo dato, el «Cancelar» con `pytest` en marcha, estado vacío, CLI rota y los comandos de barra |
| 2026-11-11 | VS Code 1.142.0 · perfil aislado, `0.1.5` reempaquetada · `/tmp/sdd-vacio` vacío y `/tmp/sdd-manual` con el intérprete roto | extensión | ⚠️ parcial: **estado vacío y CLI rota** — con una carpeta sin `.specify/` la vista muestra `⛔ sin inicializar o CLI no disponible` + `Inicializar proyecto`, la CLI responde `⛔ no hay proyecto toolkit aquí (falta .specify/); ejecute toolkit init` y la barra de estado no tiene elemento `SDD: …`; con `sddToolkit.python` en `/no/existe/python3` la vista cae en la misma fila y la barra se oculta. **Dos casillas más (16 de 29)**. **Hallazgo**: en una carpeta nueva la ventana abre en modo restringido y la extensión no se activa (sin vista SDD) hasta abrirla con `--disable-workspace-trust`. Faltan el vacío de los comandos opcionales, el «Cancelar» con `pytest` en marcha, las dos de `Inicializar proyecto` y los comandos de barra |
| 2026-11-11 | VS Code 1.142.0 · perfil aislado, `0.1.5` reempaquetada · `/tmp/sdd-manual` | extensión | ⚠️ parcial: **vacío en comandos opcionales** — `SDD: Generar / ver SPEC` con el cuadro vacío pide `SDD: ENR-ID (vacío = listar)` y deja `specify --list (código 0)` en el canal; `SDD: Mensaje final de fase` pide `SDD: TASK-ID o PLAN-ID (vacío = foto)` y deja `cierre (código 0)` con «Foto actual sin cerrar una fase concreta». **Una casilla más (17 de 29)**. Faltan el «Cancelar» con `pytest` en marcha, las dos de `Inicializar proyecto` y los comandos de barra |
| 2026-11-11 | VS Code 1.142.0 · proyecto `/tmp/sdd-manual` | comandos de barra | ⚠️ parcial: 14 archivos en `.github/prompts/` y `comandos --verificar` en verde; no se abrió el chat |

### Para marcar la pasada en editor

Plantilla con los datos del entorno ya levantado: lo único que falta es escribir
lo que se vea. Los valores salen de `scripts/preparar-manual.sh --solo-verificar`.

```
Entorno y versión:   VS Code 1.142.0 (`sdd-toolkit.sdd-visual-toolkit@0.1.5`)
Superficie:          extensión | comandos de barra
Proyecto:            /tmp/sdd-manual (fixture 0.1.0, 9/9 fases con artefacto)
Sistema:             Linux (Wayland), `code --version` 1.142.0
Fecha:               2026-11-11
Resultado:           ⚠️ parcial — aquí va lo observado
Fallos:              casilla, comando, mensaje obtenido, mensaje esperado
```

Al cerrar una superficie, tres cambios y ningún otro:

1. su fila del registro pasa de `⚠️ parcial` a `✅ verificado (…, 2026-11-11)`;
2. la celda correspondiente de «Estado» pierde `sin prueba manual` y la nombra;
3. las casillas de `ide/PRUEBA-MANUAL.md` se marcan una por una.

Mientras no haya una sola casilla marcada, esta plantilla no se usa: queda aquí
como la edición pendiente, no como un resultado.

### Pasada del 2026-11-11 sin editor (arnés headless)

Se preparó `/tmp/sdd-manual` con `scripts/preparar-manual.sh --instalar` —fixture
0.1.0, `.md` de plan, tareas e informe materializados, `.vsix` verificado e
instalado en VS Code 1.142.0— y se ejecutó `tests/js/arnes_extension.js`, que
carga el `extension.js` real con un stub de `vscode` y la CLI real:

- **41/41 comprobaciones en verde**: barra de estado con fase y siguiente,
  nueve nodos de `Fases y tareas` (fase, `1/18`, pruebas, siguiente, cuatro
  píldoras sin candado, nueve del árbol con cinco completadas), nueve del
  `Flujo SDD` con artefacto y tooltip, clic derecho en vista previa —incluidos
  `PLAN-001.md`, `TASKS-PLAN-001.md` e `INFORME-PLAN-001.md`—, paleta (`status`,
  `plan`, `pin` con dos datos, opcional vacío, `Escape`), `clarify` válido e
  inexistente, fallo de `build PLAN-999` sin abrir el canal, aviso de skills con
  su regeneración y los estados vacío y CLI rota.
- **Nada de esto se vio en un editor**: no hay ventana, ni menú contextual, ni
  notificación. Por eso las filas quedan en ⚠️ y ninguna casilla de
  `ide/PRUEBA-MANUAL.md` se marcó.

Sigue pendiente para pasar a ✅: el pintado real de la vista y la barra, los
tooltips y el menú contextual, la notificación de progreso con su «Cancelar"
(también que muera el `pytest` hijo), el tope de `sddToolkit.timeoutMinutos`,
las tareas `SDD: …` en *Terminal → Ejecutar tarea* y `/sdd*` en el chat. Esa
casilla de las tareas usa `/tmp/sdd-init` con `init`, porque `/tmp/sdd-manual`
se copia del fixture y no trae `.vscode/tasks.json`.

Regla (§47): donde falte capacidad, se degrada a CLI + `export`, nunca se
inventa estado.
