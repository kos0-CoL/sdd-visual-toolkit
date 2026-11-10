"""RF-25 — Cobertura de tests (§18.4: "Cobertura, cuando esté disponible").

Mide qué líneas ejecutables de los archivos fuente de la tarea ejecutan
sus tests, con `sys.settrace` de la biblioteca estándar (sin
dependencias). Capa INFORMATIVA: nunca frena el ciclo; si queda por
debajo del umbral avisa pero no bloquea.

Medición honesta: líneas ejecutables = primeras líneas de sentencias
AST (best-effort documentado, no branch coverage).
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

UMBRAL = 70  # % mínimo orientativo; por debajo avisa, no bloquea


def ejecutables(fuente: str) -> set[int]:
    """Primeras líneas de cada sentencia (incluye docstrings)."""
    try:
        arbol = ast.parse(fuente)
    except SyntaxError:
        return set()
    return {n.lineno for n in ast.walk(arbol) if isinstance(n, ast.stmt)}


def _a_dotted(rel: str) -> str:
    return rel[:-3].replace("/", ".") if rel.endswith(".py") else rel


def medir(raiz, tarea, timeout: int = 180) -> dict:
    """Capa de cobertura: {fase, total, pasadas, fallidas, omitidas,
    ok, errores}. total=líneas ejecutables, pasadas=ejecutadas."""
    base = {"fase": "cobertura", "total": 0, "pasadas": 0, "fallidas": 0,
            "omitidas": 0, "duracion_s": 0.0, "ok": True, "errores": ""}
    raiz = Path(raiz)
    fuentes = [a for a in tarea.archivos
               if not a.startswith("tests/") and a.endswith(".py")
               and (raiz / a).is_file()]
    tests = [a for a in tarea.archivos
             if a.startswith("tests/") and a.endswith(".py")
             and (raiz / a).is_file()]
    if not fuentes:
        base["errores"] = "sin fuentes en la tarea (no se inventa medida)"
        return base
    if not tests:
        base["errores"] = ("sin tests en la tarea: cobertura 0% "
                           "(no se inventa resultado)")
        return base
    lineas: dict[str, set[int]] = {}
    for rel in fuentes:
        try:
            lineas[rel] = ejecutables((raiz / rel).read_text(
                encoding="utf-8", errors="replace"))
        except OSError:
            lineas[rel] = set()
    args = {"root": str(raiz), "targets": fuentes,
            "tests": [_a_dotted(t) for t in tests]}
    with tempfile.NamedTemporaryFile("w", suffix=".json",
                                     delete=False) as fh:
        json.dump(args, fh)
        args_path = fh.name
    try:
        proc = subprocess.run(
            [sys.executable,
             str(Path(__file__).resolve().parent / "_cov_runner.py"),
             str(raiz), args_path],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {**base, "errores": "cobertura: TIMEOUT (%ds)" % timeout}
    finally:
        Path(args_path).unlink(missing_ok=True)
    try:
        salida = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {**base, "errores": "cobertura: sin salida del runner"}
    if "error" in salida:
        return {**base, "errores": "cobertura: %s" % salida["error"]}
    tocadas = {r: set(v) for r, v in salida.get("tocadas", {}).items()}
    total = sum(len(v) for v in lineas.values())
    hechas = sum(len(lineas[r] & tocadas.get(r, set())) for r in lineas)
    pct = round(100.0 * hechas / total) if total else 0
    partes = []
    for r in sorted(lineas):
        if lineas[r]:
            p = round(100.0 * len(lineas[r] & tocadas.get(r, set()))
                      / len(lineas[r]))
            partes.append("%s %d%%" % (r, p))
        else:
            partes.append("%s —" % r)
    detalle = "; ".join(partes)
    estado = "✅" if pct >= UMBRAL else "⚠️ por debajo del umbral %d%%" % UMBRAL
    base.update({"total": total, "pasadas": hechas,
                 "errores": "Cobertura %s: %d%% de %d líneas (%s) %s"
                            % (tarea.id, pct, total, detalle, estado)})
    return base
