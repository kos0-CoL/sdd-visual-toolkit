# Compatibilidad por entorno (§30) — RF-40

La compatibilidad se comprueba individualmente; no se asume. Cada entorno
tiene dos superficies independientes: la **extensión** (`ide/vscode/`, RF-39)
y los **comandos de barra** (`toolkit comandos`, RF-36). Una puede estar verde
y la otra no.

## Estado

| Entorno | Extensión | Comandos de barra |
|---|---|---|
| VS Code | ✅ `node --check` + `tests/test_ide.py`; **sin prueba manual** | ✅ `.github/prompts/`; **sin probar en el IDE** |
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
| — | — | — | sin pruebas manuales registradas |

Regla (§47): donde falte capacidad, se degrada a CLI + `export`, nunca se
inventa estado.
