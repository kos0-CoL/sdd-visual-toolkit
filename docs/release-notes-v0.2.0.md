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
  `.specify/cache/`). Si ya existe no lo toca: imprime esas reglas para
  copiarlas a mano.

## Cambiado

- `copilot` ya no escribe `.github/prompts/<nombre>.prompt.md`; con las dos
  formas el menú `/` listaba cada comando dos veces. `comandos --regenerar`
  retira los que dejaron versiones anteriores —solo los que llevan la cabecera
  del toolkit— y regenera la skill aunque el proyecto no tuviera ninguna.
- La instalación del README empieza por «instalar el comando», no por
  `python3 …/cli/main.py`: `sdd init` fallaba con «Orden no encontrada» si nadie
  había instalado el paquete antes.

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

- `python3 -m pytest tests/ -q` → 472 passed, 81 subtests passed.
- CI en verde en Python 3.11, 3.12, 3.13 y 3.14, más la instalación editable.
- `python3 scripts/verificar_release.py --previo 0.2.0` en verde antes del tag.
- `uv tool install` desde el repositorio dejó `sdd` y `toolkit`, y en un
  proyecto vacío `sdd init --cliente copilot` creó `.specify/`, `specs/`,
  catorce skills y el `.gitignore`.
- `git check-ignore -v` confirmó las dos reglas del `.gitignore` generado.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/docs/RELEASES.md)
- Compatibilidad por entorno: [`ide/COMPATIBILIDAD.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/ide/COMPATIBILIDAD.md)
- Checklist de prueba manual: [`ide/PRUEBA-MANUAL.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/ide/PRUEBA-MANUAL.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.0/CONTRIBUTING.md)
