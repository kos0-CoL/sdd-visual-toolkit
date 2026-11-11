# SDD Visual Toolkit v0.1.5

Versión con capacidad nueva y la primera que adjunta la extensión del IDE.

Hasta 0.1.4 la extensión se instalaba depurando desde el código; desde esta
versión cada release publica `sdd-visual-toolkit-0.1.5.vsix`, empaquetado con
`vsce` desde el mismo commit que el tag. Es compatible con proyectos creados
con 0.1.0 a 0.1.4: no cambian el formato de `.specify/`, los comandos que ya
existían ni el protocolo MCP.

## Añadido

- **`toolkit comandos`**: escribe los comandos de barra del flujo en la
  carpeta que cada agente lee, con la ruta absoluta de la CLI dentro, así que
  funcionan sin configurar nada:

  ```bash
  toolkit comandos                       # los cinco clientes
  toolkit comandos --cliente cursor      # uno solo
  ```

  Son catorce: `/sdd`, `/sdd-status`, `/sdd-enrich`, `/sdd-specify`,
  `/sdd-clarify`, `/sdd-plan`, `/sdd-plan-gate`, `/sdd-tasks`,
  `/sdd-analyze`, `/sdd-build`, `/sdd-pin`, `/sdd-test`, `/sdd-traza` y
  `/sdd-cierre`, en el orden del flujo. Cada archivo repite las mismas reglas:
  la salida de la CLI es la fuente de la verdad, un `⛔` o un `🔒` detienen al
  agente y el identificador que falte se pide, no se inventa.

  Lo que cambia según el cliente es el formato:

  | Cliente | Dónde | Qué recibe |
  |---|---|---|
  | Claude Code | `.claude/skills/` | `$ARGUMENTS` sustituido |
  | Cursor | `.cursor/commands/` | Markdown sin frontmatter |
  | Copilot | `.github/prompts/` | `agent: agent` y pista de argumento |
  | Windsurf | `.windsurf/workflows/` | workflow invocable con `/` |
  | Antigravity | `.agents/skills/` | skill que el agente elige por nombre y descripción |

- **La extensión viaja con cada release**: el `.vsix` se empaqueta desde el
  commit etiquetado y se adjunta a la release, y el README documenta ese
  camino de instalación en lugar de la depuración desde el código:

  ```bash
  code --install-extension sdd-visual-toolkit-0.1.5.vsix
  ```

  Requiere VS Code 1.80 o posterior y `sddToolkit.cliPath` apuntando a
  `cli/main.py`.

- **El proceso de release comprueba más antes de etiquetar**: la versión de
  `ide/vscode/package.json` tiene que coincidir con la del release —si no, el
  `.vsix` saldría con otro número— y el commit de `HEAD` tiene que tener todos
  sus checks terminados y en verde. Un tag sobre un `main` con el CI roto o a
  medias ya no llega a crearse.

- **Documentación de compatibilidad honesta**: `ide/COMPATIBILIDAD.md` separa
  extensión y comandos de barra por cliente y deja dicho que ninguno está
  probado dentro del IDE, y `ide/PRUEBA-MANUAL.md` da las casillas concretas
  para probarlos en VS Code y Antigravity, con el resultado esperado sobre el
  fixture y el formato de registro.

## Corregido

- **La paleta de `pin` pedía solo el plan**: `pin` es por tarea, así que desde
  VS Code respondía «indique PLAN-ID y --task, o use --check/--suggest». Ahora
  pregunta los dos identificadores y ejecuta `pin PLAN-001 --task TASK-001`.
- **Once comandos morían con un traceback** cuando el ID no existía: `ast`,
  `diff`, `historia`, `reporte`, `test`, `validate`, `flush`, `pin`,
  `recover`, `traza` y `clarify` solo capturaban el error de su módulo, no el
  de cargar la SPEC, el plan o la tarea. Ahora avisan con un `⛔`.
- **`pin --task` reventaba con `NameError`** por una llamada a `_guardar_pin`
  que nadie importaba, y al reutilizar la línea base decía «registrada»
  aunque no hubiera registrado nada.
- **`build` mandaba a `analyze` con un plan que no existe**: respondía «sin
  informe para PLAN-999; ejecute `analyze PLAN-999` primero» en vez de «plan
  inexistente». El Quality Gate 4 sigue igual para los planes que sí existen.
- **`toolkit comandos` escribía frontmatter inválido** cuando la descripción
  llevaba «: » — doce de los cincuenta y seis archivos generados no eran YAML
  válido, y el cliente podía no cargar el comando. Los valores van entre
  comillas simples.
- **La pista de `/sdd-enrich` no se podía ejecutar**: `enrich` toma un solo
  argumento y ahora la idea se pide entre comillas.
- **`specify --revise` dejaba una copia huérfana** en `.specify/spec_history/`
  cuando el ENR de origen no existía: armaba la revisión después de copiar.
- **El verificador del release solo miraba los enlaces `blob`**: un relativo o
  un `/tree/` de las notas pasaban sin protestar. Ahora todo enlace a un
  repositorio tiene que ser `blob` del tag, y las notas de 0.1.0 apuntan a
  `blob/v0.1.0` en lugar de enlazar en relativo, que daba 404.

## Verificación

- `python3 -m pytest tests/ -q` → 372 passed, 45 subtests passed.
- CI en verde en Python 3.11, 3.12, 3.13 y 3.14, más la instalación editable.
- Los 70 archivos de comandos generados en un proyecto de ejemplo: 56 de 56
  frontmatter parsean con `yaml.safe_load`, y los catorce comandos se ejecutan
  con lo que pide su pista sin error de parseo ni traceback.
- `python3 scripts/verificar_release.py --previo 0.1.5` en verde antes de
  crear el tag.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.5/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.5/docs/RELEASES.md)
- Compatibilidad por entorno: [`ide/COMPATIBILIDAD.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.5/ide/COMPATIBILIDAD.md)
- Checklist de prueba manual: [`ide/PRUEBA-MANUAL.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.5/ide/PRUEBA-MANUAL.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.5/CONTRIBUTING.md)
