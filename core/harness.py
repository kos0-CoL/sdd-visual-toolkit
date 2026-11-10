"""RF-19 — Testing Harness (§18).

El ciclo unitarios → integración → regresión → aceptación → estructural
corre en el momento apropiado (antes de cerrar), no al final del proyecto.
Resultados visibles §18.4, comparación con corridas anteriores y registro
de evidencia. El arnés nunca modifica los tests (§18.3): solo los ejecuta.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path


class HarnessError(ValueError):
    """Condición de aceptación violada en el arnés."""


def hashes_tests(raiz, archivos: list[str]) -> dict[str, str]:
    hashes = {}
    for rel in archivos:
        ruta = Path(raiz) / rel
        if rel.startswith("tests/") and ruta.is_file():
            hashes[rel] = hashlib.sha256(ruta.read_bytes()).hexdigest()[:16]
    return hashes


def _parsear(salida: str) -> dict:
    total = pasadas = fallidas = omitidas = 0
    duracion = 0.0
    m = re.search(r"Ran (\d+) tests? in ([\d.]+)s", salida)
    if m:
        total, duracion = int(m.group(1)), float(m.group(2))
    m = re.search(r"FAILED \((.*?)\)", salida)
    if m:
        detalle = m.group(1)
        f = re.search(r"failures=(\d+)", detalle)
        e = re.search(r"errors=(\d+)", detalle)
        fallidas = (int(f.group(1)) if f else 0) + (int(e.group(1)) if e else 0)
    m = re.search(r"skipped=(\d+)", salida)
    if m:
        omitidas = int(m.group(1))
    pasadas = max(0, total - fallidas - omitidas)
    return {"total": total, "pasadas": pasadas, "fallidas": fallidas,
            "omitidas": omitidas, "duracion_s": round(duracion, 3)}


def _hay(binario: str) -> bool:
    import shutil  # noqa: PLC0415 (solo stdlib, perezoso como el resto)
    return shutil.which(binario) is not None


def detectar_runner(raiz) -> str:
    """Respeta la convención del repo (§51, RF-43): el repo manda.

    package.json con scripts.test (+node/npm) → npm; go.mod (+go) → go;
    Cargo.toml (+cargo) → cargo; si no, pytest solo si el repo lo usa
    y está instalado; si no, unittest de la biblioteca estándar.
    Nunca impone un runner ajeno al repo.
    """
    raiz = Path(raiz)
    pkg = raiz / "package.json"
    if pkg.is_file() and ("test" in pkg.read_text(
            encoding="utf-8", errors="replace")) and (
            _hay("npm") or _hay("node")):
        return "npm"
    if (raiz / "go.mod").is_file() and _hay("go"):
        return "go"
    if (raiz / "Cargo.toml").is_file() and _hay("cargo"):
        return "cargo"
    usa_pytest = ((raiz / "pytest.ini").exists()
                  or (raiz / "pyproject.toml").exists() and "pytest" in
                  (raiz / "pyproject.toml").read_text(encoding="utf-8",
                                                       errors="replace"))
    if usa_pytest:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True, timeout=30)
            if proc.returncode == 0:
                return "pytest"
        except (OSError, subprocess.TimeoutExpired):
            pass
    return "unittest"


def correr(raiz, etiqueta: str, objetivos: list[str],
           timeout: int = 180) -> dict:
    """Ejecuta los objetivos de una fase en UNA sola invocación (§18).

    Antes se abría un proceso por archivo; con muchos tests eso dominaba
    el tiempo total. El runner propio del repo sigue mandando (§51) y el
    marcador FALLA se conserva para que el rojo no se oculte.
    """
    inicio = time.monotonic()
    runner = detectar_runner(raiz)
    if runner in ("npm", "go", "cargo"):
        # §51: el runner del repo es dueño de la selección; una sola
        # corrida del suite, sin partir por archivo.
        return _correr_suite(raiz, etiqueta, runner, timeout)
    if not objetivos:
        return {"fase": etiqueta, "total": 0, "pasadas": 0, "fallidas": 0,
                "omitidas": 0, "duracion_s": 0.0, "ok": True,
                "errores": "sin archivos para esta fase (no se inventa resultado)"}
    if runner == "pytest":
        r = _invocar(raiz, [sys.executable, "-m", "pytest", "-q"] + objetivos,
                     etiqueta, True, timeout)
    else:
        r = _invocar(raiz, [sys.executable, "-m", "unittest"] +
                     [_a_dotted(o) for o in objetivos], etiqueta, False, timeout)
    r["fase"] = etiqueta
    r["runner"] = runner
    if r.get("ok"):
        r["errores"] = r.get("errores") or "—"
    else:
        r["errores"] = "FALLA (%d objetivo(s)): %s" % (
            len(objetivos), r.get("errores") or "sin salida")
    r["duracion_s"] = round(time.monotonic() - inicio, 3)
    return r


def _parsear_pytest(salida: str) -> dict:
    """1 failed, 2 passed, 1 skipped in 0.34s."""
    total = pasadas = fallidas = omitidas = 0
    duracion = 0.0
    m = re.search(r"in ([\d.]+)s", salida)
    if m:
        duracion = float(m.group(1))
    for cantidad, nombre in re.findall(r"(\d+) (passed|failed|error|skipped)", salida):
        if nombre == "passed":
            pasadas += int(cantidad)
        elif nombre == "skipped":
            omitidas += int(cantidad)
        else:
            fallidas += int(cantidad)
    total = pasadas + fallidas + omitidas
    return {"total": total, "pasadas": pasadas, "fallidas": fallidas,
            "omitidas": omitidas, "duracion_s": round(duracion, 3)}


def _a_dotted(rel: str) -> str:
    return rel[:-3].replace("/", ".") if rel.endswith(".py") else rel


def _invocar(raiz, comando, fase, es_pytest: bool, timeout=180) -> dict:
    """Una sola invocación del runner; parsea el agregado."""
    try:
        proc = subprocess.run(
            comando, cwd=str(raiz), capture_output=True, text=True,
            timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"total": 0, "pasadas": 0, "fallidas": 1,
                "omitidas": 0, "ok": False,
                "errores": f"{fase}: TIMEOUT ({timeout}s)"}
    texto = (proc.stdout.strip() + "\n" + proc.stderr.strip()).strip()
    parte = _parsear_pytest(texto) if es_pytest else _parsear(texto)
    ultima = texto.splitlines()
    errores = ("—" if proc.returncode == 0
               else (ultima[-1] if ultima else "sin salida"))
    parte.update({"ok": proc.returncode == 0, "errores": errores})
    return parte


def _parsear_npm(salida: str) -> dict:
    """jest (Tests: N passed), vitest (Tests N passed), mocha
    (N passing / N failing / N pending). Sin coincidencias no se
    inventan conteos: el veredicto lo da el código de salida."""
    pasadas = fallidas = omitidas = 0
    for cantidad in re.findall(r"Tests:\s*(\d+) passed", salida):
        pasadas = max(pasadas, int(cantidad))
    for cantidad in re.findall(r"Tests\s+(\d+) passed", salida):
        pasadas = max(pasadas, int(cantidad))
    for cantidad in re.findall(r"(\d+) passing", salida):
        pasadas = max(pasadas, int(cantidad))
    for cantidad in re.findall(r"(\d+) failing", salida):
        fallidas += int(cantidad)
    for cantidad in re.findall(r"(\d+) failed", salida):
        fallidas += int(cantidad)
    for cantidad in re.findall(r"(\d+) (?:pending|skipped)", salida):
        omitidas += int(cantidad)
    return {"total": pasadas + fallidas + omitidas, "pasadas": pasadas,
            "fallidas": fallidas, "omitidas": omitidas,
            "duracion_s": 0.0}


def _parsear_go(salida: str) -> dict:
    """Cuenta --- PASS: / --- FAIL: de `go test ./...`."""
    pasadas = len(re.findall(r"^--- PASS:", salida, re.MULTILINE))
    fallidas = len(re.findall(r"^--- FAIL:", salida, re.MULTILINE))
    return {"total": pasadas + fallidas, "pasadas": pasadas,
            "fallidas": fallidas, "omitidas": 0, "duracion_s": 0.0}


def _parsear_cargo(salida: str) -> dict:
    """Suma los `test result: ok. N passed; M failed` de cargo."""
    pasadas = sum(int(n) for n in re.findall(r"(\d+) passed", salida))
    fallidas = sum(int(n) for n in re.findall(r"(\d+) failed", salida))
    omitidas = sum(int(n) for n in re.findall(r"(\d+) ignored", salida))
    return {"total": pasadas + fallidas + omitidas, "pasadas": pasadas,
            "fallidas": fallidas, "omitidas": omitidas,
            "duracion_s": 0.0}


_COMANDOS_SUITE = {
    "npm": (["npm", "test"], _parsear_npm),
    "go": (["go", "test", "./..."], _parsear_go),
    "cargo": (["cargo", "test"], _parsear_cargo),
}


def _correr_suite(raiz, etiqueta: str, runner: str, timeout: int = 180) -> dict:
    """Una corrida del suite con el runner propio del repo (§51)."""
    inicio = time.monotonic()
    comando, parsear = _COMANDOS_SUITE[runner]
    try:
        proc = subprocess.run(
            comando, cwd=str(raiz), capture_output=True, text=True,
            timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"fase": etiqueta, "total": 0, "pasadas": 0, "fallidas": 1,
                "omitidas": 0, "duracion_s": round(time.monotonic() - inicio, 3),
                "ok": False, "errores": f"suite {runner}: TIMEOUT ({timeout}s)",
                "runner": runner}
    except OSError as error:
        return {"fase": etiqueta, "total": 0, "pasadas": 0, "fallidas": 0,
                "omitidas": 0, "duracion_s": round(time.monotonic() - inicio, 3),
                "ok": False, "errores": f"suite {runner}: no ejecutable ({error})",
                "runner": runner}
    texto = (proc.stdout.strip() + "\n" + proc.stderr.strip()).strip()
    parte = parsear(texto)
    parte["duracion_s"] = round(time.monotonic() - inicio, 3)
    if proc.returncode == 0 and parte["fallidas"] == 0:
        errores = "suite %s verde" % runner if parte["total"] else \
            "suite %s verde (conteo no parseable, ver salida)" % runner
        return {"fase": etiqueta, **parte, "ok": True,
                "errores": "—" if parte["total"] else errores,
                "runner": runner}
    ultima = texto.splitlines()
    cola = ultima[-1] if ultima else "sin salida"
    if parte["total"] == 0:
        # Rojo sin conteo parseable: se declara, no se fabrica.
        return {"fase": etiqueta, **parte, "ok": False,
                "errores": "suite %s ROJA: %s" % (runner, cola),
                "runner": runner}
    return {"fase": etiqueta, **parte, "ok": False,
            "errores": "suite %s: %s" % (runner, cola),
            "runner": runner}


def _correr_unittest(raiz, archivos: list[str], timeout: int = 180) -> dict:
    dotted = [_a_dotted(a) for a in archivos]
    return _invocar(raiz, [sys.executable, "-m", "unittest"] + dotted,
                    "regresión", False, timeout)


def _correr_pytest(raiz, archivos: list[str], timeout: int = 180) -> dict:
    return _invocar(raiz, [sys.executable, "-m", "pytest", "-q"] + archivos,
                    "regresión", True, timeout)


def correr_archivos(raiz, archivos: list[str], fase: str = "unitarios",
                    timeout: int = 180) -> dict:
    """RF-19/RF-43: ejecuta los tests de una tarea con el runner detectado.

    pytest/unittest para Python; una corrida de suite completa para
    npm/go/cargo (§51: el repo manda). Sin archivos: resultado honesto
    (no se inventa resultado)."""
    runner = detectar_runner(raiz)
    if runner in ("npm", "go", "cargo"):
        return _correr_suite(raiz, fase, runner, timeout)
    if not archivos:
        return {"fase": fase, "total": 0, "pasadas": 0, "fallidas": 0,
                "omitidas": 0, "duracion_s": 0.0, "ok": True,
                "errores": "sin archivos para esta fase (no se inventa resultado)"}
    if runner == "pytest":
        r = _invocar(raiz, [sys.executable, "-m", "pytest", "-q"] + archivos,
                    fase, True, timeout)
    else:
        r = _invocar(raiz, [sys.executable, "-m", "unittest"] +
                    [_a_dotted(a) for a in archivos], fase, False, timeout)
    r["fase"] = fase
    return r


FASES = ("unitarios", "integración", "regresión", "cobertura",
         "aceptación", "estructural")


def ejecutar_ciclo(raiz, tarea, spec=None,
                   solo: tuple[str, ...] | None = None) -> dict:
    """Ciclo §18.2. Devuelve el consolidado con las 5 capas (o un
    subconjunto con `solo`, para corridas dirigidas)."""
    if solo is not None:
        desconocidas = set(solo) - set(FASES)
        if desconocidas:
            raise HarnessError(f"fase(s) inválida(s): {sorted(desconocidas)}")
        elegidas = set(solo)
    else:
        elegidas = set(FASES)
    tests_tarea = sorted(a for a in tarea.archivos
                         if a.startswith("tests/") and a.endswith(".py")
                         and (Path(raiz) / a).is_file())
    unitarios = [a for a in tests_tarea if "integration" not in a.lower()]
    integracion = [a for a in tests_tarea if "integration" in a.lower()]
    # RF-22: tests generales = flujos completos §53.1, por convención de
    # nombre (*general*, *system*, *e2e*, *flujo*). Corren en la capa
    # unitarios y se rebarren en la regresión.
    generales = [a for a in tests_tarea if _es_general(a)]
    capas = []
    if "unitarios" in elegidas:
        capas.append(correr(raiz, "unitarios", unitarios))
    if "integración" in elegidas:
        capas.append(capa_integracion(raiz, tarea, integracion))
    if "regresión" in elegidas:
        capas.append(capa_regresion(raiz, tarea,
                                    unitarios + integracion, generales))
    if "cobertura" in elegidas:
        capas.append(capa_cobertura(raiz, tarea))
    if "aceptación" in elegidas:
        capas.append(capa_aceptacion(raiz, tarea, spec))
    if "estructural" in elegidas:
        capas.append(capa_estructural(tarea, raiz))
    ejecutadas = [c for c in capas if c["total"] > 0 or not c["ok"]]
    # RF-23/RF-24: aceptación y estructural son ejecutables; su rojo
    # frena el ciclo. (Estructural: solo RECHAZADO bloquea; la
    # ADVERTENCIA pide --nota pero no frena.)
    ok = all(c["ok"] for c in capas)
    return {"tarea": tarea.id, "capas": capas, "ok": ok,
            "hashes_tests": hashes_tests(raiz, tarea.archivos),
            "resumen": render(capas, tarea.id, ok)}


PATRONES_GENERAL = ("general", "system", "e2e", "flujo")


def _es_general(rel: str) -> bool:
    nombre = rel.rsplit("/", 1)[-1].lower()
    return any(p in nombre for p in PATRONES_GENERAL)


def capa_integracion(raiz, tarea, archivos: list[str]) -> dict:
    """RF-21: verificación estática entre módulos + tests *integration*."""
    from core.integration import verificar  # noqa: PLC0415

    estatica = verificar(raiz, tarea)
    dinamica = correr(raiz, "integración", archivos)
    total = len(estatica["hallazgos"]) + dinamica["total"]
    fallidas = (len(estatica["hallazgos"]) + dinamica["fallidas"])
    errores = []
    for h in estatica["hallazgos"]:
        errores.append(f"{h['archivo']}: {h['detalle']}")
    if not errores:
        errores.append(estatica["resumen"])
    if dinamica["errores"] not in ("—",) and dinamica["total"] > 0:
        errores.append(dinamica["errores"])
    return {"fase": "integración", "total": total,
            "pasadas": max(0, total - fallidas), "fallidas": fallidas,
            "omitidas": dinamica["omitidas"],
            "duracion_s": dinamica["duracion_s"],
            "ok": estatica["ok"] and dinamica["ok"],
            "errores": "; ".join(errores) or estatica["resumen"]}


def correr_conjunto(raiz: Path, fase: str, archivos: list[str]) -> dict:
    """Ejecuta una lista de archivos de test en UNA sola invocación.

    Barrido conjunto (no por archivo) para que emerjan interferencias
    entre módulos. Si no hay archivos, no se inventa resultado.
    """
    runner = detectar_runner(raiz)
    inicio = time.monotonic()
    if not archivos and runner not in _COMANDOS_SUITE:
        return {"fase": fase, "total": 0, "pasadas": 0, "fallidas": 0,
                "omitidas": 0, "duracion_s": 0.0, "ok": True,
                "errores": "sin archivos para esta fase "
                           "(no se inventa resultado)"}
    if runner == "pytest":
        r = _correr_pytest(raiz, archivos)
    elif runner in _COMANDOS_SUITE:
        r = _correr_suite(raiz, fase, runner)
        dur = round(time.monotonic() - inicio, 1)
        return {"fase": fase, "total": r["total"],
                "pasadas": r["pasadas"], "fallidas": r["fallidas"],
                "omitidas": r["omitidas"], "duracion_s": dur,
                "ok": r["ok"], "errores": r["errores"]}
    else:
        r = _correr_unittest(raiz, archivos)
    dur = round(time.monotonic() - inicio, 1)
    return {"fase": fase, "total": r["total"],
            "pasadas": r["pasadas"], "fallidas": r["fallidas"],
            "omitidas": r["omitidas"], "duracion_s": dur,
            "ok": r["ok"], "errores": r["errores"]}


def capa_regresion(raiz, tarea, archivos: list[str],
                    generales: list[str] | None = None) -> dict:
    """RF-22: barrido de regresión — todo el suite junto.

    §53.2: verifica que nada de lo ya verificado se rompió.
    Exige 0 rojos en el conjunto completo.
    """
    r = correr_conjunto(raiz, "regresión", archivos)
    if r["total"] == 0:
        return r
    if r["ok"]:
        extra = (f" ({len(generales)} de flujo completo)"
                 if generales else "")
        r["errores"] = (f"Regresión {tarea.id}: {r['total']} pruebas "
                         f"re-ejecutadas{extra}, 0 rojos.")
    return r


def capa_aceptacion(raiz, tarea, spec) -> dict:
    """RF-23: casos Given-When-Then ejecutables (delegado)."""
    from core.acceptance import evaluar  # noqa: PLC0415
    return evaluar(raiz, tarea, spec)


def capa_cobertura(raiz, tarea) -> dict:
    """RF-25: medición de cobertura (informativa, no bloquea)."""
    from core.coverage import medir  # noqa: PLC0415
    return medir(raiz, tarea)


def capa_estructural(tarea, raiz) -> dict:
    from core.astcheck import _resumen, comparar  # noqa: PLC0415
    from core.pin import _cargar_pin, asegurar_baseline  # noqa: PLC0415
    from core.structure import verificar  # noqa: PLC0415

    previo = _cargar_pin(raiz, tarea.id)
    baseline = previo.get("baseline", {}) if previo else {}
    if not baseline:
        baseline, _ = asegurar_baseline(raiz, tarea)
    r = comparar(tarea, baseline, raiz)
    # RF-24: dependencias (ciclos), contratos rotos e interfaces sin
    # evidencia se suman con la misma forma de hallazgo.
    r["hallazgos"].extend(verificar(raiz, tarea, baseline)["hallazgos"])
    if any(h["severidad"] == "rechazado" for h in r["hallazgos"]):
        r["veredicto"] = "RECHAZADO"
    elif r["hallazgos"]:
        r["veredicto"] = "ADVERTENCIA"
    else:
        r["veredicto"] = "ACEPTADO"
    r["resumen"] = _resumen(tarea, r["hallazgos"], r["veredicto"])
    rojos = sum(1 for h in r["hallazgos"] if h["severidad"] == "rechazado")
    return {"fase": "estructural", "total": len(r["hallazgos"]),
            "pasadas": len(r["hallazgos"]) - rojos, "fallidas": rojos,
            "omitidas": 0, "duracion_s": 0.0,
            "ok": r["veredicto"] != "RECHAZADO",
            "errores": r["veredicto"] + (": " + r["resumen"].splitlines()[0]
                                         if r["hallazgos"] else "")}


def render(capas: list[dict], task_id: str, ok: bool) -> str:
    lineas = [f"🧪 Ciclo de testing {task_id}: "
              f"{'✅ TODO VERDE' if ok else '❌ HAY ROJO'}."]
    for c in capas:
        marca = "✅" if c["ok"] and (c["total"] or c["fase"] in
                                     ("aceptación", "estructural")) else \
                ("⚪" if c["ok"] else "❌")
        lineas.append(
            f"{marca} {c['fase']}: total={c['total']} "
            f"pasadas={c['pasadas']} fallidas={c['fallidas']} "
            f"omitidas={c['omitidas']} ({c['duracion_s']}s)")
        if c["errores"] != "—":
            lineas.append(f"   {c['errores']}")
    # RF-26: totales visibles §18.4 (duración agregada + cobertura).
    lineas.append(f"⏱ duración total: {round(sum(c['duracion_s'] for c in capas), 1)}s")
    cob = next((c for c in capas if c["fase"] == "cobertura"), None)
    if cob is not None and cob["total"]:
        pct = round(100.0 * cob["pasadas"] / cob["total"])
        lineas.append(f"📊 cobertura: {pct}% de {cob['total']} líneas")
    return "\n".join(lineas)
