"""Comandos de barra para agentes de código (§31, §30).

Un agente solo descubre lo que está en su workspace: `.claude/skills/`,
`.cursor/commands/`, `.github/prompts/`, `.windsurf/workflows/` o
`.agents/skills/`. Este módulo guarda el catálogo una sola vez y lo escribe
en el formato de cada cliente, con la ruta absoluta de la CLI dentro del
proyecto del usuario —la extensión del IDE hace lo mismo y por eso también
necesita `cliPath`.

Cada archivo generado invoca la CLI y declara que su salida es la fuente de
la verdad: el agente no reemplaza el estado por un resumen de memoria.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Comando:
    """Un comando de barra y el subcomando de la CLI que ejecuta."""

    nombre: str
    descripcion: str
    argv: str
    pista: str = ""


# El orden es el del flujo SDD: es el que verá el usuario al tipear "/".
#
# Cada descripción dice qué hace y **cuándo usarlo**: en una skill es lo
# único que el agente ve antes de decidir si la aplica (§30).
COMANDOS: tuple[Comando, ...] = (
    Comando("sdd", "Qué hacer ahora: tablero y próximo comando recomendado. "
            "Úsalo al empezar o cuando no sepas qué paso toca.",
            "siguiente"),
    Comando("sdd-status", "Estado del proyecto: fase, progreso y bloqueos. "
            "Úsalo para ver dónde está el trabajo antes de elegir el paso "
            "siguiente.", "status"),
    # La idea va como un solo argumento: sin comillas, `enrich una idea`
    # termina en `unrecognized arguments`.
    Comando("sdd-enrich", "Enriquecer una idea y dejarla pendiente de "
            "validar. Úsalo cuando la idea cabe en una frase y hay que "
            "convertirla en requerimientos.",
            "enrich", pista='idea entre comillas: "…"'),
    Comando("sdd-specify", "Generar la SPEC a partir de un ENR validado. "
            "Úsalo cuando el requerimiento ya está aceptado y toca escribir "
            "la especificación.", "specify", pista="ENR-ID"),
    Comando("sdd-clarify", "Responder las aclaraciones abiertas de una "
            "SPEC. Úsalo cuando quedan preguntas sin responder y no se "
            "puede planificar.", "clarify", pista="SPEC-ID"),
    Comando("sdd-plan", "Generar el plan técnico de una SPEC aprobada. "
            "Úsalo cuando la SPEC está clara y hay que decidir arquitectura "
            "y pasos.", "plan", pista="SPEC-ID"),
    Comando("sdd-plan-gate", "Aprobar el plan y superar el Quality Gate. "
            "Úsalo cuando el plan existe y falta la aprobación para "
            "escribir tareas.", "plan --gate", pista="PLAN-ID"),
    Comando("sdd-tasks", "Desglosar el plan en tareas verificables. Úsalo "
            "cuando el plan está aprobado y hay que repartirlo en tareas "
            "con prueba.", "tasks", pista="PLAN-ID"),
    Comando("sdd-analyze", "Informe de consistencia antes de implementar. "
            "Úsalo cuando las tareas ya existen y antes de tocar código.",
            "analyze", pista="PLAN-ID"),
    Comando("sdd-build", "Poner la siguiente tarea en curso. Úsalo cuando "
            "quieres empezar o retomar la implementación de una tarea.",
            "build", pista="PLAN-ID"),
    Comando("sdd-pin", "Congelar las interfaces de la tarea: línea base y "
            "desviaciones. Úsalo antes de editar archivos que otra tarea "
            "también toca.", "pin", pista="PLAN-ID --task TASK-ID"),
    Comando("sdd-test", "Correr el arnés de pruebas de una tarea. Úsalo "
            "cuando la implementación está lista para medirse.",
            "test", pista="TASK-ID"),
    Comando("sdd-traza", "Trazabilidad SPEC → test → evidencia. Úsalo "
            "cuando piden demostrar qué cubre cada requerimiento.",
            "traza", pista="SPEC-ID"),
    Comando("sdd-cierre", "Mensaje de cierre de la fase. Úsalo cuando la "
            "tarea o el plan terminan y hay que entregar el resumen.",
            "cierre", pista="TASK-ID o PLAN-ID"),
)

# Dónde busca cada cliente sus comandos. La clave es lo que acepta
# `toolkit comandos --cliente`.
CLIENTES: dict[str, str] = {
    "claude": ".claude/skills/{nombre}/SKILL.md",
    "cursor": ".cursor/commands/{nombre}.md",
    "copilot": ".github/prompts/{nombre}.prompt.md",
    "windsurf": ".windsurf/workflows/{nombre}.md",
    "antigravity": ".agents/skills/{nombre}/SKILL.md",
}

# Clientes cuyo formato no lleva frontmatter (Cursor lo ignora y el cuerpo
# solo es lo documentado).
SIN_FRONTMATTER = {"cursor"}

# Clientes que sustituyen `$ARGUMENTS` por lo que el usuario escribe detrás
# del comando. En el resto, el cuerpo pide los datos si faltan.
CON_ARGUMENTOS = {"claude"}

_CABECERA = "<!-- generado por `toolkit comandos`; se sobrescribe -->"


def _cuerpo(comando: Comando, python: str, cli: Path, cliente: str) -> str:
    orden = f'{python} "{cli}" --root . {comando.argv}'
    if cliente in CON_ARGUMENTOS:
        orden = f"{orden} $ARGUMENTS"
    lineas = [
        "Ejecuta este comando en la terminal, desde la raíz del proyecto:",
        "",
        f"    {orden}",
        "",
        "Reglas:",
        "",
        "- La salida de la CLI es la fuente de la verdad: muéstrala tal cual, "
        "sin reemplazarla por un resumen de memoria.",
        "- Si responde con ⛔ o 🔒, detente y muestra el mensaje; no lo rodees "
        "con otros comandos ni edites el estado a mano.",
        "- Si falta un identificador (ENR, SPEC, PLAN o TASK), pídelo antes de "
        "ejecutar; no lo inventes.",
    ]
    if cliente not in CON_ARGUMENTOS:
        lineas.append(
            "- Si el usuario escribió texto o un identificador detrás del "
            "comando, pásalo tal cual al final del comando.")
    return "\n".join(lineas)


def _escalar(texto: str) -> str:
    """Valor entre comillas simples, que es YAML válido para cualquier texto.

    Sin comillas, una descripción con «: » deja el frontmatter roto
    (`mapping values are not allowed here`) y el cliente no carga el comando.
    """
    return "'" + texto.replace("'", "''") + "'"


def _frontmatter(comando: Comando, cliente: str) -> str:
    if cliente in SIN_FRONTMATTER:
        return ""
    lineas = [
        "---",
        f"name: {_escalar(comando.nombre)}",
        f"description: {_escalar(comando.descripcion)}",
    ]
    if comando.pista:
        lineas.append(f"argument-hint: {_escalar(comando.pista)}")
    if cliente == "copilot":
        lineas.append(f"agent: {_escalar('agent')}")
    lineas.append("---")
    return "\n".join(lineas)


# La ruta horneada en el cuerpo: `{python} "{cli}" --root . {argv}`.
_RUTA_CLI = re.compile(r'"([^"]*cli[\\/]main\.py)" --root \.')


def instalados(raiz) -> dict[str, dict[Path, str]]:
    """Cliente → {archivo generado: ruta de CLI que lleva grabada}.

    Sirve para revisar lo ya escrito sin volver a generarlo: la ruta absoluta
    queda dentro del archivo, así que si el toolkit se movió hay que saberlo.
    """
    encontrados: dict[str, dict[Path, str]] = {}
    for cliente, plantilla in CLIENTES.items():
        carpeta = Path(raiz) / plantilla.split("{nombre}")[0]
        if not carpeta.is_dir():
            continue
        archivos: dict[Path, str] = {}
        for ruta in sorted(carpeta.rglob("*.md")):
            match = _RUTA_CLI.search(ruta.read_text(encoding="utf-8"))
            if match:
                archivos[ruta] = match.group(1)
        if archivos:
            encontrados[cliente] = archivos
    return encontrados


def generar(cliente: str, python: str, cli: Path) -> dict[str, str]:
    """Ruta relativa → contenido, para cada comando del catálogo."""
    if cliente not in CLIENTES:
        raise ValueError(f"cliente desconocido: {cliente}")
    plantilla = CLIENTES[cliente]
    archivos: dict[str, str] = {}
    for comando in COMANDOS:
        # El frontmatter va en la primera línea o el cliente lo ignora.
        partes = [parte for parte in (
            _frontmatter(comando, cliente), _CABECERA,
            _cuerpo(comando, python, cli, cliente)) if parte]
        archivos[plantilla.format(nombre=comando.nombre)] = (
            "\n\n".join(partes) + "\n")
    return archivos
