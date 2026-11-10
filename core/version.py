"""Versión del paquete en una sola fuente (CLI y servidor MCP)."""

from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version_instalada
from pathlib import Path

NOMBRE_PAQUETE = "sdd-toolkit"

_RAIZ = Path(__file__).resolve().parent.parent


def version() -> str:
    """Versión del toolkit.

    Desde el árbol de fuentes manda `pyproject.toml`; en una instalación
    normal el archivo no viaja con el paquete, así que se usan los metadatos
    de distribución.
    """
    archivo = _RAIZ / "pyproject.toml"
    if archivo.exists():
        try:
            datos = tomllib.loads(archivo.read_text(encoding="utf-8"))
            return str(datos["project"]["version"])
        except (OSError, KeyError, tomllib.TOMLDecodeError):
            pass
    try:
        return _version_instalada(NOMBRE_PAQUETE)
    except PackageNotFoundError:
        return "desconocida"
