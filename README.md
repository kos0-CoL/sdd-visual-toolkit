# SDD Visual Toolkit

![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)
![Tests](https://img.shields.io/badge/tests-469%20passed-green)
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

Requisitos: **Python ≥ 3.11** y nada más: cero dependencias en tiempo de
ejecución. Con el ZIP o el clon funciona igual; Git solo hace falta para
instalar el paquete desde el repositorio («Ponerlo global»).

### Si solo va a usarlo

El toolkit no se instala: se ejecuta desde la carpeta donde quedó el código.
No hay dependencias ni hace falta entorno virtual.

```bash
git clone https://github.com/kos0-CoL/sdd-visual-toolkit.git
cd sdd-visual-toolkit
python3 cli/main.py --version          # toolkit 0.1.6
```

- **Linux y macOS**: `python3`. En macOS ya viene de serie; en Linux suele
  estar instalado.
- **Windows**: use `py` o `python` en lugar de `python3` (PowerShell, CMD o
  Git Bash); el resto de comandos es igual. *No probado en Windows*: ver
  `ide/COMPATIBILIDAD.md`.
- **Sin Git**: *Code → Download ZIP* en GitHub y descomprimir; el resultado
  es el mismo.
- Opcional: `python3 -m pip install -e .` deja el comando `toolkit`
  disponible en cualquier carpeta (ver `pyproject.toml`).

Con eso la CLI ya funciona desde la terminal. Para usarla **dentro de su
proyecto** y tener los comandos `/sdd…` en el chat, siga «Instalar en tu
proyecto (2 pasos)».

### Ponerlo global: `sdd` en cualquier carpeta

Sin instalar, cada orden lleva la ruta al `cli/main.py`. Si prefiere el flujo
de spec-kit —entrar a la carpeta del proyecto y escribir `sdd init`— instale
el paquete una vez. Hace falta `pipx` (o `uv`) y **Git**, porque instala desde
el repositorio:

```bash
pipx install git+https://github.com/kos0-CoL/sdd-visual-toolkit.git
# con uv en lugar de pipx: uv tool install git+https://github.com/kos0-CoL/sdd-visual-toolkit.git
# sin pipx ni uv: python3 -m pip install . dentro del clon deja los mismos dos comandos
```

Deja dos comandos con el mismo programa: **`sdd`** y **`toolkit`**. Después,
por proyecto:

```bash
cd ~/kiosko
sdd init --cliente cline   # el tuyo: copilot, claude, kilo, cursor, windsurf, antigravity
sdd status
```

`init` escribe en `.vscode/settings.json` la ruta del `cli/main.py` de la copia
instalada y el intérprete que la tiene instalada, así que no hay nada más que
apuntar a mano. Verificado instalando desde el repositorio en un entorno
limpio: `sdd init` deja el proyecto listo y `sdd status` responde.

### Si va a desarrollarlo

```bash
# 1. Entorno virtual (opcional pero recomendado)
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Dependencias de desarrollo (pytest y pytest-xdist, en requirements-dev.txt)
python3 -m pip install -r requirements-dev.txt

# 3. Verificar que todo funciona (469 tests, ~40 s; ~20 s con -n 2)
python3 -m pytest tests/ -q
python3 -m pytest tests/ -q -m "not lento"   # sin el arnés de la extensión
```

---

## Instalar en tu proyecto (2 pasos)

Sirve para cualquier proyecto, nuevo o existente. No hace falta `pip install` ni
copiar el toolkit dentro del proyecto: se queda donde está y el proyecto guarda
su ruta.

**Paso 1 — el chat (obligatorio).** Desde la carpeta del proyecto:

```bash
cd ~/mi-proyecto
python3 /ruta/al/toolkit/cli/main.py init --cliente copilot
```

Deja el estado (`.specify/`, `specs/`), los ajustes del IDE
(`.vscode/settings.json` con la ruta del toolkit y las tareas `SDD: …`) y las
**14 skills** en `.github/skills/`. Eso es el menú `/sdd…` del chat: archivos en
el proyecto, nada instalado en el editor.

**Cómo elegir el agente.** `--cliente` decide qué archivos de comandos se
escriben. Sin él, `init` **no deja los comandos hechos**:

| Situación | Qué hace `init` |
|---|---|
| `init --cliente cline` | escribe los 14 comandos de ese agente y no pregunta nada |
| `init` en una terminal interactiva | pregunta una vez: un nombre, varios separados por comas, `todos`, o vacío para ninguno |
| `init` desde un script, un hook o la extensión | no pregunta y no escribe comandos: imprime la orden para lanzarla después |
| `init --sin-comandos` | ni pregunta ni escribe comandos; el estado y los ajustes del IDE sí |

Valores de `--cliente`: `copilot`, `claude`, `cline`, `kilo`, `cursor`,
`windsurf`, `antigravity`. Es repetible, para dos agentes a la vez:

```bash
sdd init --cliente cline --cliente kilo
```

Si ya inicializaste y cambias de agente, no repitas `init`:

```bash
sdd comandos --cliente cline
```

Y `sdd comandos` sin `--cliente` escribe los siete a la vez (7 × 14 archivos);
solo tiene sentido si estás probando varios agentes. Después, `sdd status` y el
resto de comandos son idénticos cambies o no de agente. Si no instalaste el
paquete global, donde dice `sdd` va `python3 /ruta/al/toolkit/cli/main.py`.

**Empezar en el chat.** Con la carpeta abierta y los comandos ya generados, el
primero es `/sdd-enrich` con la idea entre comillas:

```text
/sdd-enrich "quiero un dashboard para gestionar un kiosco"
```

`/sdd` no arranca nada: muestra el tablero y el paso recomendado, y por eso no
lleva texto detrás. Después del primer enriquecimiento sí es la brújula: dice
cuál toca (`/sdd-enrich --accept ENR-001`, `/sdd-specify ENR-001`…). La lista
completa, con lo que ejecuta cada uno, está en [Comandos](#comandos).

**Paso 2 — la extensión (opcional).** Añade la vista `Fases y tareas`, la barra
de estado y la paleta `SDD: …`. El `.vsix` no viene en el repositorio: descárguelo
de la [última release](https://github.com/kos0-CoL/sdd-visual-toolkit/releases/latest)
y instálelo desde la ruta donde quedó:

```bash
code --install-extension /ruta/a/sdd-visual-toolkit-0.1.6.vsix
```

y recargar la ventana; en el editor también sirve *Extensiones → … → Instalar
desde VSIX…*. El chat del paso 1 funciona sin este paso.

**Comprobar que quedó bien:** abre la carpeta en el editor y escribe `/` en el
chat del cliente que instalaste —el arnés `Copilot` en VS Code, el panel de
`Cline`, el de tu agente—: deben aparecer los comandos. `/sdd` responde con el
tablero y `/sdd-enrich "una idea"` arranca el flujo; en Cline se invocan con
extensión (`/sdd-enrich.md`). Con la extensión de VS Code, `Fases y tareas`
aparece en la barra lateral y `SDD: <fase>` en la barra de estado.

---

## Primera sesión: de la idea al primer build

Una sesión real, sin retoques: proyecto de ejemplo en `/tmp/sesion`, Python
3.14.4, 2026-11-12. Para no repetir la ruta, el bloque usa
`TK="python3 /ruta/al/sdd-visual-toolkit/cli/main.py"`. Donde dice «…» la
salida está recortada; lo demás es literal.

Los mismos pasos desde el chat son `/sdd-enrich`, `/sdd-specify`,
`/sdd-clarify`… Aquí van en terminal para que se vea la salida completa de
cada fase.

### 1. Idea → SPEC

```console
$ $TK init --cliente copilot
🟢 PROYECTO INICIALIZADO: /tmp/sesion
Estado:
✓ .specify/ (memoria con estado e historial, checkpoints)
✓ .specify/planes/ .specify/tareas/ .specify/informes/
✓ specs/ (SPEC-001.md y su .json)
✓ .vscode/settings.json, .vscode/tasks.json (ruta del toolkit y tareas SDD)
🧩 copilot: 14 comando(s) en .github/skills/{nombre}/SKILL.md
✓ Comandos de barra instalados en /tmp/sesion

$ $TK enrich "Quiero una agenda de turnos para un consultorio: necesito registrar \
  clientes, reservar turnos, cancelar turnos y consultar la agenda del día. \
  Debe funcionar sin internet."
🌀 ENRIQUECIMIENTO ENR-001 (pendiente de validación) — dominio: turnos

🎯 Objetivo:
  [OBJ-1] (explicito) Una agenda de turnos para un consultorio: necesito registrar
  clientes, reservar turnos, cancelar turnos y consultar la agenda del día

📦 Entidades potenciales (inferido):
  [ENT-1] (inferido) Clientes
  [ENT-2] (inferido) Turnos
  [ENT-3] (inferido) Agenda
  [ENT-4] (inferido) Profesionales

⚙️ Funcionalidades:
  [FUN-1] (explicito) Debe funcionar sin internet
  [FUN-2] (inferido) Reserva de turnos
  [FUN-3] (inferido) Cancelación de turnos
  [FUN-4] (inferido) Consulta de agenda
  [FUN-5] (inferido) Registro de clientes

❓ Falta información (desconocido):
  [FAL-1] (desconocido) Stack tecnológico sin definir (pendiente de aclaración)
  [FAL-2] (desconocido) ¿dónde se guardan los datos hoy? (archivo, planilla, base de datos)

Problemas pendientes: responda lo marcado como desconocido.

$ $TK enrich --accept ENR-001
🟢 ENRIQUECIMIENTO VALIDADO: ENR-001
Requerimientos creados: 3
  ...

$ $TK specify ENR-001 --titulo "Agenda de turnos"
📝 SPEC SPEC-001 v1.0.0 [draft] — Agenda de turnos
  funcionales: 12 | entidades: 4
  criterios: 12 | casos: 12
  fuera de alcance: 2 | supuestos: 2
```

Nada se aprobó solo: `enrich` marca lo inferido como pendiente y la SPEC nace
en `draft`. Aceptar el enriquecimiento es el primer acto humano.

### 2. Aclarar antes de planificar

`clarify` lista lo que falta. En esta sesión fueron 18 preguntas: 4 de
contexto, 12 de confirmación y 2 sobre datos de cada entidad.

```console
$ $TK clarify --list SPEC-001
○ CLA-001 [supuesto] Pendiente de aclarar: Stack tecnológico sin definir (pendiente de aclaración)
○ CLA-002 [supuesto] Pendiente de aclarar: ¿dónde se guardan los datos hoy? (archivo, planilla, base de datos)
○ CLA-003 [regla] ¿Hay alguna regla de negocio (precios, descuentos, permisos)?
○ CLA-009 [confirmar_req] ¿Se confirma este requerimiento? «[ENR-001/FUN-2] Reserva de turnos»
…
○ CLA-018 [entidad_datos] ¿Qué datos guarda «Profesionales»?

$ $TK clarify SPEC-001 --answer CLA-001 "Python 3.11, sin dependencias externas"
✓ CLA-001: supuesto resuelto y movido a aclarados
$ $TK clarify SPEC-001 --answer CLA-009 "sí"
✓ CLA-009: [ENR-001/FUN-2] confirmado como aceptado
$ $TK clarify SPEC-001 --skip CLA-013 --skip CLA-014
— CLA-013 omitida (registrada, no se repetirá)
— CLA-014 omitida (registrada, no se repetirá)
```

Omitir es explícito y queda en el historial: no es lo mismo que responder
«no lo sé». Lo que se descarta se marca con `Descartar` como respuesta.

```console
$ $TK clarify SPEC-001 --gate
🟢 QUALITY GATE 1: SUPERADO — 18/18 aclaradas. SPEC-001 lista para /plan
```

### 3. Plan y tareas (Gate 2)

```console
$ $TK plan SPEC-001
📐 PLAN PLAN-001 v1.0.0 [draft] → SPEC-001
  pasos: 14 | riesgos: 1 | validación: 12 criterios
  greenfield: True | archivos analizados: 0

$ $TK plan --gate PLAN-001
🟢 QUALITY GATE 2: SUPERADO — PLAN-001 responde a SPEC-001 y al repo real.
Sin funcionalidad inventada (§8.6).

$ $TK tasks PLAN-001
🧩 14 tareas derivadas de PLAN-001 (TASK-001…TASK-014), cadena secuencial explícita.

$ $TK analyze PLAN-001
🔍 Informe PLAN-001: 6 hallazgo(s), 0 crítica(s).
```

El plan no se puede generar con preguntas abiertas, y las tareas no se pueden
generar sin el Gate 2. Son dos bloqueos reales, no avisos.

### 4. El primer build

```console
$ $TK siguiente
🧭 Navegación — fase actual: 💾 Tareas.
Recomendada: [ build PLAN-001 ]

$ $TK build PLAN-001
🏗️ PLAN-001: 0/14 completadas.
📌 PIN TASK-001 — SPEC SPEC-001 [draft]
Requerimiento: (sección §6:Clientes, §6:Turnos, §6:Agenda, §6:Profesionales)
Tarea: Modelar entidades de §6. Estructuras de datos antes que comportamiento.
Criterio: Criterio de §6:Clientes: completar «Modelar entidades de §6» según su sección SPEC
Archivos autorizados: src/clientes.py, tests/test_clientes.py
Exclusiones: Facturación electrónica; Múltiples sedes
Supuestos abiertos: 0

▶ TASK-001 en curso. Implemente, luego `build PLAN-001 --done TASK-001`.
```

Ahí está el aporte concreto: **la tarea autoriza dos archivos y nada más**.
La implementación la escribe el agente o usted; el toolkit la mide. Este es el
contenido real con el que se cerró la tarea:

```python
# src/clientes.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Cliente:
    """Persona que reserva turnos. Datos mínimos: nombre y teléfono."""

    nombre: str
    telefono: str

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise ValueError("el cliente necesita un nombre")
        if not self.telefono.strip():
            raise ValueError("el cliente necesita un teléfono")
```

```console
$ $TK test TASK-001
🧪 Ciclo de testing TASK-001: ✅ TODO VERDE.
✅ unitarios: total=3 pasadas=3 fallidas=0 omitidas=0 (0.497s)
✅ regresión: total=3 pasadas=3 fallidas=0 omitidas=0 (0.4s)
✅ cobertura: total=12 pasadas=12 fallidas=0 omitidas=0 (0.0s)
   Cobertura TASK-001: 100% de 12 líneas (src/clientes.py 100%) ✅

$ $TK validate TASK-001
✔ Validación TASK-001: OBSERVADO (0 rechazo(s), 4 observación(es)).
  🟡 [pin-B] src/clientes.py: símbolo público nuevo «Cliente (clase)» en archivo
  creado por la tarea: justifique por qué es indispensable (§12.B)
  …
Revise y justifique con --nota (§17.4).
```

`validate` no bloquea por un símbolo nuevo, pero no lo deja pasar en silencio:
pide una nota. Con ella, la tarea se cierra:

```console
$ $TK build PLAN-001 --done TASK-001 --nota "Cliente es la entidad de §6:Clientes
  que la tarea pide modelar; dataclass evita escribir a mano igualdad y repr,
  y from __future__ import annotations es la cabecera estándar de los módulos."
✔ Validación TASK-001: VALIDADO (0 rechazo(s), 4 observación(es)).
✅ TASK-001 completada (intento 1).
```

El PLAN-ID se puede omitir: `build --done TASK-001` lo deduce de la tarea. Si
la tarea no existe, el mensaje lo dice —`⛔ tarea inexistente: TASK-999`— en
vez de `plan inexistente: None`.

### 5. Dónde quedó el trabajo

```console
$ $TK tablero
📊 Tablero «sesion» — SPEC-001 [draft].
Fase actual: 🧪 Pruebas.
Progreso: [█···················] 1/14.
Tarea actual: ninguna en curso.
Última completada: TASK-001.
Pendientes: 13.
Pruebas: ✅ P=6 F=0 cob=100% (TASK-001).
Errores: ninguno registrado.
Próxima acción: build PLAN-001
```

Eso es el ciclo completo: idea → 12 requerimientos → 18 preguntas cerradas →
plan de 14 pasos → 14 tareas → una tarea implementada, probada y cerrada. El
estado vive en `.specify/` y `specs/`, así que el día siguiente empieza con
`$TK recover` o `$TK siguiente`, no con explicaciones.

## Terminal, chat o extensión: qué necesita cada cosa

El toolkit vive **una sola vez** en su máquina: el proyecto del usuario no
lleva una copia, solo la ruta en `.vscode/settings.json`. Integrarlo con el
IDE tampoco es instalar nada en el editor; cada superficie se consigue así:

| Superficie | Qué añade | Cómo se consigue |
|---|---|---|
| **Chat del IDE** | los comandos `/sdd-enrich`, `/sdd-plan`, `/sdd-test`… | `init --cliente copilot` escribe `.github/skills/` en el proyecto. Nada que instalar |
| **Extensión de VS Code** | vista `Fases y tareas`, barra de estado, paleta `SDD: …`, aviso de comandos desactualizados | instalar el `.vsix`. **Opcional** |
| **Terminal** | todos los subcomandos, incluidos los que no tienen botón | `python3 cli/main.py …` desde la raíz de tu proyecto, o con `--root RUTA` desde cualquier carpeta |

**Basta el chat** para el flujo completo, los catorce: `/sdd`, `/sdd-enrich`,
`/sdd-specify`, `/sdd-clarify`, `/sdd-plan`, `/sdd-plan-gate`, `/sdd-tasks`,
`/sdd-analyze`, `/sdd-build`, `/sdd-pin`, `/sdd-test`, `/sdd-traza`,
`/sdd-status` y `/sdd-cierre`. Cada uno ejecuta su subcomando de la CLI: no hay
dos caminos, hay dos puertas a lo mismo.

**Basta la extensión** para mirar y lanzar ese flujo desde la vista lateral y
la paleta, con progreso, «Cancelar», «Ver salida» y el aviso para regenerar
los comandos cuando mueve el repositorio del toolkit.

La paleta `SDD: …` cubre los subcomandos habituales (`status`, `tablero`,
`plan`, `tasks`, `test`, `traza`, `diff`…); la terminal hace falta para los
**flags** que ningún botón expone:

- aceptar un enriquecimiento: `enrich --accept ENR-001`;
- cerrar una tarea justificando las observaciones:
  `build PLAN-001 --done TASK-001 --nota "…"`;
- `--root` para actuar sobre otra carpeta sin entrar en ella;
- `comandos --regenerar` si movió el repo del toolkit (la vista lateral también
  lo ofrece desde su aviso, así que aquí es el plan B);
- el servidor MCP (`python3 mcp/server.py`), CI y scripts.

Y ni siquiera esos son obligatorios a mano: se le piden al chat con el dato en
la misma frase («ejecuta `enrich --accept ENR-001`») y el agente corre la CLI
por usted. El atajo `toolkit` solo acorta lo que se escribe en una terminal; no
cambia ningún comportamiento.

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

# 4. Generar la SPEC (aprobarla es opcional: `plan` no la exige)
toolkit specify ENR-001 --titulo "Kiosco"
# toolkit specify --approve SPEC-001

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
toolkit comandos                     # todos los clientes
toolkit comandos --cliente cursor    # repetible; solo los que use
toolkit comandos --verificar         # ¿siguen existiendo las rutas grabadas?
toolkit comandos --regenerar         # reescribir con la ruta actual y limpiar
```

`--verificar` no escribe nada: recorre los archivos ya generados, extrae la
ruta absoluta que llevan dentro y falla si esa ruta ya no existe —porque el
toolkit se movió o se borró— diciendo a cuál apuntan y cómo regenerarlos.
`toolkit status` hace la misma comprobación al terminar y, si encuentra rutas
muertas, lo avisa en una línea con el comando para regenerar.

`--regenerar` además retira los `.github/prompts/<nombre>.prompt.md` que
escribieron versiones anteriores: con el prompt file al lado de la skill, el menú
`/` del chat de VS Code lista cada comando dos veces. Solo borra los archivos
que llevan la cabecera del toolkit —uno escrito por el usuario se queda— y, si
el proyecto venía solo con prompts, los cuenta como instalados para regenerar
la skill antes de retirarlos.

| Cliente | Destino | Se invoca con |
|---|---|---|
| Claude Code | `.claude/skills/<nombre>/SKILL.md` | `/sdd-status` |
| Cursor | `.cursor/commands/<nombre>.md` | `/sdd-status` |
| Copilot (VS Code) | `.github/skills/<nombre>/SKILL.md` (arneses `Copilot` y `Local`) | `/sdd-status` |
| Windsurf | `.windsurf/workflows/<nombre>.md` | `/sdd-status` |
| Antigravity | `.agents/skills/<nombre>/SKILL.md` | `/sdd-status` |
| Cline | `.clinerules/workflows/<nombre>.md` | `/sdd-status.md` |
| Kilo Code | `.kilo/commands/<nombre>.md` | `/sdd-status` |

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
tests/      Suite pytest (469 tests, uno o más por RF)
ide/vscode/ Extensión VS Code (RF-39) + matriz de compatibilidad
mcp/        Servidor MCP stdio (RF-40)
docs/       SPEC-v0.1.md (requerimientos §44 y marco del producto)
```

## Estado del proyecto

- ✅ §44 completo (30/30) y las RF definidas en el código (RF-01 a RF-43;
  no existe RF-20) verificadas con tests.
- ⏳ Pendiente en entorno real: 4 de las 29 casillas de VS Code (25 vistas el
  2026-11-11), Antigravity, y abrir los comandos en Cursor, Windsurf, Cline,
  Kilo y Claude Code. El detalle está en `ide/COMPATIBILIDAD.md`.
- La fuente de verdad es `docs/SPEC-v0.1.md`; cada RF cita su sección.

## Contribuir

- Guía: [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Código de conducta: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- Cambios por versión: [`CHANGELOG.md`](CHANGELOG.md).
- Proceso de release: [`docs/RELEASES.md`](docs/RELEASES.md).
- Rama protegida: [`docs/BRANCH_PROTECTION.md`](docs/BRANCH_PROTECTION.md).
- Integración continua: `.github/workflows/ci.yml` (Python 3.11–3.14).
- Licencia: MIT (ver [`LICENSE`](LICENSE)).
