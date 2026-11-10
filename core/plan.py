"""RF-05 — Plan de implementación (§8).

Investiga el repositorio real (nunca inventa arquitectura) y deriva el plan
técnico solo de la SPEC + lo hallado. Sin clarify superado no hay plan (§26).
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

from core.clarify import raices
from state import store

IGNORAR_DIRS = {
    ".git", "__pycache__", ".specify", ".pytest_cache", "venv", ".venv",
    "node_modules", "specs", ".mypy_cache", "dist", "build", "target",
}

LENGUAJES = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".java": "Java",
    ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C",
}

PATRONES_TEST = ("test_", "_test", "tests", "spec.")


class PlanError(ValueError):
    """Condición de aceptación violada en planificación."""


def _es_test(ruta: Path) -> bool:
    nombre = ruta.name.lower()
    return (
        any(p in nombre for p in PATRONES_TEST) or "tests" in ruta.parts
    )


def _archivos_considerados(raiz: Path) -> list[Path]:
    """Archivos del repo que el análisis mira (mismas exclusiones §8.2)."""
    archivos: list[Path] = []
    for ruta in sorted(raiz.rglob("*")):
        if not ruta.is_file():
            continue
        if any(parte in IGNORAR_DIRS or parte.startswith(".") for parte in ruta.parts[len(raiz.parts):-1]):
            continue
        if ruta.suffix == ".pyc":
            continue
        archivos.append(ruta)
    return archivos


def _mapa_archivos(raiz: Path, archivos: list[Path]) -> dict[str, list[int]]:
    """Huella barata por archivo (tamaño + mtime) para invalidar la caché."""
    mapa: dict[str, list[int]] = {}
    for ruta in archivos:
        try:
            estado = ruta.stat()
        except OSError:
            continue
        mapa[str(ruta.relative_to(raiz))] = [estado.st_size, estado.st_mtime_ns]
    return mapa


def _huella(mapa: dict) -> str:
    import hashlib  # noqa: PLC0415

    datos = json.dumps(mapa, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(datos.encode("utf-8")).hexdigest()[:16]


def _ruta_cache(raiz: Path) -> Path:
    return raiz / store.SPECIFY_DIR / "cache" / "analisis.json"


def _leer_cache(raiz: Path):
    ruta = _ruta_cache(raiz)
    if not ruta.exists():
        return None
    try:
        datos = store.leer_json(ruta)
    except store.StoreError:
        return None  # caché corrupta: se ignora y se recalcula
    if not isinstance(datos, dict) or "huella" not in datos or "hallazgos" not in datos:
        return None
    return datos


def archivos_afectados(raiz_proyecto: Path) -> dict:
    """Archivos cambiados/nuevos/eliminados respecto de la última caché."""
    raiz = Path(raiz_proyecto)
    actual = _mapa_archivos(raiz, _archivos_considerados(raiz))
    previo = _leer_cache(raiz)
    if previo is None:
        return {"hay_cache": False, "cambiados": sorted(actual),
                "eliminados": [], "huella": _huella(actual)}
    antes = previo.get("archivos", {})
    cambiados = sorted(k for k, v in actual.items() if antes.get(k) != v)
    eliminados = sorted(set(antes) - set(actual))
    return {"hay_cache": True, "cambiados": cambiados,
            "eliminados": eliminados, "huella": _huella(actual),
            "huella_previa": previo.get("huella")}


def investigar(raiz_proyecto: Path, usar_cache: bool = True) -> dict:
    """Lee el repositorio real: estructura, lenguajes, dependencias,
    persistencia, pruebas y convenciones (§8.2).

    La caché es opcional y solo se escribe si el proyecto ya tiene `.specify/`:
    un análisis sin cambios se reutiliza; cualquier archivo modificado
    (tamaño o mtime) invalida la huella y se recalcula.
    """
    raiz = Path(raiz_proyecto)
    archivos = _archivos_considerados(raiz)
    mapa = _mapa_archivos(raiz, archivos)
    huella = _huella(mapa)
    if usar_cache:
        cache = _leer_cache(raiz)
        if cache is not None and cache.get("huella") == huella:
            return json.loads(json.dumps(cache["hallazgos"]))

    por_lenguaje: dict[str, int] = {}
    codigo: list[str] = []
    pruebas: list[str] = []
    datos: list[str] = []
    for ruta in archivos:
        rel = str(ruta.relative_to(raiz))
        if ruta.suffix in LENGUAJES:
            por_lenguaje[LENGUAJES[ruta.suffix]] = por_lenguaje.get(LENGUAJES[ruta.suffix], 0) + 1
            (pruebas if _es_test(ruta) else codigo).append(rel)
        elif ruta.suffix in (".db", ".sqlite", ".sqlite3") or (
            ruta.suffix == ".json" and "data" in ruta.parts
        ):
            datos.append(rel)

    dependencias: list[str] = []
    manifiestos = [a for a in archivos if a.name in (
        "pyproject.toml", "requirements.txt", "requirements-dev.txt",
        "package.json", "go.mod", "Cargo.toml", "Gemfile")]
    for man in manifiestos:
        try:
            texto = man.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if man.name == "package.json":
            try:
                pkg = json.loads(texto)
                for seccion in ("dependencies", "devDependencies"):
                    dependencias.extend(sorted(pkg.get(seccion, {})))
            except json.JSONDecodeError:
                pass
        else:
            for linea in texto.splitlines():
                linea = linea.strip()
                if linea and not linea.startswith(("#", "[", ";", "-")) and "=" in linea or (
                    man.name.startswith("requirements") and linea
                    and not linea.startswith(("#", "-"))
                ):
                    nombre = linea.split("=")[0].split(">")[0].split("<")[0].split()[0].strip("\"'")
                    if nombre and len(nombre) < 60:
                        dependencias.append(f"{nombre} ({man.name})")
    dependencias = sorted(set(dependencias))

    imports_externos: set[str] = set()
    modulos_internos: set[str] = set()
    for rel in codigo:
        if not rel.endswith(".py"):
            continue
        try:
            arbol = ast.parse((raiz / rel).read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    imports_externos.add(alias.name.split(".")[0])
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                imports_externos.add(nodo.module.split(".")[0])
    stdlib_muestra = {"os", "sys", "json", "pathlib", "argparse", "unittest",
                      "dataclasses", "ast", "datetime", "re", "typing"}
    modulos_internos = {m for m in imports_externos if (raiz / f"{m}.py").exists() or (raiz / m).is_dir()}
    imports_externos -= modulos_internos | stdlib_muestra

    fuentes = " ".join(
        (raiz / r).read_text(encoding="utf-8", errors="replace")
        for r in codigo if r.endswith(".py")
    ) if codigo else ""
    persistencia = sorted(set(datos) | {
        f"uso de {mod}" for mod in ("sqlite3", "json", "shelve")
        if f"import {mod}" in fuentes or f"{mod}." in fuentes
    }) if codigo else sorted(datos)

    top_dirs = sorted({Path(a).parts[0] for a in archivos
                       if len(Path(a).parts) > 1 and not Path(a).parts[0].startswith(".")})
    convenciones = []
    if (raiz / "README.md").exists() or (raiz / "README.rst").exists():
        convenciones.append("README presente")
    if pruebas:
        convenciones.append(f"suite de pruebas existente ({len(pruebas)} archivo(s))")
    if (raiz / "docs").is_dir():
        convenciones.append("documentación en docs/")

    hallazgos = {
        "es_greenfield": not codigo,
        "lenguajes": por_lenguaje,
        "total_archivos": len(archivos),
        "codigo": sorted(codigo),
        "pruebas": sorted(pruebas),
        "datos": persistencia,
        "dependencias": dependencias,
        "manifiestos": sorted(str(m.relative_to(raiz)) for m in manifiestos),
        "modulos_internos": sorted(modulos_internos),
        "imports_externos": sorted(imports_externos),
        "carpetas": top_dirs,
        "convenciones": convenciones,
    }
    if (raiz / store.SPECIFY_DIR).is_dir():
        try:
            ruta = _ruta_cache(raiz)
            ruta.parent.mkdir(parents=True, exist_ok=True)
            store.escribir_json(ruta, {"huella": huella, "archivos": mapa,
                                       "hallazgos": hallazgos})
        except (store.StoreError, OSError):
            pass  # la caché acelera el análisis, no es un requisito
    return hallazgos


def componentes_relacionados(spec, hallazgos: dict, tope: int = 10) -> list[str]:
    """Solo coincidencia nominal contra el vocabulario de la SPEC (§8.2:
    limitarse a los componentes relacionados)."""
    vocabulario = set()
    for _id, texto, _e in spec.funcionales:
        vocabulario |= raices(texto)
    vocabulario |= {r for e in spec.entidades for r in raices(e)}
    relacionados = [
        r for r in hallazgos["codigo"]
        if raices(r.replace("/", " ").replace("_", " ").replace(".", " ")) & vocabulario
    ]
    return relacionados[:tope]


@dataclass
class Paso:
    id: str
    titulo: str
    refs: list = field(default_factory=list)  # REQ-IDs o secciones SPEC
    detalle: str = ""


@dataclass
class Plan:
    plan_id: str
    spec_id: str
    version: str = "1.0.0"
    status: str = "draft"
    hallazgos: dict = field(default_factory=dict)
    relacionados: list = field(default_factory=list)
    modificables: list = field(default_factory=list)
    intactos: list = field(default_factory=list)
    creables: list = field(default_factory=list)
    reutilizables: list = field(default_factory=list)
    arquitectura: str = ""
    dependencias_plan: list = field(default_factory=list)
    orden: list = field(default_factory=list)  # [Paso]
    integracion: str = ""
    riesgos: list = field(default_factory=list)
    compatibilidad: str = ""
    impacto: str = ""
    pruebas_estrategia: str = ""
    validacion: list = field(default_factory=list)
    alternativas: list = field(default_factory=list)  # sugerencias, no decisiones
    created_at: str = ""
    updated_at: str = ""

    def cobertura_funcional(self, spec) -> list[str]:
        """Funcionales aceptados sin ningún paso que los cite (§8.6)."""
        cubiertos = {r for p in self.orden for r in p.refs}
        return [i for i, _t, e in spec.funcionales
                if e == "aceptado" and i not in cubiertos]

    def to_dict(self) -> dict:
        datos = {
            "plan_id": self.plan_id, "spec_id": self.spec_id,
            "version": self.version, "status": self.status,
            "hallazgos": self.hallazgos, "relacionados": self.relacionados,
            "modificables": self.modificables, "intactos": self.intactos,
            "creables": self.creables, "reutilizables": self.reutilizables,
            "arquitectura": self.arquitectura,
            "dependencias_plan": self.dependencias_plan,
            "orden": [{"id": p.id, "titulo": p.titulo, "refs": p.refs,
                       "detalle": p.detalle} for p in self.orden],
            "integracion": self.integracion, "riesgos": self.riesgos,
            "compatibilidad": self.compatibilidad, "impacto": self.impacto,
            "pruebas_estrategia": self.pruebas_estrategia,
            "validacion": self.validacion, "alternativas": self.alternativas,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }
        return datos

    @classmethod
    def from_dict(cls, datos: dict) -> "Plan":
        try:
            orden = [Paso(**p) for p in datos.get("orden", [])]
            return cls(
                plan_id=str(datos["plan_id"]), spec_id=str(datos["spec_id"]),
                version=str(datos.get("version", "1.0.0")),
                status=str(datos.get("status", "draft")),
                hallazgos=dict(datos.get("hallazgos", {})),
                relacionados=list(datos.get("relacionados", [])),
                modificables=list(datos.get("modificables", [])),
                intactos=list(datos.get("intactos", [])),
                creables=list(datos.get("creables", [])),
                reutilizables=list(datos.get("reutilizables", [])),
                arquitectura=str(datos.get("arquitectura", "")),
                dependencias_plan=list(datos.get("dependencias_plan", [])),
                orden=orden,
                integracion=str(datos.get("integracion", "")),
                riesgos=list(datos.get("riesgos", [])),
                compatibilidad=str(datos.get("compatibilidad", "")),
                impacto=str(datos.get("impacto", "")),
                pruebas_estrategia=str(datos.get("pruebas_estrategia", "")),
                validacion=list(datos.get("validacion", [])),
                alternativas=list(datos.get("alternativas", [])),
                created_at=str(datos.get("created_at", "")),
                updated_at=str(datos.get("updated_at", "")),
            )
        except (KeyError, TypeError) as error:
            raise PlanError(f"registro de plan corrupto: {error}") from error


def derivar_orden(spec) -> list[Paso]:
    """Entidades → reglas → funcionales (aceptados primero) → integración →
    pruebas. Cada paso cita sus REQ (§8.5, §9.4)."""
    pasos: list[Paso] = []
    n = 1

    def agregar(titulo: str, refs: list, detalle: str = "") -> None:
        nonlocal n
        pasos.append(Paso(id=f"P{n:02d}", titulo=titulo, refs=refs, detalle=detalle))
        n += 1

    # Las entidades viven en §6 de la SPEC; se citan por nombre de sección.
    if spec.entidades:
        agregar("Modelar entidades de §6",
                [f"§6:{e.split(' (')[0]}" for e in spec.entidades],
                "Estructuras de datos antes que comportamiento.")
    if spec.reglas and not spec.reglas[0].startswith("Sin reglas"):
        agregar("Implementar reglas de negocio de §7",
                ["§7"], "Las reglas condicionan los funcionales.")
    aceptados = [(i, t) for i, t, e in spec.funcionales if e == "aceptado"]
    for req_id, texto in aceptados:
        agregar(f"Implementar {req_id}: {texto[:60]}", [req_id])
    pendientes = [(i, t) for i, t, e in spec.funcionales if e != "aceptado"]
    if pendientes:
        agregar("Definir o descartar funcionales pendientes de clarify",
                [i for i, _ in pendientes],
                "No implementar sin confirmación humana.")
    agregar("Integrar persistencia y componentes",
            ["§9", "§10"],
            "Conectar según fronteras de código; interfaces existentes intactas.")
    agregar("Escribir pruebas de §12 y ejecutar suite",
            [c.id for c in spec.casos],
            "Un caso por criterio antes de dar por terminado.")
    return pasos


def generar_desde_spec(spec, hallazgos: dict, historial: list,
                       plan_id: str) -> Plan:
    from datetime import datetime, timezone  # noqa: PLC0415
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    relacionados = componentes_relacionados(spec, hallazgos)
    greenfield = hallazgos["es_greenfield"]

    riesgos = [
        f"Supuesto sin aclarar: {s}" for s in spec.supuestos if not s.startswith("✓")
    ]
    for h in historial:
        if h.get("respuesta") and "no lo sé" in str(h["respuesta"]).lower():
            riesgos.append(f"{h['pregunta']} quedó sin definir: {h['respuesta']}")
    if not riesgos:
        riesgos = ["Sin riesgos detectados con la evidencia actual."]

    if greenfield:
        arquitectura = (
            "Proyecto vacío: propuesta mínima derivada de la SPEC — "
            f"módulos por entidad de §6 ({len(spec.entidades)}), "
            "capa de reglas de §7 y CLI/API según §8. Sin arquitectura previa que respetar."
        )
        creables = ["Estructura completa según §6–§8 de la SPEC"]
        modificables, intactos = [], []
        impacto = "Sin impacto: no hay código existente que romper."
        compatibilidad = "N/A (greenfield)."
        integracion = "Arranque desde cero siguiendo el orden de implementación."
    else:
        lengs = ", ".join(f"{k} ({v})" for k, v in hallazgos["lenguajes"].items())
        arquitectura = (
            f"Respetar arquitectura existente ({lengs}). "
            f"Reutilizar módulos internos: {', '.join(hallazgos['modulos_internos']) or 'ninguno detectado'}. "
            "Lo nuevo vive en módulos propios; lo existente solo se toca donde la SPEC lo exige."
        )
        creables = ["Módulos nuevos por entidad/funcional no cubiertos"]
        modificables = relacionados or ["(ningún archivo coincide nominalmente; crear módulos nuevos)"]
        intactos = ["Interfaces públicas de módulos reutilizados",
                    "Suite de pruebas existente (solo agregar, no reescribir)"]
        impacto = (f"Modificar únicamente: {', '.join(modificables)}. "
                   "El resto permanece intacto (§8.4).")
        compatibilidad = (
            f"Depende de: {', '.join(hallazgos['dependencias']) or 'solo biblioteca estándar'}. "
            f"Persistencia detectada: {', '.join(hallazgos['datos']) or 'ninguna'}."
        )
        integracion = ("Integrar por detrás de las interfaces existentes; "
                       "cada paso con su prueba antes del siguiente.")

    if hallazgos["pruebas"]:
        pruebas_estrategia = (
            f"Extender la suite existente ({len(hallazgos['pruebas'])} archivo(s), "
            "framework según manifiestos) con un caso por CRI de §12. No reescribir."
        )
    else:
        pruebas_estrategia = ("Crear suite mínima desde cero: un caso por criterio "
                              "de aceptación de §12.")

    alternativas = [
        "SUGERENCIA (no aprobada): si la persistencia crece, evaluar SQLite "
        "frente a JSON plano. Decidir con datos reales de volumen.",
        "SUGERENCIA (no aprobada): exponer API además de CLI solo si un "
        "funcional futuro lo exige; hoy no hay evidencia que lo pida.",
    ]

    return Plan(
        plan_id=plan_id,
        spec_id=spec.spec_id,
        hallazgos=hallazgos,
        relacionados=relacionados,
        modificables=modificables,
        intactos=intactos,
        creables=creables,
        reutilizables=hallazgos["modulos_internos"],
        arquitectura=arquitectura,
        dependencias_plan=hallazgos["dependencias"],
        orden=derivar_orden(spec),
        integracion=integracion,
        riesgos=riesgos,
        compatibilidad=compatibilidad,
        impacto=impacto,
        pruebas_estrategia=pruebas_estrategia,
        validacion=[f"{c.id} ({c.req_id}): {c.texto}" for c in spec.criterios],
        alternativas=alternativas,
        created_at=ahora,
        updated_at=ahora,
    )


def render_markdown(plan: Plan) -> str:
    lineas = [
        "---",
        f"plan_id: {plan.plan_id}",
        f"spec: {plan.spec_id}",
        f"plan_version: {plan.version}",
        f"status: {plan.status}",
        "---",
        "",
        f"# {plan.plan_id} — Plan para {plan.spec_id}",
        "",
        "## 1. Investigación del proyecto (§8.2)",
        f"Archivos analizados: {plan.hallazgos.get('total_archivos', 0)}; "
        f"greenfield: {plan.hallazgos.get('es_greenfield')}.",
        f"Lenguajes: {plan.hallazgos.get('lenguajes') or 'ninguno'}.",
        f"Carpetas: {', '.join(plan.hallazgos.get('carpetas', [])) or '—'}.",
        f"Dependencias: {', '.join(plan.hallazgos.get('dependencias_plan', plan.hallazgos.get('dependencias', []))) or 'solo estándar'}.",
        f"Persistencia: {', '.join(plan.hallazgos.get('datos', [])) or 'ninguna detectada'}.",
        f"Pruebas existentes: {len(plan.hallazgos.get('pruebas', []))} archivo(s).",
        f"Convenciones: {', '.join(plan.hallazgos.get('convenciones', [])) or '—'}.",
        f"Componentes relacionados (coincidencia nominal): {', '.join(plan.relacionados) or 'ninguno'}.",
        "",
        "## 2. Fronteras de código (§8.4)",
        f"Modificables: {', '.join(plan.modificables) or '—'}.",
        f"Intactos: {', '.join(plan.intactos) or '—'}.",
        f"Creables: {', '.join(plan.creables) or '—'}.",
        f"Reutilizables: {', '.join(plan.reutilizables) or '—'}.",
        "",
        "## 3. Arquitectura propuesta",
        plan.arquitectura,
        "",
        "## 4. Orden de implementación",
        *[f"- {p.id} {p.titulo} [refs: {', '.join(p.refs) or '—'}]"
          + (f" — {p.detalle}" if p.detalle else "") for p in plan.orden],
        "",
        "## 5. Estrategia de integración",
        plan.integracion,
        "",
        "## 6. Riesgos",
        *[f"- {r}" for r in plan.riesgos],
        "",
        "## 7. Compatibilidad e impacto",
        plan.compatibilidad,
        plan.impacto,
        "",
        "## 8. Estrategia de pruebas",
        plan.pruebas_estrategia,
        "",
        "## 9. Criterios de validación (§8.6: el plan responde a la SPEC)",
        *[f"- {v}" for v in plan.validacion],
        "",
        "## 10. Alternativas sugeridas (NO aprobadas)",
        *[f"- {a}" for a in plan.alternativas],
        "",
    ]
    return "\n".join(lineas)


SUGERENCIA_ESTADOS = ("sugerida", "aprobada", "descartada")


def _ahora() -> str:
    from datetime import datetime, timezone  # noqa: PLC0415

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Sugerencia:
    """Mejora detectada durante el trabajo, fuera del alcance (§40)."""

    id: str
    plan_id: str
    texto: str
    origen: str = ""
    tarea: str = ""
    estado: str = "sugerida"
    fecha: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "plan_id": self.plan_id, "texto": self.texto,
            "origen": self.origen, "tarea": self.tarea,
            "estado": self.estado, "fecha": self.fecha,
        }

    @classmethod
    def from_dict(cls, datos: dict) -> "Sugerencia":
        try:
            return cls(
                id=str(datos["id"]), plan_id=str(datos["plan_id"]),
                texto=str(datos["texto"]),
                origen=str(datos.get("origen", "")),
                tarea=str(datos.get("tarea", "")),
                estado=str(datos.get("estado", "sugerida")),
                fecha=str(datos.get("fecha", "")),
            )
        except (KeyError, TypeError) as error:
            raise PlanError(f"sugerencia corrupta: {error}") from error


def ruta_sugerencias(raiz, plan_id: str) -> Path:
    return Path(raiz) / store.SPECIFY_DIR / "sugerencias" / f"{plan_id}.json"


def listar_sugerencias(raiz, plan_id: str) -> list[Sugerencia]:
    ruta = ruta_sugerencias(raiz, plan_id)
    if not ruta.exists():
        return []
    datos = store.leer_json(ruta)
    if not isinstance(datos, list):
        raise PlanError("el registro de sugerencias está corrupto")
    return [Sugerencia.from_dict(d) for d in datos]


def _guardar_sugerencias(raiz, plan_id: str,
                         sugerencias: list[Sugerencia]) -> None:
    ruta = ruta_sugerencias(raiz, plan_id)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    store.escribir_json(ruta, [s.to_dict() for s in sugerencias])


def registrar_sugerencia(raiz, plan_id: str, texto: str, origen: str = "",
                         tarea: str = "") -> Sugerencia:
    """Registra una mejora en su propio registro: no toca PLAN ni tareas."""
    limpio = texto.strip()
    if not limpio:
        raise PlanError("la sugerencia necesita texto; no se registra vacía")
    sugerencias = listar_sugerencias(raiz, plan_id)
    sugerencia = Sugerencia(
        id=f"SUG-{len(sugerencias) + 1:03d}", plan_id=plan_id, texto=limpio,
        origen=origen.strip(), tarea=tarea.strip(), fecha=_ahora())
    sugerencias.append(sugerencia)
    _guardar_sugerencias(raiz, plan_id, sugerencias)
    return sugerencia


def decidir_sugerencia(raiz, plan_id: str, sug_id: str,
                       estado: str) -> Sugerencia:
    """Decisión humana explícita sobre una sugerencia (§40)."""
    if estado not in ("aprobada", "descartada"):
        raise PlanError("estado inválido: use «aprobada» o «descartada»")
    sugerencias = listar_sugerencias(raiz, plan_id)
    for sugerencia in sugerencias:
        if sugerencia.id == sug_id:
            sugerencia.estado = estado
            _guardar_sugerencias(raiz, plan_id, sugerencias)
            return sugerencia
    raise PlanError(f"sugerencia inexistente: {sug_id}")
