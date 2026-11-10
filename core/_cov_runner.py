"""Ejecutor con trazado de líneas para RF-25 (uso interno).

Se invoca en un subproceso: `python _cov_runner.py <root> <args.json>`.
Instala sys.settrace restringido a los archivos objetivo, corre los
tests con unittest y vuelca a stdout el JSON {rel: [lineas]}.
"""

import io
import json
import os
import sys
import unittest


def main() -> int:
    root, args_path = sys.argv[1], sys.argv[2]
    with open(args_path, encoding="utf-8") as fh:
        args = json.load(fh)
    os.chdir(root)  # como el arnés: los tests usan rutas relativas
    sys.path.insert(0, root)
    objetivos = {args["root"] + "/" + rel: rel for rel in args["targets"]}
    tocadas: dict[str, set] = {rel: set() for rel in args["targets"]}

    def traza(frame, evento, _arg):
        if evento == "line":
            rel = objetivos.get(frame.f_code.co_filename)
            if rel is not None:
                tocadas[rel].add(frame.f_lineno)
        return traza

    sys.settrace(traza)
    try:
        suite = unittest.TestSuite()
        cargador = unittest.TestLoader()
        for dotted in args["tests"]:
            try:
                suite.addTests(cargador.loadTestsFromName(dotted))
            except Exception as exc:  # noqa: BLE001
                print(json.dumps({"error": "%s: %s" % (dotted, exc)}))
                return 2
        unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    finally:
        sys.settrace(None)
    print(json.dumps({"tocadas": {r: sorted(v)
                                  for r, v in tocadas.items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
