# SDD Visual Toolkit v0.2.0

Primera versión con capacidad nueva desde hace varias: dos clientes de chat más
y el comando corto `sdd` para instalar una vez y escribir `sdd init` dentro de
cualquier proyecto. Compatible con los proyectos creados con 0.1.x: no cambian
el formato de `.specify/` ni el protocolo MCP.

Cada release adjunta `sdd-visual-toolkit-0.2.0.vsix`, empaquetado con `vsce`
desde el mismo commit que el tag:

```bash
code --install-extension sdd-visual-toolkit-0.2.0.vsix
```

## Añadido

- **`sdd`, el mismo programa que `toolkit`.** Instalarlo desde el repositorio
  deja los dos nombres, y el flujo queda como el de spec-kit: instalar una vez
  por máquina, entrar a la carpeta del proyecto y escribir
  `sdd init --cliente <el tuyo>`.
- **Clientes `Cline` y `Kilo Code`.** Cline escribe
  `.clinerules/workflows/<nombre>.md` (se invoca `/sdd-status.md`) y Kilo
  `.kilo/commands/<nombre>.md` (`/sdd-status`). Sin frontmatter: ninguno de los
  dos documentos lo pide.
- **En VS Code, `copilot` escribe skills.** `.github/skills/<nombre>/SKILL.md`
  lo listan los dos arneses del chat, `Copilot` y `Local`, en 1.142; el prompt
  file anterior solo lo veía uno y duplicaba cada comando en el menú `/`.
- **`init` deja un `.gitignore`** cuando el proyecto no tiene uno, con las dos
  rutas que guardan datos de la máquina (`.vscode/settings.json` y
  `.specify/cache/`). Si ya existe **añade solo las reglas que le faltan**
  —una carpeta como `.vscode/` ya cuenta como cubierta— sin duplicar ni tocar
  el resto, y dice cuáles agregó. Los comentarios van en su propia línea: en
  un `.gitignore` un `#` al final forma parte del patrón.
- **La extensión ejecuta el `sdd` instalado.** En un proyecto sin
  `cli/main.py` busca `sdd` y `toolkit` en el `PATH` antes de caer a
  `python -m cli.main`, así que `SDD: Inicializar proyecto` funciona en una
  carpeta vacía sin configurar `sddToolkit.cliPath` ni el intérprete. Si no
  encuentra el comando, el aviso lo nombra y dice cómo instalarlo, en vez de
  `spawn python3 ENOENT`.
- **`init` no acepta el repositorio del toolkit como proyecto.** Se niega si la
  carpeta es el propio repositorio y avisa si encuentra una copia clonada
  dentro del proyecto.

## Cambiado

- `copilot` ya no escribe `.github/prompts/<nombre>.prompt.md`; con las dos
  formas el menú `/` listaba cada comando dos veces. `comandos --regenerar`
  retira los que dejaron versiones anteriores —solo los que llevan la cabecera
  del toolkit— y regenera la skill aunque el proyecto no tuviera ninguna.
- **El README instala como spec-kit, con un solo camino.** `uv tool install`
  una vez por máquina y `sdd init` por proyecto; el camino de «clonar y
  ejecutar la ruta» desapareció porque invitaba a clonar el repositorio dentro
  del proyecto y a correr `init` sobre el toolkit.

## Corregido

- **Las skills de `sdd` y `sdd-status` no piden texto.** `siguiente` y `status`
  no aceptan argumentos y la CLI respondía `unrecognized arguments`; la regla
  ahora dice lo contrario, y en Claude esas dos skills no llevan `$ARGUMENTS`.
- **`build --done TASK-001` deduce el PLAN-ID.** Antes, sin él, respondía
  `⛔ plan inexistente: None`; ahora, si la tarea no existe, el mensaje la nombra
  y muestra la orden con el plan explícito.
- **Las skills piden el dato antes de ejecutar.** El primer punto de las reglas
  nombra el dato del comando (`**Antes de ejecutar**: este comando necesita la
  SPEC-ID…`) y aclara que el ⛔ de la CLI no sustituye a la pregunta.
- **`clarify --skip` sin `--answer`** reventaba con `TypeError`: `args.answer`
  llega en `None` cuando solo se omite. Ahora omite, registra en el historial y
  el fallo del Gate 1 baja.

## Verificación

- `python3 -m pytest tests/ -q` → 478 passed, 81 subtests passed.
- CI en verde en Python 3.11, 3.12, 3.13 y 3.14, más la instalación editable.
- `python3 scripts/verificar_release.py --previo 0.2.0` en verde antes del tag.
- `uv tool install` desde el repositorio instaló `sdd-toolkit==0.2.0` y dejó
  `sdd` y `toolkit`; en un proyecto vacío
  `sdd init --cliente copilot` creó `.specify/`, `specs/`, catorce skills y el
  `.gitignore`.
- La extensión `0.2.0` instalada desde el `.vsix` resuelve el `sdd` del `PATH`:
  `sdd --version` → `toolkit 0.2.0`.
- `git check-ignore -v` confirmó las dos reglas del `.gitignore` generado.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/docs/RELEASES.md)
- Compatibilidad por entorno: [`ide/COMPATIBILIDAD.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/ide/COMPATIBILIDAD.md)
- Checklist de prueba manual: [`ide/PRUEBA-MANUAL.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/ide/PRUEBA-MANUAL.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/CONTRIBUTING.md)
