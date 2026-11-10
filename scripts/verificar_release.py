#!/usr/bin/env python3
"""Verificación posterior a publicar una release (docs/RELEASES.md).

Comprueba en un solo comando, para una versión dada:

1. que el tag `vX.Y.Z` existe en local y en `origin`, que es anotado y que
   ambos apuntan al mismo objeto;
2. que ese tag contiene la versión en `pyproject.toml` y como primera
   entrada con fecha del CHANGELOG;
3. que la release de GitHub no quedó en borrador ni marcada como previa;
4. que el cuerpo de la release es el de `docs/release-notes-vX.Y.Z.md` —sin
   contar espacios ni saltos finales— y no un texto autogenerado;
5. que cada enlace `.../blob/<ref>/<ruta>` de `docs/release-notes-vX.Y.Z.md`
   apunta al tag y que la ruta existe en esa ref.

Con `--previo` comprueba lo que se puede saber **antes** de crear el tag
(tag libre, árbol limpio, `HEAD` en `origin/main`, versión y CHANGELOG en el
árbol, `[No publicado]` vacía, notas con enlaces al tag futuro y versión
posterior a la última etiquetada).

Uso:

    python3 scripts/verificar_release.py [VERSION]
    python3 scripts/verificar_release.py --previo [VERSION]

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
_TAG_VERSION = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


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


def _normalizar(texto: str) -> list[str]:
    """Líneas sin espacios finales, para comparar cuerpos de release."""
    return [linea.rstrip() for linea in texto.strip().splitlines()]


def _enlaces(notas: str) -> list[tuple[str, str, str]]:
    """Enlaces a ficheros del repo: (owner/repo, ref, ruta)."""
    return [("".join((dueno, "/", repo)), ref, ruta)
            for dueno, repo, ref, ruta in _BLOB.findall(notas)]


def _tag_remoto(correr_comando: Callable[[list[str]], Salida],
                tag: str) -> Salida:
    return correr_comando(["git", "ls-remote", "--tags", "origin",
                           f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"])


def _vinetas_sin_publicar(changelog: str) -> list[str]:
    """Viñetas que siguen dentro de `[No publicado]`."""
    partes = changelog.split("## [No publicado]", 1)
    if len(partes) < 2:
        return []
    resto = partes[1]
    siguiente = re.search(r"^## \[", resto, re.MULTILINE)
    bloque = resto[:siguiente.start()] if siguiente else resto
    return re.findall(r"^- ", bloque, re.MULTILINE)


def _tupla(version: str) -> tuple[int, ...]:
    return tuple(int(parte) for parte in version.split("."))


def verificar_previo(version: str,
                     correr_comando: Callable[[list[str]], Salida] = correr,
                     raiz: Path = RAIZ,
                     ) -> list[tuple[bool, str]]:
    """Comprobaciones posibles antes de crear el tag `vX.Y.Z`."""
    tag = f"v{version}"
    resultados: list[tuple[bool, str]] = []

    def anotar(correcto: bool, mensaje: str) -> bool:
        resultados.append((correcto, mensaje))
        return correcto

    local = correr_comando(["git", "rev-parse", "--verify", "--quiet",
                            f"refs/tags/{tag}"])
    if local.codigo == 0:
        anotar(False, f"el tag {tag} ya existe en local: es inmutable, "
                      "use otra versión")
        return resultados
    remoto = correr_comando(["git", "ls-remote", "--tags", "origin",
                             f"refs/tags/{tag}"])
    if remoto.codigo == 0 and remoto.stdout.strip():
        anotar(False, f"el tag {tag} ya existe en origin: es inmutable, "
                      "use otra versión")
        return resultados
    anotar(True, f"tag {tag} libre en local y en origin")

    estado = correr_comando(["git", "status", "--porcelain"])
    anotar(not estado.stdout.strip(),
           "árbol limpio" if not estado.stdout.strip()
           else "hay cambios sin confirmar: el tag apuntaría a otro contenido")

    rama = correr_comando(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    cabeza = correr_comando(["git", "rev-parse", "HEAD"]).stdout.strip()
    publicado = correr_comando(["git", "rev-parse", "origin/main"])
    nombre_rama = rama.stdout.strip()
    if nombre_rama != "main":
        anotar(False, f"la rama actual es {nombre_rama or 'desconocida'}, "
                      "no main: el tag debe caer sobre main")
    elif not cabeza or cabeza != publicado.stdout.strip():
        anotar(False, "HEAD no coincide con origin/main: empuje antes de "
                      "etiquetar")
    else:
        anotar(True, "HEAD en main y sincronizado con origin")

    try:
        datos = tomllib.loads(
            (raiz / "pyproject.toml").read_text(encoding="utf-8"))
        en_arbol = str(datos["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        anotar(False, f"no se pudo leer la versión de pyproject.toml: {error}")
        return resultados
    anotar(en_arbol == version,
           f"pyproject.toml declara {version}" if en_arbol == version
           else f"pyproject.toml declara {en_arbol}, no {version}")

    try:
        changelog = (raiz / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError as error:
        anotar(False, f"no se pudo leer CHANGELOG.md: {error}")
        return resultados
    publicadas = _VERSION_CHANGELOG.findall(changelog)
    anotar(bool(publicadas) and publicadas[0] == version,
           f"primera versión con fecha del CHANGELOG: "
           f"{publicadas[0] if publicadas else 'ninguna'}")

    sin_publicar = _vinetas_sin_publicar(changelog)
    anotar(not sin_publicar,
           "`[No publicado]` quedó vacía" if not sin_publicar
           else f"`[No publicado]` conserva {len(sin_publicar)} viñeta(s): "
                "muévalas a la sección nueva")

    anotar(f"compare/{tag}...HEAD" in changelog
           and f"releases/tag/{tag}" in changelog,
           f"enlaces del pie apuntan a {tag}"
           if f"compare/{tag}...HEAD" in changelog
           and f"releases/tag/{tag}" in changelog
           else f"los enlaces del pie no apuntan a {tag}")

    notas_ruta = raiz / "docs" / f"release-notes-{tag}.md"
    try:
        notas = notas_ruta.read_text(encoding="utf-8")
    except OSError:
        anotar(False, f"falta docs/release-notes-{tag}.md")
        return resultados
    enlaces = _enlaces(notas)
    if not enlaces:
        anotar(False, f"docs/release-notes-{tag}.md no enlaza "
                      "ficheros del repo")
        return resultados
    for _repositorio, ref, ruta in enlaces:
        if ref != tag:
            anotar(False, f"{ruta} apunta a {ref}, no a {tag}")
        elif not (raiz / ruta).is_file():
            anotar(False, f"{ruta} no existe en el árbol")
        else:
            anotar(True, f"{ruta} existe y apunta a {tag}")

    etiquetas = correr_comando(["git", "tag", "--list", "v*"]).stdout.split()
    previas = [(m.groups(), m.group(0))
               for m in (_TAG_VERSION.match(e) for e in etiquetas) if m]
    if not previas:
        anotar(True, "no hay versiones etiquetadas todavía")
    else:
        grupos, ultima = max(previas, key=lambda par: _tupla(".".join(
            par[0])))
        anotar(_tupla(version) > _tupla(".".join(grupos)),
               f"{version} es posterior a {ultima}" if _tupla(version) >
               _tupla(".".join(grupos))
               else f"{version} no es posterior a {ultima}")
    return resultados


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

    cuerpo = None
    release = correr_comando(["gh", "release", "view", tag, "--json",
                              "tagName,isDraft,isPrerelease,body"])
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
            cuerpo = datos.get("body")
            anotar(not borrador and not previa,
                   f"release {tag} publicada"
                   if not borrador and not previa
                   else f"release {tag} sin publicar (borrador={borrador}, "
                        f"previa={previa})")

    notas = correr_comando(["git", "show", f"{tag}:docs/release-notes-{tag}.md"])
    if notas.codigo != 0:
        anotar(False, f"falta docs/release-notes-{tag}.md en {tag}")
        return resultados
    mismo_cuerpo = (cuerpo is not None
                    and _normalizar(cuerpo) == _normalizar(notas.stdout))
    anotar(mismo_cuerpo,
           f"el cuerpo de {tag} es el de "
           f"docs/release-notes-{tag}.md" if mismo_cuerpo
           else f"el cuerpo de {tag} no coincide con "
                f"docs/release-notes-{tag}.md: actualícelo con "
                f"`gh release edit {tag} --notes-file "
                f"docs/release-notes-{tag}.md`")

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
    previo = "--previo" in args
    args = [arg for arg in args if arg != "--previo"]
    version = args[0].removeprefix("v") if args else version_local()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(f"⛔ versión no válida: {version!r} (se espera X.Y.Z)")
        return 1
    if previo:
        print(f"Verificando antes de etiquetar v{version}…")
        resultados = verificar_previo(version)
    else:
        print(f"Verificando la release v{version}…")
        resultados = verificar(version)
    fallos = 0
    for correcto, mensaje in resultados:
        print(f"{'✅' if correcto else '⛔'} {mensaje}")
        fallos += 0 if correcto else 1
    if fallos:
        print(f"\n⛔ {fallos} comprobación(es) fallida(s)")
        return 1
    if previo:
        print(f"\n✅ {version} lista para etiquetar: "
              f"git tag -a v{version}")
    else:
        print(f"\n✅ v{version} verificada: tag, release y enlaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
