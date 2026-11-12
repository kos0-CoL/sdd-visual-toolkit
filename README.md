# SDD Visual Toolkit

![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)
![Tests](https://img.shields.io/badge/tests-450%20passed-green)
![Deps](https://img.shields.io/badge/dependencias-cero-lightgrey)
![License](https://img.shields.io/badge/license-MIT-blue)

Orquestador del **Desarrollo Guiado por Especificaciones (SDD)**: convierta
una idea en SPEC, plan, tareas, código verificado y evidencia trazable —
con la IA trabajando bajo reglas, gates humanos y estado recuperable.

SPEC de producto: [`docs/SPEC-v0.1.md`](docs/SPEC-v0.1.md).

> **Filosofía en una línea:** la herramienta ayuda a producir mejor software;
> no se limita a impedir que la IA haga cosas. Todo lo afirmado sale de
> artefactos reales; lo que no se sabe, se declara — nunca se inventa.

---

## ¿Para qué sirve?

- **Dirigir a la IA con especificaciones, no con prompts sueltos.** Cada fase
  (idea → SPEC → plan → tareas → código → pruebas) deja artefactos
  versionables bajo `.specify/` y exige validación humana en los gates.
- **Evitar el código fuera de alcance.** *Spec pinning* congela firmas e
  interfaces; el AST diff muestra qué cambió estructuralmente y la validación
  bloquea lo no autorizado.
- **No perder el hilo.** Journal, checkpoints, snapshots por tarea y
  recuperación de sesiones permiten retomar el trabajo días después.
- **Ver el estado de un vistazo.** Tablero, árbol de estados, píldoras de
  navegación ("¿qué hago ahora?") y mensajes de cierre uniformes.
- **Integrarse donde usted trabaje.** CLI completa sin IDE, extensión para
  VS Code (y compatibles), servidor MCP y hooks propios por evento.

## Casos de uso

### 1. De una idea a software verificado
Usted tiene una frase ("quiero un dashboard para mi kiosco") y termina con
SPEC aprobada, plan validado, tareas implementadas una a una, pruebas en
verde y trazabilidad SPEC → test → evidencia. Cada paso lo guía `siguiente`.

### 2. Retomar un proyecto a medias (o ajeno)
`investigar` mapea el repositorio real (lenguajes, dependencias, pruebas,
convenciones), `recover` dice dónde quedó el trabajo y `instrucciones`
genera el contexto que cualquier agente necesita para continuar.

### 3. Auditar lo que hizo la IA
`traza SPEC-001` muestra qué requerimiento cubre cada test y con qué
evidencia; `diff TASK-001` compara firmas antes/después; `historia`
reconstruye la vida de una tarea; `pin --check` delata cambios ajenos.

### 4. Equipos y varios IDEs
El estado central (`.specify/` + `export` JSON) lo comparten la CLI, la
extensión de VS Code, cualquier cliente MCP y sus propios hooks
(`.specify/hooks/`), sin duplicar información.

---

## Instalación paso a paso

Requisitos: **Python ≥ 3.11**, Git. Cero dependencias en tiempo de ejecución.

```bash
# 1. Clonar
git clone https://github.com/kos0-CoL/sdd-visual-toolkit.git
cd sdd-visual-toolkit

# 2. (Opcional pero recomendado) entorno virtual
python3 -m venv .venv && source .venv/bin/activate

# 3. Dependencias de desarrollo (pytest y pytest-xdist, en requirements-dev.txt)
python3 -m pip install -r requirements-dev.txt

# 4. Verificar que todo funciona (450 tests, ~40 s; ~20 s con -n 2)
python3 -m pytest tests/ -q

#    Ciclo rápido: deja fuera el arnés de la extensión (marcado "lento")
python3 -m pytest tests/ -q -m "not lento"

# 5. Probar la CLI
python3 cli/main.py --help
python3 cli/main.py --version
```

> **Sin instalación:** el proyecto se ejecuta desde su raíz con
> `python3 cli/main.py …`. Si prefiere el comando global `toolkit`,
> `pip install -e .` lo expone (ver `pyproject.toml`).

---

## Guía rápida: su primer proyecto en 10 pasos

```bash
cd /ruta/a/mi-proyecto   # o una carpeta vacía para greenfield

# 1. Inicializar (crea .specify/; no toca su código)
python3 /ruta/al/toolkit/cli/main.py init
# ...o desde cualquier carpeta, indicando el destino:
python3 /ruta/al/toolkit/cli/main.py --root /ruta/a/mi-proyecto init
# A partir de aquí puede abreviar con --root, o trabajar desde dentro.

# 2. Enriquecer la idea (todo lo inferido nace pendiente de validación)
toolkit enrich "Quiero un dashboard para gestionar un kiosco"

# 3. Aceptar el enriquecimiento
toolkit enrich --accept ENR-001

# 4. Generar la SPEC y aprobarla
toolkit specify ENR-001 --titulo "Kiosco"
toolkit specify --approve SPEC-001

# 5. Responder las aclaraciones (interactivo o por flags)
toolkit clarify SPEC-001
# ...o: toolkit clarify SPEC-001 --answer CLA-001 "Efectivo y tarjeta"

# 6. Plan técnico (exige Quality Gate 1 superado) y validarlo
toolkit plan SPEC-001
toolkit plan --gate PLAN-001

# 7. Desglosar en tareas y revisar consistencia
toolkit tasks PLAN-001
toolkit analyze PLAN-001

# 8. Implementar tarea por tarea (con snapshot y pin automáticos)
toolkit build PLAN-001            # pone la siguiente en curso
# ... usted o su agente implementa ...
toolkit test TASK-001             # arnés: unitarios→integración→…
toolkit build PLAN-001 --done TASK-001 --nota "ventas listas"

# 9. Ver el estado cuando quiera
toolkit status     # tablero + qué sigue
toolkit siguiente   # píldoras ejecutables
toolkit cierre PLAN-001   # mensaje final de 7 puntos

# 10. Trazabilidad
toolkit traza SPEC-001
```

`toolkit siguiente` es la brújula: siempre propone el próximo comando
ejecutable, marca lo bloqueado (🔒) y pide aprobación donde el SPEC la exige.

## Comandos

| Fase | Comandos |
|---|---|
| Proyecto | `init`, `status`, `tablero`, `arbol`, `siguiente`, `cierre` |
| Idea → SPEC | `enrich`, `specify`, `clarify`, `investigar` |
| Planificación | `plan`, `tasks`, `analyze` |
| Implementación | `build` (alias `implement`), `pin`, `context`, `flush` |
| Seguridad/continuidad | `journal`, `recover`, `checkpoint`, `rollback`, `hooks` |
| Verificación | `ast`, `validate`, `test`, `reporte`, `diff` |
| Trazabilidad | `traza`, `historia` (alias `history`), `restricciones`, `req`, `specs list` |
| Integración | `export`, `instrucciones`, `comandos` |

Detalles útiles:

- `toolkit test TASK-001 --fase unitarios --fase cobertura` — corridas
  dirigidas (fases: unitarios, integración, regresión, cobertura,
  aceptación, estructural).
- `toolkit context TASK-001 --modo pruebas` — contexto por modos
  (requerimientos, arquitectura, implementacion, pruebas, recuperacion).
- `toolkit rollback --list TASK-001` / `--restore TASK-001 --n 1`.
- `toolkit instrucciones` imprime el contexto del agente; con `--guardar`
  lo persiste en `.specify/INSTRUCCIONES.md` para cargarlo en su IDE.
- `toolkit hooks` — ganchos propios en `.specify/hooks/<evento>/`
  (`tarea_abierta`, `tarea_cerrada`, `sugerencia`); reciben
  `SDD_EVENTO/PLAN/TAREA/RESULTADO/SUGERENCIA/ROOT`.
- `toolkit --version` imprime la versión (sin `--root` ni subcomando).
- `toolkit export` — foto JSON del estado para IDEs, scripts y MCP.
- Todos los comandos aceptan `--root RUTA` para operar fuera del cwd.

## Ejemplo de sesión

Salida real de un proyecto de ejemplo, justo después de `tasks` (las
píldoras restantes se omiten):

```text
$ toolkit status
📊 Tablero «mi-kiosco» — SPEC-001 [approved].
Fase actual: 💾 Tareas.
Progreso: [····················] 0/18.
Tarea actual: ninguna en curso.
Última completada: ninguna todavía.
Pendientes: 18.
Pruebas: sin corridas.
Errores: ninguno registrado.
Próxima acción: build PLAN-001

🧭 Navegación — fase actual: 💾 Tareas.
Recomendada: [ build PLAN-001 ]
[ build PLAN-001 ] ★ Empezar implementación
[ analyze PLAN-001 ] Revisar consistencia
```

---

## Integraciones

- **VS Code (y Cursor, Windsurf, compatibles):** extensión empaquetada con
  cada release como `sdd-visual-toolkit-X.Y.Z.vsix` — paleta `SDD: …`, vista
  lateral de fases y tareas, barra de estado. Ver `ide/COMPATIBILIDAD.md`
  para la matriz por entorno (Antigravity: pendiente de verificación en su
  entorno real).

  Para instalarla, descargue el `.vsix` de la
  [última release](https://github.com/kos0-CoL/sdd-visual-toolkit/releases/latest)
  y en el editor use *Extensiones → … → Instalar desde VSIX…*; en VS Code
  también sirve el comando
  `code --install-extension sdd-visual-toolkit-X.Y.Z.vsix`. Requiere 1.80 o
  superior (`engines.vscode`). Las releases anteriores a v0.1.5 no adjuntan
  el archivo.

  La extensión ejecuta la CLI en vez de reimplementarla, así que hay que
  indicarle dónde está: `sddToolkit.cliPath` (por defecto `cli/main.py`
  relativo al proyecto) debe apuntar al `cli/main.py` de su copia del toolkit
  —ruta absoluta si no vive dentro del proyecto— y `sddToolkit.python` al
  intérprete (por defecto `python3`). Si esa ruta relativa no existe —carpeta
  donde `init` todavía no ha corrido— y el intérprete tiene el paquete
  instalado (`pip install -e .`), la extensión usa `python -m cli.main`; si
  tampoco, avisa de qué ajustar en vez de dejar el error de python.
  `sddToolkit.timeoutMinutos` (5 por defecto) fija cuánto se espera a un
  comando antes de cortarlo con sus procesos hijos. Sin `.specify/` la vista
  lo declara y ofrece `SDD: Inicializar proyecto`.

  `toolkit init` deja la carpeta lista al abrirla: escribe
  `.vscode/settings.json` con `sddToolkit.python` y `sddToolkit.cliPath`
  (ruta absoluta a este `cli/main.py`) y `.vscode/tasks.json` con las tareas
  `SDD: …`, recogidas por *Ejecutar tarea* en VS Code y, si las lee, en
  Antigravity. Nunca sobrescribe archivos que ya existan.

  En una terminal, `init` pregunta por el cliente del agente y deja sus
  comandos generados en el acto, dejando escrita la elección en su propia
  línea (`· cliente: copilot`); `--cliente copilot` (repetible) lo hace sin
  preguntar y
  `--sin-comandos` lo omite. Sin terminal —extensión, hook o script— no
  pregunta e imprime la orden para hacerlo después.

  La vista **Flujo SDD** es la capa visual del método: una fila por fase con
  su estado, el artefacto que deja (`specs/SPEC-001.md`,
  `.specify/planes/PLAN-001.md`, `.specify/tareas/TASKS-PLAN-001.md`,
  `.specify/informes/INFORME-PLAN-001.md`) y la skill que la ejecuta
  (`/sdd-plan`, `/sdd-test`). Si las skills instaladas apuntan a una ruta del
  toolkit que ya no existe, `Fases y tareas` abre con un aviso: cuántos
  archivos y a qué ruta apuntan, y una fila `↻ Regenerar los comandos` que
  corre `comandos --regenerar` (solo los clientes ya instalados) y refresca
  la vista. Con clic
  lanza el comando de la fase cuando los datos alcanzan; si falta el ID, la
  fila se muestra sin comando en vez de fallar.
- **MCP:** `python3 mcp/server.py` expone por stdio las herramientas de
  lectura `exportar_estado`, `siguiente` y `tablero`, y las operativas
  `asignar_tarea`, `registrar_resultado` y `marcar_completada`.
- **Hooks:** scripts ejecutables en `.specify/hooks/<evento>/` para
  `tarea_abierta`, `tarea_cerrada` y `sugerencia`
  (env `SDD_EVENTO/PLAN/TAREA/RESULTADO/SUGERENCIA/ROOT`).

### Comandos de barra para agentes

El agente solo ve lo que está en su workspace, así que el toolkit escribe los
comandos en la carpeta de cada cliente:

```bash
toolkit comandos                     # los cinco clientes
toolkit comandos --cliente cursor    # repetible; solo los que use
toolkit comandos --verificar         # ¿siguen existiendo las rutas grabadas?
toolkit comandos --regenerar         # reescribirlos con la ruta actual
```

`--verificar` no escribe nada: recorre los archivos ya generados, extrae la
ruta absoluta que llevan dentro y falla si esa ruta ya no existe —porque el
toolkit se movió o se borró— diciendo a cuál apuntan y cómo regenerarlos.
`toolkit status` hace la misma comprobación al terminar y, si encuentra rutas
muertas, lo avisa en una línea con el comando para regenerar.

| Cliente | Destino | Se invoca con |
|---|---|---|
| Claude Code | `.claude/skills/<nombre>/SKILL.md` | `/sdd-status` |
| Cursor | `.cursor/commands/<nombre>.md` | `/sdd-status` |
| Copilot (VS Code) | `.github/prompts/<nombre>.prompt.md` (arnés `Local`) y `.github/skills/<nombre>/SKILL.md` (arnés `Copilot`) | `/sdd-status` |
| Windsurf | `.windsurf/workflows/<nombre>.md` | `/sdd-status` |
| Antigravity | `.agents/skills/<nombre>/SKILL.md` | `/sdd-status` |

Son catorce, uno por paso del flujo. Cada uno ejecuta un subcomando de la
CLI con `--root .`; el catálogo vive en `core/agent_commands.py` y es el que
usa `toolkit comandos` para escribirlos, así que la tabla y los archivos
generados no pueden separarse:

| Skill | Ejecuta | Para qué |
|---|---|---|
| `/sdd` | `siguiente` | ver el tablero y el próximo comando recomendado |
| `/sdd-status` | `status` | fase, progreso y bloqueos antes de elegir el paso |
| `/sdd-enrich` | `enrich "idea"` | convertir una idea en requerimientos |
| `/sdd-specify` | `specify ENR-ID` | escribir la SPEC de un requerimiento aceptado |
| `/sdd-clarify` | `clarify SPEC-ID` | responder las aclaraciones abiertas |
| `/sdd-plan` | `plan SPEC-ID` | plan técnico de una SPEC aprobada |
| `/sdd-plan-gate` | `plan --gate PLAN-ID` | aprobar el plan y superar el Quality Gate |
| `/sdd-tasks` | `tasks PLAN-ID` | desglosar el plan en tareas verificables |
| `/sdd-analyze` | `analyze PLAN-ID` | informe de consistencia antes de implementar |
| `/sdd-build` | `build PLAN-ID` | poner la siguiente tarea en curso |
| `/sdd-pin` | `pin PLAN-ID --task TASK-ID` | congelar interfaces y detectar desviaciones |
| `/sdd-test` | `test TASK-ID` | correr el arnés de pruebas de la tarea |
| `/sdd-traza` | `traza SPEC-ID` | trazabilidad SPEC → test → evidencia |
| `/sdd-cierre` | `cierre TASK-ID o PLAN-ID` | mensaje de cierre de la fase |

Cada archivo ejecuta la CLI con su ruta absoluta y `--root .`, y le pide al
agente dos cosas: mostrar la salida tal cual y detenerse en los `⛔` y `🔒`.
El estado lo mueve la CLI, no el agente. Como la ruta se escribe al generar,
hay que volver a correrlo si el toolkit cambia de sitio.

Los formatos son los que documenta cada cliente, pero los archivos no se
probaron todavía dentro de Cursor, Copilot, Windsurf ni Antigravity: la
matriz de `ide/COMPATIBILIDAD.md` sigue siendo la que manda. Una salvedad
concreta: Cursor no pasa argumentos al comando, así que el archivo le pide al
agente que los reciba en el chat y los añada al final.

## Testing adaptativo

El arnés respeta el repo: `package.json`+scripts.test → `npm test`,
`go.mod` → `go test ./...`, `Cargo.toml` → `cargo test`; en Python usa
pytest si el repo lo usa, si no unittest. Las capas estáticas (.py)
declaran su vacío en repos de otros lenguajes en vez de inventar.

## Estructura del repositorio

```text
cli/        CLI completa (commands/ con despachar() por comando)
core/       Lógica pura y renders (sin I/O salvo su módulo)
state/      Persistencia atómica bajo .specify/
tests/      Suite pytest (450 tests, uno o más por RF)
ide/vscode/ Extensión VS Code (RF-39) + matriz de compatibilidad
mcp/        Servidor MCP stdio (RF-40)
docs/       SPEC-v0.1.md (requerimientos §44 y marco del producto)
```

## Estado del proyecto

- ✅ §44 completo (30/30) y las RF definidas en el código (RF-01 a RF-43;
  no existe RF-20) verificadas con tests.
- ⏳ Pendiente en entorno real: prueba manual en Antigravity y VS Code.
- La fuente de verdad es `docs/SPEC-v0.1.md`; cada RF cita su sección.

## Contribuir

- Guía: [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Código de conducta: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- Cambios por versión: [`CHANGELOG.md`](CHANGELOG.md).
- Proceso de release: [`docs/RELEASES.md`](docs/RELEASES.md).
- Rama protegida: [`docs/BRANCH_PROTECTION.md`](docs/BRANCH_PROTECTION.md).
- Integración continua: `.github/workflows/ci.yml` (Python 3.11–3.14).
- Licencia: MIT (ver [`LICENSE`](LICENSE)).
