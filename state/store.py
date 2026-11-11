"""Persistencia atómica del estado (§13.5, §35).

Todo se guarda bajo `<proyecto>/.specify/`. Las escrituras usan archivo
temporal + renombrado atómico para no dejar JSON a medio escribir.
Solo biblioteca estándar.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

SPECIFY_DIR = ".specify"
REQUERIMIENTOS_FILE = "requerimientos.json"


class StoreError(OSError):
    """El estado persistido no se pudo leer o escribir de forma segura."""


def descubrir_raiz(inicio: Path | None = None) -> Path:
    """Sube desde `inicio` (o cwd) hasta encontrar `.specify/`."""
    actual = (inicio or Path.cwd()).resolve()
    for candidato in (actual, *actual.parents):
        if (candidato / SPECIFY_DIR).is_dir():
            return candidato
    raise StoreError(
        "no hay proyecto toolkit aquí (falta .specify/); ejecute `toolkit init`"
    )


def inicializar_proyecto(raiz: Path) -> Path:
    """Crea la estructura §35 sin tocar nada que ya exista del usuario."""
    raiz = raiz.resolve()
    specify = raiz / SPECIFY_DIR
    (specify / "memory").mkdir(parents=True, exist_ok=True)
    (specify / "checkpoints").mkdir(parents=True, exist_ok=True)
    (raiz / "specs").mkdir(exist_ok=True)
    # Solo donde los comandos escriben de verdad: `specify` deja la SPEC en
    # specs/, y `plan`, `tasks` y `analyze` escriben bajo .specify/. Antes se
    # creaban plans/ y tasks/ en la raíz, que nadie llegaba a usar.
    for sub in ("planes", "tareas", "informes"):
        (specify / sub).mkdir(exist_ok=True)
    # El estado de ejecución y el historial los escribe el journal dentro de
    # `memory/`; antes init dejaba aquí un `current_task.json` y un
    # `execution_history.jsonl` que nadie leía ni actualizaba.
    for nombre, contenido in (
        (REQUERIMIENTOS_FILE, []),
    ):
        destino = specify / nombre
        if not destino.exists():
            _escritura_atomica(destino, contenido, texto=isinstance(contenido, str))
    return raiz


def _fsync_dir(carpeta: Path) -> None:
    """Sincroniza el directorio para que el renombrado sobreviva a un corte.

    Sin este fsync un rename puede perderse aunque el archivo esté completo
    (§13.5, §35). En plataformas sin fsync de directorio (p. ej. Windows)
    se declara no disponible: la escritura atómica sigue siendo válida.
    """
    try:
        fd = os.open(str(carpeta), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _escritura_atomica(destino: Path, contenido, texto: bool = False) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, temporal = tempfile.mkstemp(
        dir=str(destino.parent), prefix=destino.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            if texto:
                fh.write(contenido)
            else:
                json.dump(contenido, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporal, destino)
        _fsync_dir(destino.parent)
    except BaseException:
        try:
            os.unlink(temporal)
        except OSError:
            pass
        raise


def leer_json(ruta: Path):
    try:
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as error:
        raise StoreError(f"archivo de estado inexistente: {ruta}") from error
    except json.JSONDecodeError as error:
        raise StoreError(f"archivo de estado corrupto: {ruta} ({error})") from error


def escribir_json(ruta: Path, contenido) -> None:
    try:
        _escritura_atomica(ruta, contenido)
    except OSError as error:
        raise StoreError(f"no se pudo persistir {ruta}: {error}") from error


def ruta_requerimientos(raiz: Path) -> Path:
    return raiz / SPECIFY_DIR / REQUERIMIENTOS_FILE
