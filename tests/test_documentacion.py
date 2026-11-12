"""La documentación del repo no puede apuntar a rutas que no existen.

Los enlaces de las notas de release son URL absolutas a `blob/<tag>` y los
revisa `scripts/verificar_release.py`; aquí se cubre lo otro: los enlaces
relativos de los documentos del repo, las referencias `ruta.py::símbolo` de
los documentos de remediación, las rutas del repo citadas como código en la
prosa y las rutas del proyecto del usuario (`specs/…`, `.specify/…`), que se
rompen en silencio cuando el código o el flujo cambian.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Se ignoran los bloques de código: ahí hay órdenes de ejemplo, no enlaces.
_BLOQUE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
_ENLACE = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_DEFINICION = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
# Solo rutas de paquetes del repo: si no, la prosa que cita «archivo.py::
# símbolo» como ejemplo cuenta como referencia real.
_SIMBOLO = re.compile(
    r"`((?:cli|core|mcp|scripts|state|tests)/[\w./-]+\.py)::"
    r"([A-Za-z_][A-Za-z0-9_]*)`")

# Rutas del repo citadas en la prosa como código: `cli/main.py`,
# `tests/test_ide.py`. Solo se revisan las que empiezan por una carpeta de
# este repo o son un archivo de la raíz; `specs/`, `.specify/`, `src/` y las
# rutas absolutas son del proyecto del usuario y no existen aquí.
_CITA = re.compile(r"`([^`\n]+)`")
_CARPETAS_REPO = ("cli/", "core/", "ide/", "mcp/", "scripts/", "state/",
                  "tests/", "docs/")
_ARCHIVOS_REPO = ("README.md", "CHANGELOG.md", "CONTRIBUTING.md",
                  "CODE_OF_CONDUCT.md", "SECURITY.md", "LICENSE",
                  "pyproject.toml", "requirements-dev.txt")
# Marcas de que el texto no es una ruta concreta: huecos, comodines o
# versiones de plantilla (`docs/release-notes-vX.Y.Z.md`).
_NO_ES_RUTA = re.compile(r"[<>{}*…\s]|::|^[./~]|X\.Y\.Z|\.\.\.")

# Carpetas que el toolkit escribe en el proyecto del usuario, no en este repo.
GENERADAS = (".claude/skills/", ".cursor/commands/", ".github/prompts/",
             ".github/skills/", ".windsurf/workflows/", ".agents/skills/",
             ".specify/")
# Notas y versiones con hueco: `release-notes-vX.Y.Z.md` es una plantilla.
PLANTILLAS = ("release-notes-vX.Y.Z.md",)


def documentos() -> list[Path]:
    return sorted(p for patron in ("*.md", "docs/*.md", "ide/*.md",
                                   "ide/vscode/*.md")
                  for p in RAIZ.glob(patron))


def _sin_bloques(ruta: Path) -> str:
    return _BLOQUE.sub("", ruta.read_text(encoding="utf-8"))


class TestEnlacesRelativos(unittest.TestCase):
    def test_los_enlaces_relativos_existen(self):
        revisados = 0
        for ruta in documentos():
            for destino in (_ENLACE.findall(_sin_bloques(ruta)) +
                            _DEFINICION.findall(_sin_bloques(ruta))):
                if destino.startswith(("http://", "https://", "mailto:", "#")):
                    continue  # los absolutos los revisa el verificador
                if destino.startswith(GENERADAS) or destino in PLANTILLAS:
                    continue
                if "X.Y.Z" in destino:
                    continue
                revisados += 1
                objetivo = (ruta.parent / destino.split("#", 1)[0]).resolve()
                self.assertTrue(objetivo.exists(),
                                f"{ruta.relative_to(RAIZ)} enlaza a "
                                f"{destino}, que no existe")
        self.assertGreater(revisados, 5,
                           "la revisión no encontró enlaces: ¿cambió el formato?")

    def test_los_documentos_estan_en_la_lista(self):
        """Si el glob deja de encontrar un documento, el test pasaría vacío."""
        nombres = {p.name for p in documentos()}
        for esperado in ("README.md", "CHANGELOG.md", "CONTRIBUTING.md",
                         "RELEASES.md", "COMPATIBILIDAD.md", "PRUEBA-MANUAL.md"):
            self.assertIn(esperado, nombres)


class TestReferenciasASimbolos(unittest.TestCase):
    """`core/build.py::ejecutar_pruebas` tiene que seguir existiendo."""

    def test_cada_simbolo_citado_existe(self):
        revisados = 0
        for ruta in documentos():
            for archivo, simbolo in _SIMBOLO.findall(_sin_bloques(ruta)):
                revisados += 1
                destino = (RAIZ / archivo)
                self.assertTrue(destino.is_file(),
                                f"{ruta.relative_to(RAIZ)} cita {archivo}, "
                                f"que no existe")
                arbol = ast.parse(destino.read_text(encoding="utf-8"))
                nombres = {n.name for n in ast.walk(arbol)
                           if isinstance(n, (ast.FunctionDef,
                                             ast.AsyncFunctionDef,
                                             ast.ClassDef))}
                nombres |= {t.id for n in ast.walk(arbol)
                            if isinstance(n, ast.Assign)
                            for t in n.targets if isinstance(t, ast.Name)}
                self.assertIn(simbolo, nombres,
                              f"{ruta.relative_to(RAIZ)} cita "
                              f"{archivo}::{simbolo}, que ya no está")
        self.assertGreater(revisados, 3, "no se encontró ninguna referencia")


# Rutas del proyecto del usuario: existen en el árbol que el toolkit escribe,
# no en este repo. Se comprueban contra una corrida real, no contra la prosa.
# Aquí el punto inicial es legítimo (`.specify/…`), a diferencia de _NO_ES_RUTA.
_CITA_PROYECTO = re.compile(r"`((?:\.specify|specs)/[^`\s]*)`")
_NO_ES_RUTA_PROYECTO = re.compile(r"[<>{}*…\s]|::|^[~/]|X\.Y\.Z|\.\.\.")
# Documentadas, pero solo existen si la persona las crea (un hook, una revisión
# de la SPEC, una sugerencia). Ahí se exige que la CLI las conozca.
_SOLO_A_PEDIDO = (".specify/hooks/", ".specify/spec_history/",
                  ".specify/sugerencias/")


def _correr(cli: list[str], *args: str) -> str:
    proceso = subprocess.run([*cli, *args], capture_output=True, text=True,
                             cwd=RAIZ, input="", timeout=120)
    if proceso.returncode != 0:
        raise AssertionError(
            f"{' '.join(args)} falló: {proceso.stdout}{proceso.stderr}")
    return proceso.stdout


def _proyecto_completo(base: Path) -> Path:
    """Proyecto con todo lo que escribe una corrida normal del flujo."""
    root = base / "proyecto"
    cli = [sys.executable, str(RAIZ / "cli" / "main.py"), "--root", str(root)]
    _correr(cli, "init", "--sin-comandos")
    _correr(cli, "enrich", "Quiero un dashboard para gestionar un kiosco")
    _correr(cli, "enrich", "--accept", "ENR-001")
    _correr(cli, "specify", "ENR-001", "--titulo", "Kiosco")
    _correr(cli, "specify", "--approve", "SPEC-001")
    abiertas = [linea.split()[1]
                for linea in _correr(cli, "clarify", "--list", "SPEC-001")
                .splitlines() if linea.startswith("○")]
    for numero, clarificacion in enumerate(abiertas, 1):
        _correr(cli, "clarify", "SPEC-001", "--answer", clarificacion,
                f"respuesta {numero}")
    for paso in (("plan", "SPEC-001"), ("plan", "--gate", "PLAN-001"),
                 ("tasks", "PLAN-001"), ("analyze", "PLAN-001"),
                 ("build", "PLAN-001"), ("instrucciones", "--guardar")):
        _correr(cli, *paso)
    return root


# Lo que las guías prometen de cada artefacto —que la SPEC va aprobada, que el
# plan deriva de ella, que los informes traen su veredicto— se busca en el
# archivo real: existir no basta si viene vacío o con otro formato.
_PROMESAS_DE_CONTENIDO = (
    ("specs/SPEC-001.md", ("spec_id: SPEC-001", "status: approved")),
    (".specify/planes/PLAN-001.md",
     ("plan_id: PLAN-001", "spec: SPEC-001", "# PLAN-001")),
    (".specify/tareas/TASKS-PLAN-001.md",
     ("plan: PLAN-001", "## TASK-001")),
    (".specify/informes/INFORME-PLAN-001.md",
     ("plan: PLAN-001", "# Informe de consistencia", "Hallazgos:")),
    (".specify/INSTRUCCIONES.md",
     ("# Instrucciones del agente", "## 1. Reglas del motor")),
)


class TestRutasDelProyecto(unittest.TestCase):
    """`.specify/planes/PLAN-001.md` tiene que ser lo que el flujo escribe."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.raiz = _proyecto_completo(Path(cls._tmp.name))

    def test_las_rutas_citadas_las_escribe_la_corrida(self):
        revisadas = 0
        for documento in documentos():
            for cita in _CITA_PROYECTO.findall(_sin_bloques(documento)):
                if (_NO_ES_RUTA_PROYECTO.search(cita)
                        or cita in _SOLO_A_PEDIDO):
                    continue
                revisadas += 1
                self.assertTrue(
                    (self.raiz / cita.rstrip("/")).exists(),
                    f"{documento.relative_to(RAIZ)} cita {cita}, que la CLI "
                    "no escribe")
        self.assertGreaterEqual(revisadas, 12,
                                "la revisión no encontró rutas del proyecto")

    def test_el_contenido_prometido_esta_en_los_artefactos(self):
        for relativa, promesas in _PROMESAS_DE_CONTENIDO:
            texto = (self.raiz / relativa).read_text(encoding="utf-8")
            for promesa in promesas:
                self.assertIn(promesa, texto,
                              f"{relativa} no contiene {promesa!r}")

    def test_las_que_se_crean_a_pedido_estan_en_el_codigo(self):
        fuentes = "".join(
            archivo.read_text(encoding="utf-8")
            for carpeta in ("cli", "core", "state")
            for archivo in (RAIZ / carpeta).rglob("*.py"))
        for cita in _SOLO_A_PEDIDO:
            nombre = cita.rstrip("/").rsplit("/", 1)[-1]
            self.assertIn(nombre, fuentes,
                          f"ninguna parte de la CLI menciona {cita}")


class TestRutasCitadas(unittest.TestCase):
    """`cli/main.py` citado en la prosa tiene que seguir estando."""

    def test_las_rutas_citadas_existen(self):
        revisadas = 0
        for ruta in documentos():
            for cita in _CITA.findall(_sin_bloques(ruta)):
                candidato = cita.strip()
                if _NO_ES_RUTA.search(candidato):
                    continue
                if not (candidato.startswith(_CARPETAS_REPO) or
                        candidato in _ARCHIVOS_REPO):
                    continue
                revisadas += 1
                self.assertTrue(
                    (RAIZ / candidato).exists(),
                    f"{ruta.relative_to(RAIZ)} cita {candidato}, que no existe")
        self.assertGreater(revisadas, 100,
                           "la revisión no encontró rutas: ¿cambió el formato?")


if __name__ == "__main__":
    unittest.main()
