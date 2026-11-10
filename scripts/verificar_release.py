#!/usr/bin/env python3
"""Verificación posterior a publicar una release (docs/RELEASES.md).

Comprueba en un solo comando, para una versión dada:

1. que el tag `vX.Y.Z` existe en local y en `origin`, que es anotado y que
   ambos apuntan al mismo objeto;
2. que ese tag contiene la versión en `pyproject.toml` y como primera
   entrada con fecha del CHANGELOG;
3. que la release de GitHub no quedó en borrador ni marcada como previa;
4. que cada enlace `.../blob/<ref>/<ruta>` de `docs/release-notes-vX.Y.Z.md`
   apunta al tag y que la ruta existe en esa ref.

Uso:

    python3 scripts/verificar_release.py [VERSION]

Sin argumentos usa la versión de `pyproject.toml`. Sale con 0 si todo pasa
y con 1 listando los fallos. No modifica nada.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

RAIZ = Path(__file__).resolve().parent.parent

_BLOB = re.compile(
    r"https://github\.com/([^/\s]+)/([^/\s]+)/blob/([^/\s)]+)/([^)\s]+)")
_VERSION_TOML = re.compile(r'^version = "([^"]+)"', re.MULTILINE)
_VERSION_CHANGELOG = re.compile(r"^## \[([^\]]+)\] — \d{4}-\d{2}-\d{2}$",
                                re.MULTILINE)


@dataclass(frozen=True)
class Salida:
    """Resultado de un comando externo."""

    codigo: int
    stdout: str = ""
    stderr: str = ""


def correr(comando: list[str]) -> Salida:
    """Ejecuta un comando en la raíz del repo y captura su salida."""
    try:
        proceso = subprocess.run(comando, cwd=RAIZ, capture_output=True,
                                 text=True)
    except OSError as error:
        return Salida(127, stderr=str(error))
    return Salida(proceso.returncode, proceso.stdout.strip(),
                  proceso.stderr.strip())


def version_local() -> str:
    """Versión declarada en `pyproject.toml`."""
    datos = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    return str(datos["project"]["version"])


def _enlaces(notas: str) -> list[tuple[str, str, str]]:
    """Enlaces a ficheros del repo: (owner/repo, ref, ruta)."""
    return [("".join((dueno, "/", repo)), ref, ruta)
            for dueno, repo, ref, ruta in _BLOB.findall(notas)]


def _tag_remoto(correr_comando: Callable[[list[str]], Salida],
                tag: str) -> Salida:
    return correr_comando(["git", "ls-remote", "--tags", "origin",
                           f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"])


def verificar(version: str,
              correr_comando: Callable[[list[str]], Salida] = correr,
              ) -> list[tuple[bool, str]]:
    """Ejecuta las comprobaciones y devuelve pares (correcto, mensaje)."""
    tag = f"v{version}"
    resultados: list[tuple[bool, str]] = []

    def anotar(correcto: bool, mensaje: str) -> bool:
        resultados.append((correcto, mensaje))
        return correcto

    local = correr_comando(["git", "rev-parse", "--verify", "--quiet",
                            f"refs/tags/{tag}"])
    if local.codigo != 0:
        anotar(False, f"falta el tag {tag} en local")
        return resultados
    objeto = local.stdout.strip()

    clase = correr_comando(["git", "cat-file", "-t", objeto]).stdout.strip()
    anotar(clase == "tag",
           f"tag {tag} anotado" if clase == "tag"
           else f"tag {tag} no es anotado (tipo {clase or 'desconocido'})")

    pelado = correr_comando(["git", "rev-parse", f"{tag}^{{}}"]).stdout.strip()
    remoto = _tag_remoto(correr_comando, tag)
    lineas = {}
    for linea in remoto.stdout.splitlines():
        sha, _, referencia = linea.partition("\t")
        lineas[referencia.strip()] = sha.strip()
    en_remoto, pelado_remoto = lineas.get(f"refs/tags/{tag}"), lineas.get(
        f"refs/tags/{tag}^{{}}")
    anotar(bool(en_remoto) and en_remoto == objeto
           and pelado_remoto == pelado,
           f"tag {tag} en origin coincide con el local" if en_remoto
           else f"falta el tag {tag} en origin")

    toml = correr_comando(["git", "show", f"{tag}:pyproject.toml"])
    version_tag = _VERSION_TOML.search(toml.stdout)
    anotar(bool(version_tag) and version_tag.group(1) == version,
           f"pyproject.toml en {tag} declara {version_tag.group(1)}"
           if version_tag
           else f"no se pudo leer la versión en {tag}:pyproject.toml")

    changelog = correr_comando(["git", "show", f"{tag}:CHANGELOG.md"])
    publicadas = _VERSION_CHANGELOG.findall(changelog.stdout)
    anotar(bool(publicadas) and publicadas[0] == version,
           f"primera versión con fecha del CHANGELOG en {tag}: "
           f"{publicadas[0] if publicadas else 'ninguna'}")

    release = correr_comando(["gh", "release", "view", tag, "--json",
                              "tagName,isDraft,isPrerelease"])
    if release.codigo != 0:
        anotar(False, f"no se pudo leer la release {tag}: "
                      f"{release.stderr or release.stdout}")
    else:
        try:
            datos = json.loads(release.stdout)
        except json.JSONDecodeError:
            anotar(False, f"gh devolvió datos ilegibles para la release {tag}")
        else:
            borrador, previa = datos.get("isDraft"), datos.get("isPrerelease")
            anotar(not borrador and not previa,
                   f"release {tag} publicada"
                   if not borrador and not previa
                   else f"release {tag} sin publicar (borrador={borrador}, "
                        f"previa={previa})")

    notas = correr_comando(["git", "show", f"{tag}:docs/release-notes-{tag}.md"])
    if notas.codigo != 0:
        anotar(False, f"falta docs/release-notes-{tag}.md en {tag}")
        return resultados
    enlaces = _enlaces(notas.stdout)
    if not enlaces:
        anotar(False, f"docs/release-notes-{tag}.md no enlaza ficheros del repo")
        return resultados
    for repositorio, ref, ruta in enlaces:
        if ref != tag:
            anotar(False, f"{ruta} apunta a {ref}, no a {tag}")
            continue
        consulta = correr_comando([
            "gh", "api", f"repos/{repositorio}/contents/{ruta}?ref={ref}",
            "--jq", ".path"])
        anotar(consulta.codigo == 0,
               f"{ruta} existe en {ref}" if consulta.codigo == 0
               else f"{ruta} devuelve {consulta.codigo or 1} en {ref}")
    return resultados


def main(argumentos: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argumentos is None else argumentos)
    if args and args[0] in {"-h", "--help"}:
        print(__doc__.strip())
        return 0
    version = args[0].removeprefix("v") if args else version_local()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(f"⛔ versión no válida: {version!r} (se espera X.Y.Z)")
        return 1
    print(f"Verificando la release v{version}…")
    fallos = 0
    for correcto, mensaje in verificar(version):
        print(f"{'✅' if correcto else '⛔'} {mensaje}")
        fallos += 0 if correcto else 1
    if fallos:
        print(f"\n⛔ {fallos} comprobación(es) fallida(s)")
        return 1
    print(f"\n✅ v{version} verificada: tag, release y enlaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
