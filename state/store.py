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
    for sub in ("specs", "plans", "tasks"):
        (raiz / sub).mkdir(exist_ok=True)
    for nombre, contenido in (
        ("current_task.json", {"current_spec": None, "current_phase": None}),
        ("execution_history.jsonl", ""),
        (REQUERIMIENTOS_FILE, []),
    ):
        destino = specify / nombre
        if not destino.exists():
            _escritura_atomica(destino, contenido, texto=isinstance(contenido, str))
    return raiz


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
        os.replace(temporal, destino)
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
