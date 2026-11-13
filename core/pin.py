"""RF-10 — Spec Pinning (§11.1, §12).

Restricciones presentes antes de cada escritura + detección de
desviaciones clasificadas A (requerido), B (técnico, justificar) o
C (ajeno, excluir y sugerir). Criterio: trazabilidad, no prohibición
indiscriminada.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from core.analyze import _es_protegido
from state import store


class PinError(ValueError):
    """Condición de aceptación violada en el pinning."""


@dataclass
class Desviacion:
    clase: str  # A | B | C
    archivo: str
    detalle: str

    def to_dict(self) -> dict:
        return {"clase": self.clase, "archivo": self.archivo, "detalle": self.detalle}

    @classmethod
    def from_dict(cls, datos: dict) -> "Desviacion":
        return cls(clase=str(datos["clase"]), archivo=str(datos["archivo"]),
                   detalle=str(datos["detalle"]))


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _simbolos(fuente: str) -> tuple[dict, dict, dict, dict, dict]:
    """(públicas {nombre: firma}, todas, imports, globales, retornos).

    Import, global y retorno se capturan para el chequeo estructural
    (§17); lo interno (`_x`) se registra pero no genera ruido."""
    publicas, todas, imports, globales, retornos = {}, {}, {}, {}, {}
    try:
        arbol = ast.parse(fuente)
    except SyntaxError:
        return publicas, todas, imports, globales, retornos
    for nodo in arbol.body:
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                imports[alias.name.split(".")[0]] = f"import {alias.name}"
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            for alias in nodo.names:
                imports[alias.name] = f"from {modulo} import {alias.name}"
        elif isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            todas[nodo.name] = True
            if not nodo.name.startswith("_"):
                if isinstance(nodo, ast.ClassDef):
                    publicas[nodo.name] = " (clase)"
                else:
                    args = [a.arg for a in nodo.args.args]
                    publicas[nodo.name] = f"({', '.join(args)})"
                    if nodo.returns is not None:
                        try:
                            retornos[nodo.name] = ast.unparse(nodo.returns)
                        except (ValueError, SyntaxError):
                            retornos[nodo.name] = "?"
        elif isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            for obj in objetivos:
                if isinstance(obj, ast.Name) and not obj.id.startswith("_"):
                    globales[obj.id] = True
    return publicas, todas, imports, globales, retornos


def _cuerpos(fuente: str) -> dict[str, str]:
    """{nombre_publico: hash_del_cuerpo_ast} para funciones y clases públicas.

    El cuerpo es el nodo AST sin la firma (decorators, nombre, args, returns).
    Permite detectar cambios de comportamiento interno que preservan la firma.
    """
    cuerpos: dict[str, str] = {}
    try:
        arbol = ast.parse(fuente)
    except SyntaxError:
        return cuerpos
    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if nodo.name.startswith("_"):
                continue
            cuerpo = ast.dump(nodo, include_attributes=False)
            cuerpos[nodo.name] = hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()[:16]
    return cuerpos


def snapshot_archivo(ruta: Path) -> dict | None:
    if not ruta.is_file() or ruta.suffix != ".py":
        return None
    try:
        fuente = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    publicas, _todas, imports, globales, retornos = _simbolos(fuente)
    cuerpos = _cuerpos(fuente)
    return {"sha": _sha256(ruta), "publicas": publicas,
            "imports": imports, "globales": globales, "retornos": retornos,
            "cuerpos": cuerpos}


def tomar_baseline(tarea, raiz: Path) -> dict:
    """Foto de los archivos autorizados al iniciar la tarea."""
    base = {}
    for rel in tarea.archivos:
        snap = snapshot_archivo(Path(raiz) / rel)
        if snap is not None:
            base[rel] = snap
    return base


def verificar_cambios(tarea, baseline: dict, raiz: Path) -> list[Desviacion]:
    """Compara el árbol contra la línea base. Sin baseline no hay
    evidencia: no se inventa ninguna desviación."""
    desviaciones: list[Desviacion] = []
    autorizados = set(tarea.archivos)

    for rel in sorted(autorizados):
        ruta = Path(raiz) / rel
        if not ruta.is_file():
            continue  # lo verifica build --done (archivos objetivo)
        anterior = baseline.get(rel)
        actual = snapshot_archivo(ruta)
        if actual is None:
            continue  # no-Python: sin símbolos comparables
        es_prueba = rel.startswith("tests/")  # la evidencia misma no es B
        if anterior is None:
            if not es_prueba:
                for nombre, firma in actual.get("publicas", {}).items():
                    desviaciones.append(Desviacion(
                        "B", rel,
                        f"símbolo público nuevo «{nombre}{firma}» en archivo "
                        "creado por la tarea: justifique por qué es "
                        "indispensable (§12.B)"))
            continue
        if actual["sha"] == anterior["sha"]:
            continue
        viejas = anterior.get("publicas", {})
        nuevas = actual.get("publicas", {})
        for nombre, firma in nuevas.items():
            if nombre not in viejas:
                if nombre.startswith("_"):
                    continue  # símbolo interno: ni siquiera es B
                if es_prueba:
                    continue  # evidencia nueva, no desviación técnica
                desviaciones.append(Desviacion(
                    "B", rel,
                    f"nueva función/clase pública «{nombre}{firma}»: "
                    "documente por qué es indispensable (§12.B)"))
            elif viejas[nombre] != firma:
                desviaciones.append(Desviacion(
                    "B", rel,
                    f"firma cambiada en «{nombre}»: {viejas[nombre]} → {firma}; "
                    "verifique compatibilidad con llamadores (§12.B)"))
        if actual["sha"] != anterior["sha"] and not es_prueba:
            # Si las firmas públicas son iguales, detectar cambio de cuerpo
            # interno (mismo contrato, distinto comportamiento) como B.
            if viejas == nuevas:
                cuerpos_viejos = anterior.get("cuerpos", {})
                cuerpos_nuevos = actual.get("cuerpos", {})
                if cuerpos_viejos != cuerpos_nuevos:
                    if not any(d.archivo == rel for d in desviaciones):
                        desviaciones.append(Desviacion(
                            "B", rel,
                            f"cambio de cuerpo interno en «{rel}» sin cambio de "
                            f"firma pública: verifique comportamiento (§12.B)"))

    # Archivos fuera de los autorizados: se compara la foto amplia de la
    # línea base contra el árbol actual. Incluye archivos NUEVOS (no están
    # en la foto vieja): todo .py no autorizado que aparece o cambia es
    # evidencia directa de cambio ajeno.
    amplia = baseline.get("__arbol__", {})
    actual_arbol = foto_arbol(raiz)
    for rel in sorted(set(amplia) | set(actual_arbol)):
        if rel in autorizados or rel.startswith("tests/"):
            continue
        ruta = Path(raiz) / rel
        if not ruta.is_file():
            continue  # un ajeno eliminado es corrección, no desviación
        sha_vieja = amplia.get(rel, {}).get("sha")
        ahora = snapshot_archivo(ruta)
        if ahora is None or ahora["sha"] == sha_vieja:
            continue
        if _es_protegido(rel):
            desviaciones.append(Desviacion(
                "C", rel,
                "archivo protegido modificado: requiere autorización explícita (§8.4)"))
        else:
            desviaciones.append(Desviacion(
                "C", rel,
                "cambio fuera de los archivos autorizados de la tarea: "
                "excluir de esta implementación y registrar como sugerencia (§12.C)"))
    return desviaciones


def foto_arbol(raiz: Path, limite: int = 500) -> dict:
    """Foto amplia de .py del proyecto para detectar cambios ajenos."""
    foto = {}
    n = 0
    for ruta in sorted(Path(raiz).rglob("*.py")):
        if n >= limite:
            break
        partes = ruta.relative_to(raiz).parts
        if partes[0].startswith(".") or "__pycache__" in partes:
            continue
        rel = str(ruta.relative_to(raiz))
        snap = snapshot_archivo(ruta)
        if snap is not None:
            foto[rel] = {"sha": snap["sha"]}
            n += 1
    return foto


def generar_pin(plan, spec, tarea, decisiones: list) -> str:
    reqs = [f"{i}: {t}" for i, t, _e in spec.funcionales if i in tarea.refs]
    protegidas = [a for a in tarea.archivos if _es_protegido(a)]
    return "\n".join([
        f"📌 PIN {tarea.id} — SPEC {spec.spec_id} [{spec.status}] / {plan.plan_id}",
        f"SPEC activa: {spec.titulo} (origen {spec.enr_origen or '—'})",
        f"Requerimiento: {'; '.join(reqs) or '(sección ' + ', '.join(tarea.refs) + ')'}",
        f"Tarea activa: {tarea.objetivo}",
        f"Criterios de aceptación: {tarea.criterio}",
        f"Archivos autorizados: {', '.join(tarea.archivos)}",
        f"Exclusiones: {'; '.join(spec.fuera_alcance) or '—'}",
        f"Interfaces protegidas: {', '.join(protegidas) or 'ninguna en esta tarea'}",
        f"Decisiones aprobadas: {'; '.join(decisiones) or 'ninguna registrada en clarify'}",
    ])


PINES_DIR = "pines"


def _ruta_pin(raiz, task_id: str):
    from pathlib import Path  # noqa: PLC0415
    return Path(raiz) / store.SPECIFY_DIR / PINES_DIR / f"{task_id}.json"


def _guardar_pin(raiz, task_id: str, datos: dict) -> None:
    ruta = _ruta_pin(raiz, task_id)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    store.escribir_json(ruta, datos)


def _cargar_pin(raiz, task_id: str) -> dict | None:
    ruta = _ruta_pin(raiz, task_id)
    if not ruta.exists():
        return None
    return store.leer_json(ruta)


def asegurar_baseline(raiz, tarea) -> tuple[dict, bool]:
    """Devuelve (baseline, es_parcial). Sin foto previa no se inventa
    evidencia: se registra la actual y el check es parcial."""
    previo = _cargar_pin(raiz, tarea.id)
    if previo is not None:
        return previo.get("baseline", {}), False
    baseline = tomar_baseline(tarea, raiz)
    baseline["__arbol__"] = foto_arbol(raiz)
    _guardar_pin(raiz, tarea.id, {"baseline": baseline, "desviaciones": []})
    return baseline, True


def chequear(raiz, tarea) -> tuple[list[Desviacion], bool]:
    baseline, parcial = asegurar_baseline(raiz, tarea)
    desvs = verificar_cambios(tarea, baseline, raiz)
    previo = _cargar_pin(raiz, tarea.id) or {}
    previo["desviaciones"] = [d.to_dict() for d in desvs]
    _guardar_pin(raiz, tarea.id, previo if "baseline" in previo
                 else {"baseline": baseline, "desviaciones": previo.get("desviaciones", [])})
    return desvs, parcial


def decisiones_aprobadas(historial: list) -> list[str]:
    return [f"{h['pregunta']} → {h['respuesta']}" for h in historial
            if h.get("respuesta")]
