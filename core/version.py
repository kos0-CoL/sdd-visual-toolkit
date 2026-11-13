"""Versión del paquete en una sola fuente (CLI y servidor MCP).

Verificación de actualizaciones contra PyPI con la biblioteca estándar:
sin dependencias externas, sin red automática y sin nada que se instale solo.
El usuario decide si actualiza y cuándo.
"""

from __future__ import annotations

import json
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version_instalada
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

NOMBRE_PAQUETE = "sdd-toolkit"

_RAIZ = Path(__file__).resolve().parent.parent

_PYPI_URL = f"https://pypi.org/pypi/{NOMBRE_PAQUETE}/json"


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


def _parsear_version(texto: str) -> tuple[int, ...]:
    """Convierte una versión semántica en tupla de enteros para comparar."""
    partes = []
    for parte in str(texto).strip().split("."):
        numero = ""
        for caracter in parte:
            if caracter.isdigit():
                numero += caracter
            else:
                break
        partes.append(int(numero) if numero else 0)
    return tuple(partes)


def _mayor(instalada: str, disponible: str) -> bool:
    """¿La versión disponible supera a la instalada?"""
    return _parsear_version(disponible) > _parsear_version(instalada)


def verificar_actualizacion(timeout: int = 10) -> dict:
    """Consulta PyPI y compara con la versión instalada.

    Devuelve un dict con:
      - instalada: versión que se está ejecutando
      - disponible: última versión en PyPI (o None si no se pudo consultar)
      - hay_actualizacion: bool, True solo si disponible > instalada
      - error: mensaje si la consulta falló (None si todo bien)

    Nunca instala nada ni pide red por su cuenta: es solo una consulta de
    solo lectura. El llamador decide qué hacer con el resultado.
    """
    instalada = version()
    resultado: dict = {
        "instalada": instalada,
        "disponible": None,
        "hay_actualizacion": False,
        "error": None,
    }
    try:
        req = Request(
            _PYPI_URL,
            headers={"Accept": "application/json", "User-Agent": "sdd-toolkit"},
        )
        with urlopen(req, timeout=timeout) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
        disponible = str(datos["info"]["version"])
        resultado["disponible"] = disponible
        resultado["hay_actualizacion"] = _mayor(instalada, disponible)
    except URLError as error:
        resultado["error"] = f"no se pudo consultar PyPI: {error}"
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        resultado["error"] = f"respuesta de PyPI no válida: {error}"
    return resultado
