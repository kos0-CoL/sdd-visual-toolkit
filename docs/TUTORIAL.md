# Tutorial: del cero al panel funcionando

Quince minutos, dos instalaciones y un proyecto de ejemplo: un kiosco. Al final
tenés el panel de VS Code leyendo el estado real y el primer prompt del flujo.

---

## Paso 1. Instalá el comando (una vez por máquina)

Es lo que te da `sdd` en cualquier carpeta. Necesitás **Python 3.11 o superior**
y **Git**. Si no tenés `uv`, se instala en un comando.

Linux o macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # solo si no tenés uv
uv tool install git+https://github.com/kos0-CoL/sdd-visual-toolkit
```

Windows (PowerShell): mismo comando de `uv`, con el instalador de Windows
(`irm https://astral.sh/uv/install.ps1 | iex`). El `.vsix` no está probado en
Windows; la CLI sí funciona.

Comprobá que quedó:

```console
$ sdd --version
toolkit 0.2.1
```

Si dice `Orden «sdd» no encontrada`, `~/.local/bin` no está en tu `PATH`:
agregalo y abrí una terminal nueva.

---

## Paso 2. Instalá la extensión (una vez por usuario)

Bajá `sdd-visual-toolkit-0.2.1.vsix` de la
[página de la última release](https://github.com/kos0-CoL/sdd-visual-toolkit/releases/latest)
y pegá:

```bash
code --install-extension ~/Descargas/sdd-visual-toolkit-0.2.1.vsix
```

En VS Code también sirve *Extensiones → ⋯ → Instalar desde VSIX…*. Después,
`Ctrl+Shift+P → Developer: Reload Window`.

La extensión es **global**: se instala una vez y aparece en cualquier ventana.
Lo que no es global es lo que muestra: lee el estado de la carpeta abierta.

---

## Paso 3. Creá el proyecto e inicializalo

Abrí una terminal y ubicate en la carpeta de tu proyecto (vacía o con código):

```bash
mkdir ~/kiosco
cd ~/kiosco
sdd init --cliente copilot
```

`--cliente` es tu agente de chat: `copilot`, `claude`, `cline`, `kilo`, `cursor`,
`windsurf` o `antigravity`. Esto deja el proyecto listo:

```console
🟢 PROYECTO INICIALIZADO: /home/tu-usuario/kiosco
Estado:
✓ .specify/ (memoria con estado e historial, checkpoints)
✓ .specify/planes/ .specify/tareas/ .specify/informes/
✓ specs/ (SPEC-001.md y su .json)
✓ .vscode/settings.json, .vscode/tasks.json (ruta del toolkit y tareas SDD)
✓ .gitignore (ajustes y caché de esta máquina)
🧩 copilot: 14 comando(s) en .github/skills/{nombre}/SKILL.md
✓ Comandos de barra instalados en /home/tu-usuario/kiosco
```

Que exista `.github/skills/` es lo que después te da `/sdd-enrich` en el chat.

---

## Paso 4. Abrí VS Code y mirá el panel

```bash
code .
```

En la barra de actividad de la izquierda aparece el icono **SDD**. Adentro:

- **Fases y tareas**: el árbol de trabajo — fases, plan y sus tareas.
- **Flujo SDD**: una fila por fase, con su estado y el artefacto que deja.

Recién inicializado, todo está pendiente: es correcto. El panel no inventa nada,
solo muestra lo que hay en `.specify/` y `specs/`. A medida que avanza el flujo,
las filas cambian de estado solas (se refresca al ejecutar comandos y cada
pocos segundos).

---

## Cómo se trabaja: dos caminos para lo mismo

Hay una sola fuente de verdad (`.specify/` y `specs/`) y dos formas de moverla.
Elegí una; se pueden mezclar.

**A. Desde el chat (lo normal para escribir código).** Escribís el comando en
el chat del agente, el agente ejecuta la CLI y te muestra la salida ahí mismo:

```text
/sdd-enrich "Quiero un sistema para el kiosco: cargar productos con precio y stock…"
```

Así trabajás todo el flujo: `/sdd-specify`, `/sdd-clarify`, `/sdd-plan`,
`/sdd-tasks`, `/sdd-build`. Cuando toca escribir código, `/sdd-build` le dice al
agente qué archivos puede tocar, y el agente los escribe. Vos seguís en el chat.

**B. Desde el panel de VS Code.** Hacés clic en la fase o en una píldora del
panel y la CLI corre igual; la salida aparece en el canal **SDD Toolkit**
(abajo, junto a *Terminal* → *Salida*). El panel sirve para mirar el estado y
disparar un paso suelto, no para conversar.

Si una píldora dice `enrich «idea»`, el panel te pide la idea en un cuadro de
texto antes de ejecutar: nunca manda «idea» literal.

**Recomendado:** chat para el flujo completo y el código; panel para ver dónde
estás y para los comandos que no necesitan datos (`/sdd`, `/sdd-status`).

---

## Paso 5. El primer prompt, en el chat

Abrí el chat de tu agente (`Copilot`, `Claude`, el que hayas elegido) y escribí
la idea en una frase, sin formato especial:

```text
/sdd-enrich Quiero un sistema para el kiosco: cargar productos con precio y
stock, registrar ventas del día y ver el total vendido. Tiene que andar sin
internet.
```

El agente ejecuta `sdd enrich "…"` y te devuelve el enriquecimiento. Esto es
salida real, recortada:

```console
🌀 ENRIQUECIMIENTO ENR-001 (pendiente de validación) — dominio: comercio

🎯 Objetivo:
  [OBJ-1] (explicito) Un sistema para el kiosco: cargar productos con precio y
  stock, registrar ventas del día y ver el total vendido

📦 Entidades potenciales (inferido):
  [ENT-1] (inferido) Productos
  [ENT-2] (inferido) Inventario
  [ENT-3] (inferido) Ventas
  [ENT-4] (inferido) Movimientos de stock
  [ENT-5] (inferido) Caja

⚙️ Funcionalidades:
  [FUN-1] (explicito) Tiene que andar sin internet
  [FUN-2] (inferido) Visualización de productos
  ...

💡 Mejoras / sugerencias:
  [MEJ-1] (sugerido) Alertas de stock mínimo
  ...
```

Fijate en las etiquetas: **explicito** es lo que dijiste, **inferido** lo dedujo
la herramienta y **sugerido** es una idea. Nada se aprobó solo.

**Tu primera decisión:** aceptar o corregir. En el chat:

```text
/sdd-enrich --accept ENR-001
```

```console
🟢 ENRIQUECIMIENTO VALIDADO: ENR-001
Requerimientos creados: 23
  REQ-001 [explicito/aceptado] [ENR-001/FUN-1] Tiene que andar sin internet
  REQ-002 [inferido/pendiente] [ENR-001/ENT-1] Productos
  ...
```

---

## Paso 6. El flujo, fase por fase (salida real)

A partir de acá el chat hace el trabajo y vos aprobás. Cada comando es una fase;
su salida real fue esta.

**SPEC**

```text
/sdd-specify ENR-001 --titulo "Kiosco"
```
```console
📝 SPEC SPEC-001 v1.0.0 [draft] — Kiosco
  funcionales: 16 | entidades: 5
  criterios: 16 | casos: 16
  fuera de alcance: 4 | supuestos: 3
  ⚠️ §6.4: demasiados flujos independientes; se recomienda dividir en varias SPEC
```

**Aclaraciones** — el primer control de calidad. Si quedan preguntas, bloquea:

```console
🔴 QUALITY GATE 1: BLOQUEADO — 1/24 aclaradas, 23 pendiente(s)
   ○ CLA-002 [supuesto] ¿Quiénes usarán el sistema? (roles y permisos)
   ○ CLA-003 [supuesto] ¿Dónde se guardan los datos hoy?
   ...
```

Se responden con `/sdd-clarify` y, cuando están todas:

```console
🟢 QUALITY GATE 1: SUPERADO — 24/24 aclaradas. SPEC-001 lista para /plan
```

**Plan**

```text
/sdd-plan SPEC-001
```
```console
📐 PLAN PLAN-001 v1.0.0 [draft] → SPEC-001
  pasos: 20 | riesgos: 1 | validación: 16 criterios
  greenfield: True | archivos analizados: 1
```

```text
/sdd-plan --gate PLAN-001
```
```console
🟢 QUALITY GATE 2: SUPERADO — PLAN-001 responde a SPEC-001 y al repo real.
```

**Tareas**

```text
/sdd-tasks PLAN-001
```
```console
🧩 20 tareas derivadas de PLAN-001 (TASK-001…TASK-020), cadena secuencial explícita.
```

```text
/sdd-tasks --gate PLAN-001
```
```console
🟢 QUALITY GATE 3: SUPERADO — 20 tareas verificables, PLAN-001 listo para implementar.
```

**Análisis de consistencia**

```text
/sdd-analyze PLAN-001
```
```console
🔍 Informe PLAN-001: 9 hallazgo(s), 0 crítica(s).
```

**Implementación** — acá trabaja el agente, tarea por tarea:

```text
/sdd-build PLAN-001
```
```console
🏗️ PLAN-001: 0/20 completadas.
📌 PIN TASK-001 — SPEC SPEC-001 [draft]
Tarea: Modelar entidades de §6. Estructuras de datos antes que comportamiento.
Archivos autorizados: src/productos.py, tests/test_productos.py
Exclusiones: Gestión de franquicias; Múltiples sucursales; ...

▶ TASK-001 en curso. Implemente, luego `build PLAN-001 --done TASK-001`.
```

El agente escribe esos archivos, corre las pruebas y cierra la tarea con
`--done TASK-001`; después el flujo le ofrece la siguiente. En cualquier momento:

```text
/sdd-status
```
```console
📊 Tablero «kiosco» — SPEC-001 [draft].
Fase actual: 💾 Tareas.
Progreso: [····················] 0/20.
Próxima acción: build PLAN-001
```

---

## Paso 7. Qué deberías ver en el panel

Con ese estado, **Flujo SDD** muestra una fila por fase (así las lee la vista):

| Fase | Estado | Comando del chat | Artefacto |
|---|---|---|---|
| Enriquecimiento | completado | `/sdd-enrich` | `.specify/requerimientos.json` |
| Especificación | requiere intervención | `/sdd-specify` | `specs/SPEC-001.md` |
| Aclaraciones | completado | `/sdd-clarify` | `.specify/clarifications.json` |
| Arquitectura | completado | `/sdd-plan` | `.specify/planes/PLAN-001.md` |
| Tareas | en progreso | `/sdd-tasks` | `.specify/tareas/TASKS-PLAN-001.md` |
| Análisis | pendiente | `/sdd-analyze` | `.specify/informes/INFORME-PLAN-001.md` |
| Implementación | en progreso | `/sdd-build` | `.specify/memory/current_task.json` |
| Pruebas | pendiente | `/sdd-test` | `.specify/memory/execution_history.jsonl` |
| Recuperación | pendiente | — | `.specify/checkpoints` |

«Requiere intervención» en Especificación es normal: la SPEC está en `draft`
porque aprobarla es una decisión tuya, no un paso automático.

En **Fases y tareas** ves lo mismo en detalle: las 20 tareas con su estado y el
archivo que va a tocar cada una. El clic derecho sobre una fase con artefacto lo
abre.

---

## Errores que vas a poder tener (y qué significan)

| Mensaje | Qué pasa | Solución |
|---|---|---|
| `SDD: abra una carpeta primero` | la ventana de VS Code está sin proyecto | *Archivo → Abrir carpeta…*, elegí tu proyecto |
| `Orden «sdd» no encontrada` | falta `~/.local/bin` en el `PATH` | agregalo y abrí una terminal nueva |
| `⛔ YA HAY UN PROYECTO TOOLKIT POR ENCIMA` | corriste `init` dentro de otro proyecto | trabajá desde la raíz del proyecto que ya existe |
| `⛔ ESTA CARPETA ES EL TOOLKIT` | abriste el repo de la herramienta, no tu proyecto | abrí tu proyecto y corré ahí `sdd init` |
| `🔴 QUALITY GATE 1: BLOQUEADO` | hay aclaraciones sin responder | `/sdd-clarify` y respondé las que quedan |
| `⛔ PLAN-001 no está validado` | falta el gate del plan | `/sdd-plan --gate PLAN-001` |

---

## Resumen de los dos comandos que importan

```bash
# una vez por máquina
uv tool install git+https://github.com/kos0-CoL/sdd-visual-toolkit

# una vez por proyecto, desde la raíz
sdd init --cliente copilot
```

El resto pasa en el chat: `/sdd-enrich` con tu idea y el flujo te va pidiendo lo
que necesita.
