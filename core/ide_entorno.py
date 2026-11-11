"""Deja el proyecto listo para el IDE al inicializarlo (§29, RF-39).

El usuario abre la carpeta y ya tiene la capa visual: la extensión sabe qué
intérprete y qué `cli/main.py` ejecutar sin configurar nada, y las tareas SDD
aparecen en el explorador de tareas del editor. Solo se escriben archivos que
no existan; lo que el usuario ya tenga no se toca.
"""

from __future__ import annotations

import json
import pathlib

CARPETA = ".vscode"
AJUSTES = "settings.json"
TAREAS = "tasks.json"

# Una tarea del IDE no puede pedir un PLAN-ID ni un TASK-ID, así que se ofrecen
# solo los comandos que se ejecutan solos y leen el estado actual.
COMANDOS = (
    ("estado", "status"),
    ("tablero", "tablero"),
    ("siguiente", "siguiente"),
    ("árbol", "arbol"),
    ("instrucciones", "instrucciones"),
)


def _ajustes(python: str, cli: pathlib.Path) -> dict:
    return {
        "sddToolkit.python": python,
        "sddToolkit.cliPath": str(cli),
    }


def _tareas(python: str, cli: pathlib.Path) -> dict:
    return {
        "version": "2.0.0",
        "tasks": [
            {
                "label": f"SDD: {nombre}",
                "type": "process",
                "command": python,
                "args": [str(cli), "--root", "${workspaceFolder}", comando],
                "options": {"cwd": "${workspaceFolder}"},
                "problemMatcher": [],
            }
            for nombre, comando in COMANDOS
        ],
    }


def preparar(raiz, cli, python: str) -> tuple[list[str], list[str]]:
    """Escribe los ajustes y las tareas del IDE que falten.

    Devuelve `(escritos, existentes)` con las rutas relativas a la raíz, para
    que `init` pueda decir qué hizo sin afirmar de más.
    """
    raiz = pathlib.Path(raiz)
    escritos: list[str] = []
    existentes: list[str] = []
    for nombre, contenido in (
        (AJUSTES, _ajustes(python, pathlib.Path(cli))),
        (TAREAS, _tareas(python, pathlib.Path(cli))),
    ):
        destino = raiz / CARPETA / nombre
        relativo = f"{CARPETA}/{nombre}"
        if destino.exists():
            existentes.append(relativo)
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(contenido, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        escritos.append(relativo)
    return escritos, existentes
