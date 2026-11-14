"""Deja el proyecto listo para el IDE al inicializarlo (§29, RF-39).

El usuario abre la carpeta y ya tiene la capa visual: la extensión sabe qué
intérprete y qué `cli/main.py` ejecutar sin configurar nada, y las tareas SDD
aparecen en el explorador de tareas del editor. Solo se escriben archivos que
no existan; lo que el usuario ya tenga no se toca.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sysconfig
import tomllib

CARPETA = ".vscode"
AJUSTES = "settings.json"
TAREAS = "tasks.json"
GITIGNORE = ".gitignore"

# La capa visual es esta extensión: se recomienda en el proyecto y se instala
# si el .vsix está a mano (viaja con el paquete y con el repo).
EXTENSION_ID = "sdd-toolkit.sdd-visual-toolkit"
EXTENSIONES = "extensions.json"
IDES_VSCODE = ("vscode", "trae", "cursor", "windsurf")
# Binario con el que cada IDE instala una extensión desde la terminal.
CLI_IDE = {
    "vscode": ("code", "code-insiders"),
    "trae": ("trae", "trae-cn"),
    "cursor": ("cursor",),
    "windsurf": ("windsurf",),
}

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


def actualizar_ide(raiz, cli, python: str, gitignore: bool = True
                   ) -> tuple[list[str], list[str], list[str]]:
    """Sobrescribe los ajustes y tareas del IDE con la copia del toolkit en uso.

    Se invoca tras actualizar el core para que `.vscode/settings.json` y
    `.vscode/tasks.json` apunten al `cli/main.py` y al intérprete de la nueva
    versión. Devuelve `(escritos, existentes, añadidas)` como `preparar`.
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
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(contenido, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        escritos.append(relativo)
    if not gitignore:
        return escritos, existentes, añadidas
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


def recomendar_extension(raiz) -> tuple[pathlib.Path, bool]:
    """Añade la extensión a `.vscode/extensions.json` sin pisar lo que haya.

    VS Code ofrece instalar las extensiones recomendadas al abrir la carpeta,
    así que el usuario no tiene que buscar el `.vsix` a mano. Devuelve
    `(ruta, agregada)`; con `agregada=False` ya estaba y no se tocó el archivo.
    """
    destino = pathlib.Path(raiz) / CARPETA / EXTENSIONES
    datos = {}
    if destino.exists():
        try:
            previo = json.loads(destino.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previo = {}
        if isinstance(previo, dict):
            datos = previo
    recomendadas = datos.get("recommendations")
    if not isinstance(recomendadas, list):
        recomendadas = []
    if EXTENSION_ID in recomendadas:
        return destino, False
    datos["recommendations"] = recomendadas + [EXTENSION_ID]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(datos, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destino, True


def _clave_version(ruta: pathlib.Path) -> tuple[int, ...]:
    """Números del nombre del .vsix, para quedarse con el más nuevo."""
    numeros = [int(n) for n in re.findall(r"\d+", ruta.stem)[:4]]
    return tuple(numeros) or (0,)


def buscar_vsix() -> pathlib.Path | None:
    """Busca el `.vsix` que instala la extensión.

    Primero `SDD_VSIX` (para probar un paquete concreto), después los datos
    que deja el paquete instalado (`share/sdd-toolkit`) y por último la copia
    del repo, que es donde vive mientras se desarrolla.
    """
    candidatos: list[pathlib.Path] = []
    desde_env = os.environ.get("SDD_VSIX")
    if desde_env:
        ruta = pathlib.Path(desde_env).expanduser()
        if ruta.is_file():
            candidatos.append(ruta)
    datos = pathlib.Path(sysconfig.get_path("data")) / "share" / "sdd-toolkit"
    if datos.is_dir():
        candidatos.extend(datos.glob("*.vsix"))
    aqui = pathlib.Path(__file__).resolve()
    for base in (aqui.parent, *aqui.parents[1:5]):
        carpeta = base / "ide" / "vscode"
        if carpeta.is_dir():
            candidatos.extend(carpeta.glob("*.vsix"))
            break
    existentes = [ruta for ruta in candidatos if ruta.is_file()]
    if not existentes:
        return None
    return max(existentes, key=_clave_version)


def instalar_extension(ide: str, vsix) -> tuple[bool, str]:
    """Instala el `.vsix` con el CLI del IDE. Devuelve `(ok, detalle)`.\n
    `--force` reemplaza la versión que hubiera: el `.vsix` es el que trae esta
    copia del toolkit y tiene que mandar sobre una instalación anterior.
    """
    binarios = CLI_IDE.get(ide, ())
    binario = next((nombre for nombre in binarios if shutil.which(nombre)), None)
    if binario is None:
        return False, ("no encontré el comando " + " ni ".join(binarios)
                       + " en el PATH")
    try:
        proceso = subprocess.run(
            [binario, "--install-extension", str(vsix), "--force"],
            capture_output=True, text=True, timeout=180,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"no se pudo ejecutar {binario}: {error}"
    salida = [linea.strip() for linea in
              (proceso.stdout + "\n" + proceso.stderr).splitlines() if linea.strip()]
    if proceso.returncode != 0:
        detalle = salida[-1] if salida else f"código {proceso.returncode}"
        return False, f"{binario} falló: {detalle}"
    return True, f"{binario} instaló {pathlib.Path(vsix).name}"


def configurar_ide(raiz, cli, python: str, ide: str) -> dict:
    """Deja la capa visual lista para el IDE elegido y cuenta qué hizo.

    Para IDEs basados en VS Code (vscode, trae, cursor, windsurf) escribe
    `.vscode/settings.json` y `.vscode/tasks.json`, recomienda la extensión e
    intenta instalarla desde el `.vsix` con el CLI del IDE. Para
    IntelliJ/Eclipse y Neovim/Sublime deja `.sdd/ide-config.json`.

    Devuelve un informe con `ide`, `recomendada`, `instalada`, `vsix`,
    `comando` (la orden manual si no se pudo instalar) y `detalle`.
    """
    raiz = pathlib.Path(raiz)
    cli_path = pathlib.Path(cli)
    informe = {"ide": ide, "recomendada": False, "instalada": False,
               "vsix": None, "comando": None, "detalle": ""}

    if ide in IDES_VSCODE:
        # IDEs basados en VS Code: ya se escriben en `preparar`, pero
        # configurar_ide los sobreescribe para asegurar la ruta correcta.
        escribir_archivos_ide(raiz, cli_path, python)
        _, agregada = recomendar_extension(raiz)
        informe["recomendada"] = True
        informe["detalle"] = ("recomendada en .vscode/extensions.json" if agregada
                              else "ya estaba recomendada")
        vsix = buscar_vsix()
        if vsix is None:
            informe["detalle"] = ("no encontré el .vsix de la extensión; "
                                  "instalala desde Extensiones → Instalar desde VSIX…")
            return informe
        informe["vsix"] = str(vsix)
        binario = next((nombre for nombre in CLI_IDE.get(ide, ())
                        if shutil.which(nombre)), None)
        informe["comando"] = (f"{binario or CLI_IDE.get(ide, ('code',))[0]} "
                              f"--install-extension {vsix} --force")
        ok, detalle = instalar_extension(ide, vsix)
        informe["instalada"] = ok
        informe["detalle"] = detalle
        return informe

    if ide in ("intellij", "eclipse"):
        _configurar_ide_jetbrains_eclipse(raiz, cli_path, python, ide)
        informe["detalle"] = (f"{ide} todavía no tiene extensión: quedó "
                              ".sdd/ide-config.json y la CLI como interfaz")
        return informe

    if ide in ("neovim", "sublime"):
        _configurar_ide_editor_ligero(raiz, cli_path, python, ide)
        informe["detalle"] = (f"{ide} todavía no tiene extensión: quedó "
                              ".sdd/ide-config.json y la CLI como interfaz")
    return informe


def escribir_archivos_ide(raiz: pathlib.Path, cli: pathlib.Path, python: str) -> None:
    """Escribe settings.json y tasks.json para IDEs basados en VS Code."""
    carpeta = raiz / CARPETA
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / AJUSTES).write_text(
        json.dumps(_ajustes(python, cli), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (carpeta / TAREAS).write_text(
        json.dumps(_tareas(python, cli), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _configurar_ide_jetbrains_eclipse(raiz, cli, python: str, ide: str) -> None:
    """Archivo de configuración genérico para IntelliJ/Eclipse."""
    config_dir = raiz / ".sdd"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "ide": ide,
        "cli_path": str(cli),
        "python": python,
        "toolkit_name": NOMBRE_PAQUETE,
        "specify_dir": ".specify",
        "clarify_command": "clarify",
    }
    (config_dir / "ide-config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _configurar_ide_editor_ligero(raiz, cli, python: str, ide: str) -> None:
    """Archivo de configuración para Neovim/Sublime."""
    config_dir = raiz / ".sdd"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "ide": ide,
        "cli_path": str(cli),
        "python": python,
        "toolkit_name": NOMBRE_PAQUETE,
        "specify_dir": ".specify",
        "clarify_command": "clarify",
    }
    (config_dir / "ide-config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def preparar(raiz, cli, python: str, gitignore: bool = True
             ) -> tuple[list[str], list[str], list[str]]:
    """Escribe los ajustes y las tareas del IDE que falten, y el `.gitignore`.

    Devuelve `(escritos, existentes, añadidas)`: rutas relativas a la raíz de lo
    creado y de lo que ya estaba, y las reglas que se añadieron a un
    `.gitignore` que ya existía. Las reglas que ya cubre no se duplican y se
    respeta el contenido previo tal cual. Con `gitignore=False` (lo que pide
    `init --sin-gitignore`) no lo escribe ni lo toca.
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
    if not gitignore:
        return escritos, existentes, añadidas
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
