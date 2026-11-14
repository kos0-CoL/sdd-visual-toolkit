"""Empaqueta la extensión en el `.vsix` que se adjunta a cada release.

El nombre y la versión salen de `ide/vscode/package.json`, igual que en el
manifiesto, así que el archivo no se renombra a mano. Después de empaquetar lo
revisa con el mismo verificador que usa la release: si el paquete quedó
incompleto, esto sale con código 1 en vez de publicar algo que no arranca.

Uso: python3 scripts/empaquetar_extension.py [--destino DIR] [--sin-verificar]

Lo corre el workflow de release en cada tag `v*`; en local sirve para probar el
paquete antes de etiquetar.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXTENSION = RAIZ / "ide" / "vscode"
sys.path.insert(0, str(RAIZ / "scripts"))

import verificar_vsix


def version(raiz: Path = EXTENSION) -> str:
    """La versión del manifiesto: es la que lleva el nombre del `.vsix`."""
    manifiesto = json.loads((raiz / "package.json").read_text(encoding="utf-8"))
    return manifiesto["version"]


def empaquetar(destino: Path | None = None, revisar: bool = True,
               correr=subprocess.run, raiz: Path = EXTENSION) -> Path:
    """Genera el `.vsix` y devuelve su ruta; falla si el paquete no sirve."""
    npx = shutil.which("npx")
    if npx is None:
        raise RuntimeError(
            "no encontré `npx`: hace falta Node.js para empaquetar la extensión")
    carpeta = Path(destino) if destino else raiz
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"sdd-visual-toolkit-{version(raiz)}.vsix"
    orden = [npx, "--yes", "@vscode/vsce", "package", "--no-dependencies",
             "--allow-missing-repository", "-o", str(ruta)]
    proceso = correr(orden, cwd=raiz, capture_output=True, text=True)
    if proceso.returncode != 0:
        salida = [linea for linea in
                  (proceso.stdout + proceso.stderr).splitlines() if linea.strip()]
        detalle = salida[-1] if salida else f"código {proceso.returncode}"
        raise RuntimeError(f"`vsce package` falló: {detalle}")
    if revisar:
        problemas = verificar_vsix.revisar(ruta)
        if problemas:
            raise RuntimeError("el .vsix quedó mal: " + "; ".join(problemas))
    return ruta


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Empaqueta la extensión de VS Code en un .vsix verificado.")
    parser.add_argument("--destino",
                        help="carpeta donde dejar el .vsix (defecto: ide/vscode)")
    parser.add_argument("--sin-verificar", action="store_true",
                        help="empaquetar sin pasar el verificador")
    args = parser.parse_args(argv)
    try:
        ruta = empaquetar(args.destino, revisar=not args.sin_verificar)
    except RuntimeError as error:
        print(f"⛔ {error}", file=sys.stderr)
        return 1
    try:
        mostrada = ruta.relative_to(RAIZ)
    except ValueError:
        mostrada = ruta
    print(f"✓ {mostrada} ({ruta.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
