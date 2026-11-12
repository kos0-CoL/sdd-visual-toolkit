"""Deja el proyecto listo para el IDE al inicializarlo (§29, RF-39).

El usuario abre la carpeta y ya tiene la capa visual: la extensión sabe qué
intérprete y qué `cli/main.py` ejecutar sin configurar nada, y las tareas SDD
aparecen en el explorador de tareas del editor. Solo se escriben archivos que
no existan; lo que el usuario ya tenga no se toca.
"""

from __future__ import annotations

import json
import pathlib
import tomllib

CARPETA = ".vscode"
AJUSTES = "settings.json"
TAREAS = "tasks.json"
GITIGNORE = ".gitignore"

# Lo que `init` deja escrito con rutas absolutas de esta máquina. Los
# comentarios van en su propia línea a propósito: en `.gitignore` un `#` al
# final no comenta nada, se vuelve parte del patrón y la regla deja de
# aplicarse.
REGLAS_IGNORADAS = (".vscode/settings.json", ".specify/cache/")
IGNORAR = (
    "# generado por `toolkit init`: rutas de esta máquina\n"
    + "\n".join(REGLAS_IGNORADAS)
    + "\n"
)

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


NOMBRE_PAQUETE = "sdd-toolkit"


def es_el_toolkit(carpeta) -> bool:
    """¿Esta carpeta es una copia del toolkit y no un proyecto del usuario?

    Evita el error de clonar el repositorio dentro del proyecto y correr `init`
    ahí: dejaría `.specify/` y `specs/` dentro del propio toolkit.
    """
    carpeta = pathlib.Path(carpeta)
    pyproject = carpeta / "pyproject.toml"
    if not (carpeta / "cli" / "main.py").is_file() or not pyproject.is_file():
        return False
    try:
        datos = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return datos.get("project", {}).get("name") == NOMBRE_PAQUETE


def clones_anidados(carpeta) -> list[str]:
    """Subcarpetas del proyecto que son copias del toolkit.

    Clonar el repositorio dentro del proyecto no hace falta —se instala una vez
    fuera— y deja una carpeta que nadie sabe para qué está.
    """
    carpeta = pathlib.Path(carpeta)
    try:
        hijos = sorted(p for p in carpeta.iterdir() if p.is_dir())
    except OSError:
        return []
    return [hijo.name for hijo in hijos if es_el_toolkit(hijo)]


def _ya_ignorada(regla: str, lineas: list[str]) -> bool:
    """¿El `.gitignore` ya ignora `regla`?

    Vale la regla exacta y también la carpeta que la contiene: con `.vscode/`
    o `.specify/` en el archivo, añadir la ruta de dentro sobra.
    """
    for linea in lineas:
        limpia = linea.strip()
        if not limpia or limpia.startswith(("#", "!")):
            continue
        if limpia == regla:
            return True
        if limpia.endswith("/") and (regla == limpia.rstrip("/")
                                      or regla.startswith(limpia)):
            return True
    return False


def preparar(raiz, cli, python: str) -> tuple[list[str], list[str], list[str]]:
    """Escribe los ajustes y las tareas del IDE que falten, y el `.gitignore`.

    Devuelve `(escritos, existentes, añadidas)`: rutas relativas a la raíz de lo
    creado y de lo que ya estaba, y las reglas que se añadieron a un
    `.gitignore` que ya existía. Las reglas que ya cubre no se duplican y se
    respeta el contenido previo tal cual.
    """
    raiz = pathlib.Path(raiz)
    escritos: list[str] = []
    existentes: list[str] = []
    añadidas: list[str] = []
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
    destino = raiz / GITIGNORE
    if not destino.exists():
        destino.write_text(IGNORAR, encoding="utf-8")
        escritos.append(GITIGNORE)
    else:
        previo = destino.read_text(encoding="utf-8")
        lineas = previo.splitlines()
        añadidas = [r for r in REGLAS_IGNORADAS if not _ya_ignorada(r, lineas)]
        if añadidas:
            separador = "" if not previo or previo.endswith("\n") else "\n"
            destino.write_text(
                previo + separador + "\n".join(añadidas) + "\n",
                encoding="utf-8")
        else:
            existentes.append(GITIGNORE)
    return escritos, existentes, añadidas
