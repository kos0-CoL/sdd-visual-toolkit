"""Comprueba que el `.vsix` lleve solo lo que se instala y que nada vaya vacío.

`vsce` puede terminar con código 0 y un paquete incompleto: si cambian `files`
o `.vscodeignore`, o si un archivo queda a cero, el editor instala una
extensión que no arranca. Esto lo mira antes de dar el paquete por bueno.

Uso: python3 scripts/verificar_vsix.py RUTA.vsix [--esperar RUTA ...]
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

# Lo que `ide/PRUEBA-MANUAL.md` promete que viaja en el paquete.
ESPERADOS = ("extension/extension.js", "extension/package.json",
             "extension/readme.md")
MANIFIESTO = ("[Content_Types].xml", "extension.vsixmanifest")
# `vsce` renombra LICENSE a LICENSE.txt: basta con que empiece así.
LICENCIA = "extension/LICENSE"


def revisar(ruta: Path, esperados: tuple[str, ...] = ESPERADOS) -> list[str]:
    """Problemas encontrados; lista vacía si el paquete está bien."""
    if not ruta.is_file():
        return [f"no existe {ruta}"]
    try:
        with zipfile.ZipFile(ruta) as paquete:
            entradas = {nombre: paquete.getinfo(nombre)
                        for nombre in paquete.namelist()}
    except zipfile.BadZipFile:
        return [f"{ruta.name} no es un .vsix válido"]

    problemas: list[str] = []
    for nombre in MANIFIESTO + esperados:
        if nombre not in entradas:
            problemas.append(f"falta {nombre}")
        elif entradas[nombre].file_size == 0:
            problemas.append(f"{nombre} está vacío")
    permitidos = set(esperados) | set(MANIFIESTO)
    for nombre in sorted(entradas):
        if nombre in permitidos or nombre.startswith(LICENCIA):
            continue
        if nombre.endswith(".vsix") or "vscodeignore" in nombre:
            problemas.append(f"sobra {nombre} (no debería viajar)")
        elif nombre.startswith("extension/"):
            problemas.append(f"sobra {nombre}")
    return problemas


def main(argv: list[str]) -> int:
    pendientes = list(argv)
    esperados = list(ESPERADOS)
    rutas: list[str] = []
    while pendientes:
        argumento = pendientes.pop(0)
        if argumento == "--esperar":
            if not pendientes:
                print("⛔ --esperar necesita una ruta", file=sys.stderr)
                return 2
            esperados.append(pendientes.pop(0))
        elif argumento.startswith("-"):
            print(f"⛔ opción desconocida: {argumento}", file=sys.stderr)
            return 2
        else:
            rutas.append(argumento)
    if len(rutas) != 1:
        print("uso: verificar_vsix.py RUTA.vsix [--esperar RUTA ...]",
              file=sys.stderr)
        return 2

    ruta = Path(rutas[0])
    problemas = revisar(ruta, tuple(esperados))
    if problemas:
        for problema in problemas:
            print(f"⛔ {problema}")
        return 1
    with zipfile.ZipFile(ruta) as paquete:
        total = len(paquete.namelist())
    print(f"✓ .vsix verificado: {total} entradas, {ruta.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
