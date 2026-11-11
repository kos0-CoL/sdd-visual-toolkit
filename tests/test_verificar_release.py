"""Pruebas de `scripts/verificar_release.py` (antes y después de publicar)."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import verificar_release as vr

TAG = "v0.1.2"
SLUG = "kos0-CoL/sdd-visual-toolkit"
CI = ("gh", "api", "repos/{owner}/{repo}/commits/def456/check-runs",
      "--jq", ".check_runs | map({name, status, conclusion})")


def _salida(codigo: int = 0, stdout: str = "", stderr: str = "") -> vr.Salida:
    return vr.Salida(codigo, stdout, stderr)


def _notas(ref: str = TAG) -> str:
    return ("# Notas\n\n"
            f"- [Changelog](https://github.com/{SLUG}/blob/{ref}/CHANGELOG.md)\n")


RELEASE = json.dumps({"tagName": TAG, "isDraft": False,
                      "isPrerelease": False, "body": _notas()})


def _respuestas() -> dict[tuple[str, ...], vr.Salida]:
    return {
        ("git", "rev-parse", "--verify", "--quiet", f"refs/tags/{TAG}"):
            _salida(stdout="abc123"),
        ("git", "cat-file", "-t", "abc123"): _salida(stdout="tag"),
        ("git", "rev-parse", f"{TAG}^{{}}"): _salida(stdout="def456"),
        ("git", "ls-remote", "--tags", "origin", f"refs/tags/{TAG}",
         f"refs/tags/{TAG}^{{}}"):
            _salida(stdout=f"abc123\trefs/tags/{TAG}\n"
                           f"def456\trefs/tags/{TAG}^{{}}\n"),
        CI: _salida(stdout=json.dumps([
            {"name": "tests (Python 3.12)", "status": "completed",
             "conclusion": "success"}])),
        ("git", "show", f"{TAG}:pyproject.toml"):
            _salida(stdout='[project]\nversion = "0.1.2"\n'),
        ("git", "show", f"{TAG}:CHANGELOG.md"):
            _salida(stdout="## [No publicado]\n\nSin cambios.\n\n"
                           "## [0.1.2] — 2026-11-10\n"),
        ("gh", "release", "view", TAG, "--json",
         "tagName,isDraft,isPrerelease,body"): _salida(stdout=RELEASE),
        ("git", "show", f"{TAG}:docs/release-notes-{TAG}.md"):
            _salida(stdout=_notas()),
        ("gh", "api", f"repos/{SLUG}/contents/CHANGELOG.md?ref={TAG}",
         "--jq", ".path"): _salida(stdout="CHANGELOG.md"),
        ("git", "remote", "get-url", "origin"):
            _salida(stdout=f"https://github.com/{SLUG}.git\n"),
    }


def _correr_con(respuestas):
    def correr(comando):
        return respuestas.get(tuple(comando),
                              _salida(1, stderr="orden no simulada"))
    return correr


class TestVerificarRelease(unittest.TestCase):
    def verificar(self, cambios: dict | None = None):
        respuestas = _respuestas()
        respuestas.update(cambios or {})
        return vr.verificar("0.1.2", _correr_con(respuestas))

    def test_todo_correcto(self):
        resultados = self.verificar()
        self.assertEqual([mensaje for ok, mensaje in resultados if not ok], [])
        self.assertEqual(len(resultados), 8)

    def test_ci_rojo_falla(self):
        resultados = self.verificar({CI: _salida(stdout=json.dumps([
            {"name": "tests (Python 3.12)", "status": "completed",
             "conclusion": "failure"}]))})
        fallos = [mensaje for ok, mensaje in resultados if not ok]
        self.assertEqual(len(fallos), 1)
        self.assertIn("no está verde", fallos[0])
        self.assertIn("tests (Python 3.12) (failure)", fallos[0])

    def test_ci_sin_terminar_falla(self):
        resultados = self.verificar({CI: _salida(stdout=json.dumps([
            {"name": "tests (Python 3.12)", "status": "in_progress",
             "conclusion": None}]))})
        fallos = [mensaje for ok, mensaje in resultados if not ok]
        self.assertEqual(len(fallos), 1)
        self.assertIn("sin terminar", fallos[0])

    def test_ci_sin_checks_falla(self):
        resultados = self.verificar({CI: _salida(stdout="[]")})
        fallos = [mensaje for ok, mensaje in resultados if not ok]
        self.assertEqual(len(fallos), 1)
        self.assertIn("no tiene checks", fallos[0])

    def test_ci_ilegible_falla(self):
        resultados = self.verificar({CI: _salida(1, stderr="HTTP 404")})
        fallos = [mensaje for ok, mensaje in resultados if not ok]
        self.assertEqual(len(fallos), 1)
        self.assertIn("HTTP 404", fallos[0])

    def test_sin_tag_local_se_detiene(self):
        resultados = self.verificar({
            ("git", "rev-parse", "--verify", "--quiet", f"refs/tags/{TAG}"):
                _salida(1)})
        self.assertEqual(len(resultados), 1)
        self.assertFalse(resultados[0][0])
        self.assertIn("falta el tag", resultados[0][1])

    def test_tag_ligero_no_cuenta_como_anotado(self):
        resultados = self.verificar({
            ("git", "cat-file", "-t", "abc123"): _salida(stdout="commit")})
        self.assertFalse(resultados[0][0])
        self.assertIn("no es anotado", resultados[0][1])

    def test_tag_remoto_desfasado(self):
        resultados = self.verificar({
            ("git", "ls-remote", "--tags", "origin", f"refs/tags/{TAG}",
             f"refs/tags/{TAG}^{{}}"):
                _salida(stdout=f"abc123\trefs/tags/{TAG}\n"
                               f"999999\trefs/tags/{TAG}^{{}}\n")})
        self.assertFalse(resultados[1][0])
        self.assertIn("origin", resultados[1][1])

    def test_tag_sin_la_version(self):
        resultados = self.verificar({
            ("git", "show", f"{TAG}:pyproject.toml"):
                _salida(stdout='version = "0.1.1"\n')})
        self.assertFalse(resultados[3][0])
        self.assertIn("0.1.1", resultados[3][1])

    def test_changelog_sin_la_version(self):
        resultados = self.verificar({
            ("git", "show", f"{TAG}:CHANGELOG.md"):
                _salida(stdout="## [0.1.1] — 2026-11-10\n")})
        self.assertFalse(resultados[4][0])
        self.assertIn("0.1.1", resultados[4][1])

    def test_release_en_borrador(self):
        resultados = self.verificar({
            ("gh", "release", "view", TAG, "--json",
             "tagName,isDraft,isPrerelease,body"):
                _salida(stdout=json.dumps({"tagName": TAG, "isDraft": True,
                                           "isPrerelease": False,
                                           "body": _notas()}))})
        self.assertFalse(resultados[5][0])
        self.assertIn("sin publicar", resultados[5][1])

    def test_release_inexistente(self):
        resultados = self.verificar({
            ("gh", "release", "view", TAG, "--json",
             "tagName,isDraft,isPrerelease,body"):
                _salida(1, stderr="release not found")})
        self.assertFalse(resultados[5][0])
        self.assertIn("release not found", resultados[5][1])

    def test_cuerpo_autogenerado_por_github(self):
        resultados = self.verificar({
            ("gh", "release", "view", TAG, "--json",
             "tagName,isDraft,isPrerelease,body"):
                _salida(stdout=json.dumps({
                    "tagName": TAG, "isDraft": False, "isPrerelease": False,
                    "body": "## What's Changed\n* algo por @alguien\n"}))})
        fallos = [m for ok, m in resultados if not ok]
        self.assertEqual(len(fallos), 1)
        self.assertIn("no coincide con docs/release-notes", fallos[0])
        self.assertIn("gh release edit", fallos[0])

    def test_cuerpo_con_salto_final_cuenta_como_igual(self):
        resultados = self.verificar({
            ("gh", "release", "view", TAG, "--json",
             "tagName,isDraft,isPrerelease,body"):
                _salida(stdout=json.dumps({
                    "tagName": TAG, "isDraft": False, "isPrerelease": False,
                    "body": _notas() + "\n"}))})
        self.assertEqual([m for ok, m in resultados if not ok], [])

    def test_tag_legado_se_compara_con_las_notas_del_arbol(self):
        """0.1.0: su tag conserva notas que la página rompe y es inmutable."""
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            (raiz / "docs").mkdir()
            (raiz / "docs" / f"release-notes-{TAG}.md").write_text(
                _notas(), encoding="utf-8")
            respuestas = _respuestas()
            respuestas[("git", "show",
                        f"{TAG}:docs/release-notes-{TAG}.md")] = \
                _salida(stdout=_notas("main"))  # el tag quedó desfasado
            with mock.patch.object(vr, "NOTAS_DEL_ARBOL", {TAG}):
                resultados = vr.verificar("0.1.2", _correr_con(respuestas),
                                          raiz=raiz)
        self.assertEqual([mensaje for ok, mensaje in resultados if not ok], [])

    def con_notas(self, notas: str) -> dict:
        """Notas en el tag y en la release, para que solo falle lo que se mide."""
        return {
            ("git", "show", f"{TAG}:docs/release-notes-{TAG}.md"):
                _salida(stdout=notas),
            ("gh", "release", "view", TAG, "--json",
             "tagName,isDraft,isPrerelease,body"):
                _salida(stdout=json.dumps({
                    "tagName": TAG, "isDraft": False, "isPrerelease": False,
                    "body": notas})),
        }

    def test_enlace_a_otra_ref(self):
        resultados = self.verificar({
            ("git", "show", f"{TAG}:docs/release-notes-{TAG}.md"):
                _salida(stdout=_notas("main"))})
        self.assertFalse(resultados[-1][0])
        self.assertIn("main", resultados[-1][1])

    def test_enlace_relativo_falla(self):
        resultados = self.verificar(self.con_notas(
            "# Notas\n\n- [RELEASES](docs/RELEASES.md)\n"))
        fallos = [m for ok, m in resultados if not ok]
        self.assertIn("relativo", " ".join(fallos))

    def test_ruta_relativa_suelta_no_es_enlace(self):
        resultados = self.verificar(self.con_notas(
            f"# Notas\n\n- [x](https://github.com/{SLUG}/blob/{TAG}/CHANGELOG.md)\n"
            "- ver docs/RELEASES.md\n"))
        self.assertEqual([m for ok, m in resultados if not ok], [])

    def test_definicion_de_enlace_relativa_falla(self):
        resultados = self.verificar(self.con_notas(
            "# Notas\n\n- [Changelog][cl]\n\n[cl]: docs/CHANGELOG.md\n"))
        fallos = [m for ok, m in resultados if not ok]
        self.assertIn("relativo", " ".join(fallos))

    def test_enlace_tree_falla(self):
        resultados = self.verificar(self.con_notas(
            f"# Notas\n\n- [docs](https://github.com/{SLUG}/tree/{TAG}/docs)\n"))
        fallos = [m for ok, m in resultados if not ok]
        self.assertEqual(len(fallos), 1, fallos)
        self.assertIn("tree", fallos[0])

    def test_enlace_a_otro_repositorio_falla(self):
        resultados = self.verificar(self.con_notas(
            "# Notas\n\n- [otro](https://github.com/otro/repo/blob/"
            f"{TAG}/docs/RELEASES.md)\n"))
        fallos = [m for ok, m in resultados if not ok]
        self.assertIn("otro/repo", " ".join(fallos))
        self.assertIn(f"no a {SLUG}", " ".join(fallos))

    def test_blob_con_ancla_no_falla(self):
        resultados = self.verificar(self.con_notas(
            f"# Notas\n\n- [CHANGELOG](https://github.com/{SLUG}/blob/{TAG}/"
            "CHANGELOG.md#no-publicado)\n"))
        self.assertEqual([m for ok, m in resultados if not ok], [])

    def test_enlaces_de_navegacion_no_se_exigen_blob(self):
        resultados = self.verificar(self.con_notas(
            f"# Notas\n\n- [x](https://github.com/{SLUG}/blob/{TAG}/CHANGELOG.md)\n"
            f"\n**Full Changelog**: https://github.com/{SLUG}/compare/"
            "v0.1.1...v0.1.2\n"))
        self.assertEqual([m for ok, m in resultados if not ok], [])

    def test_clon_en_bloque_de_codigo_no_es_enlace(self):
        resultados = self.verificar(self.con_notas(
            f"# Notas\n\n```\ngit clone https://github.com/{SLUG}.git\n```\n\n"
            f"- [x](https://github.com/{SLUG}/blob/{TAG}/CHANGELOG.md)\n"))
        self.assertEqual([m for ok, m in resultados if not ok], [])

    def test_blob_sin_ruta_falla(self):
        resultados = self.verificar(self.con_notas(
            f"# Notas\n\n- [CHANGELOG](https://github.com/{SLUG}/blob/{TAG})\n"))
        fallos = [m for ok, m in resultados if not ok]
        self.assertEqual(len(fallos), 1, fallos)
        self.assertIn("no apunta a un fichero", fallos[0])

    def test_enlace_roto_en_la_ref(self):
        resultados = self.verificar({
            ("gh", "api", f"repos/{SLUG}/contents/CHANGELOG.md?ref={TAG}",
             "--jq", ".path"): _salida(1, stderr="not found")})
        self.assertFalse(resultados[-1][0])
        self.assertIn("CHANGELOG.md", resultados[-1][1])

    def test_sin_notas_en_el_tag(self):
        resultados = self.verificar({
            ("git", "show", f"{TAG}:docs/release-notes-{TAG}.md"):
                _salida(128, stderr="path does not exist")})
        self.assertFalse(resultados[-1][0])
        self.assertIn("release-notes", resultados[-1][1])


PREVIA = "v0.1.4"
CI_PREVIO = ("gh", "api", "repos/{owner}/{repo}/commits/abc123/check-runs",
             "--jq", ".check_runs | map({name, status, conclusion})")


def _changelog(version: str = "0.1.4", previa: str = "0.1.3",
               sin_publicar: str = "", enlaces: bool = True) -> str:
    texto = ("# Changelog\n\n## [No publicado]\n\n" + sin_publicar +
             f"\n## [{version}] — 2026-11-10\n\n### Añadido\n\n- algo.\n\n"
             f"## [{previa}] — 2026-11-10\n")
    if enlaces:
        texto += (f"\n[No publicado]: https://github.com/{SLUG}"
                  f"/compare/v{version}...HEAD\n"
                  f"[{version}]: https://github.com/{SLUG}"
                  f"/releases/tag/v{version}\n")
    return texto


class TestVerificarPrevio(unittest.TestCase):
    """Comprobaciones que se pueden hacer antes de crear el tag."""

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self._temporal.name)
        (self.raiz / "docs").mkdir()
        self.escribir(version="0.1.4")

    def tearDown(self):
        self._temporal.cleanup()

    def escribir(self, version: str, changelog: str | None = None,
                 notas: str | None = None,
                 extension: str | None = None) -> None:
        (self.raiz / "pyproject.toml").write_text(
            f'[project]\nversion = "{version}"\n', encoding="utf-8")
        (self.raiz / "ide" / "vscode").mkdir(parents=True, exist_ok=True)
        (self.raiz / "ide" / "vscode" / "package.json").write_text(
            json.dumps({"name": "sdd-visual-toolkit",
                        "version": version if extension is None else extension}),
            encoding="utf-8")
        (self.raiz / "CHANGELOG.md").write_text(
            _changelog(version=version) if changelog is None else changelog,
            encoding="utf-8")
        ruta = self.raiz / "docs" / "release-notes-v0.1.4.md"
        if notas is None:
            ruta.write_text(_notas(PREVIA), encoding="utf-8")
        elif notas:
            ruta.write_text(notas, encoding="utf-8")

    def verificar(self, cambios: dict | None = None):
        respuestas = {
            ("git", "rev-parse", "--verify", "--quiet",
             "refs/tags/v0.1.4"): _salida(1),
            ("git", "ls-remote", "--tags", "origin", "refs/tags/v0.1.4"):
                _salida(stdout=""),
            ("git", "status", "--porcelain"): _salida(stdout=""),
            ("git", "rev-parse", "--abbrev-ref", "HEAD"):
                _salida(stdout="main"),
            ("git", "rev-parse", "HEAD"): _salida(stdout="abc123"),
            ("git", "rev-parse", "origin/main"): _salida(stdout="abc123"),
            ("git", "tag", "--list", "v*"):
                _salida(stdout="v0.1.2\nv0.1.3\n"),
            ("git", "remote", "get-url", "origin"):
                _salida(stdout=f"git@github.com:{SLUG}.git\n"),
            CI_PREVIO: _salida(stdout=json.dumps([
                {"name": "tests (Python 3.12)", "status": "completed",
                 "conclusion": "success"}])),
        }
        respuestas.update(cambios or {})
        return vr.verificar_previo("0.1.4", _correr_con(respuestas),
                                   self.raiz)

    def fallos(self, cambios: dict | None = None) -> list[str]:
        return [m for ok, m in self.verificar(cambios) if not ok]

    def test_todo_correcto(self):
        resultados = self.verificar()
        self.assertEqual([m for ok, m in resultados if not ok], [])
        self.assertEqual(len(resultados), 11)

    def test_extension_con_otra_version_bloquea_el_tag(self):
        """El `.vsix` del release se empaqueta con la versión del manifiesto."""
        self.escribir(version="0.1.4", extension="0.1.0")
        fallos = " ".join(self.fallos())
        self.assertIn("ide/vscode/package.json declara 0.1.0", fallos)

    def test_ci_rojo_bloquea_el_tag(self):
        self.assertIn("no está verde", " ".join(self.fallos({
            CI_PREVIO: _salida(stdout=json.dumps([
                {"name": "tests (Python 3.12)", "status": "completed",
                 "conclusion": "failure"}]))})))

    def test_ci_sin_terminar_bloquea_el_tag(self):
        self.assertIn("sin terminar", " ".join(self.fallos({
            CI_PREVIO: _salida(stdout=json.dumps([
                {"name": "tests (Python 3.12)", "status": "queued",
                 "conclusion": None}]))})))

    def test_ci_sin_checks_bloquea_el_tag(self):
        self.assertIn("no tiene checks", " ".join(self.fallos({
            CI_PREVIO: _salida(stdout="[]")})))

    def test_ci_ilegible_bloquea_el_tag(self):
        self.assertIn("no se pudo leer el CI", " ".join(self.fallos({
            CI_PREVIO: _salida(1, stderr="HTTP 403")})))

    def test_tag_existente_en_local(self):
        resultados = self.verificar({
            ("git", "rev-parse", "--verify", "--quiet",
             "refs/tags/v0.1.4"): _salida(stdout="abc123")})
        self.assertEqual(len(resultados), 1)
        self.assertIn("inmutable", resultados[0][1])

    def test_tag_existente_en_origin(self):
        resultados = self.verificar({
            ("git", "ls-remote", "--tags", "origin",
             "refs/tags/v0.1.4"):
                _salida(stdout="abc123\trefs/tags/v0.1.4\n")})
        self.assertEqual(len(resultados), 1)
        self.assertIn("origin", resultados[0][1])

    def test_arbol_con_cambios_sin_confirmar(self):
        self.assertIn("sin confirmar", " ".join(self.fallos({
            ("git", "status", "--porcelain"):
                _salida(stdout=" M CHANGELOG.md\n")})))

    def test_rama_distinta_de_main(self):
        self.assertIn("no main", " ".join(self.fallos({
            ("git", "rev-parse", "--abbrev-ref", "HEAD"):
                _salida(stdout="chore/release")})))

    def test_head_sin_empujar(self):
        self.assertIn("origin/main", " ".join(self.fallos({
            ("git", "rev-parse", "HEAD"): _salida(stdout="abc123"),
            ("git", "rev-parse", "origin/main"):
                _salida(stdout="def456")})))

    def test_version_no_posterior_a_la_ultima(self):
        self.assertIn("no es posterior", " ".join(self.fallos({
            ("git", "tag", "--list", "v*"):
                _salida(stdout="v0.1.3\nv0.1.4\n")})))

    def test_no_publicado_con_vinetas(self):
        self.escribir(version="0.1.4",
                      changelog=_changelog(sin_publicar="- una viñeta\n"))
        self.assertIn("conserva 1 viñeta", " ".join(self.fallos()))

    def test_enlaces_del_pie_a_la_version_anterior(self):
        texto = _changelog().replace(f"compare/v0.1.4...HEAD",
                                     "compare/v0.1.3...HEAD")
        self.escribir(version="0.1.4", changelog=texto)
        self.assertIn("enlaces del pie", " ".join(self.fallos()))

    def test_notas_con_enlace_a_main(self):
        self.escribir(version="0.1.4", notas=_notas("main"))
        self.assertIn("main", " ".join(self.fallos()))

    def test_notas_con_enlace_relativo(self):
        self.escribir(version="0.1.4", notas="- [RELEASES](docs/RELEASES.md)\n")
        self.assertIn("relativo", " ".join(self.fallos()))

    def test_notas_con_enlace_tree(self):
        self.escribir(version="0.1.4", notas=(
            f"- [docs](https://github.com/{SLUG}/tree/v0.1.4/docs)\n"))
        self.assertIn("tree", " ".join(self.fallos()))

    def test_notas_con_enlace_a_otro_repositorio(self):
        self.escribir(version="0.1.4", notas=(
            "- [otro](https://github.com/otro/repo/blob/v0.1.4/docs/"
            "RELEASES.md)\n"))
        self.assertIn("otro/repo", " ".join(self.fallos()))

    def test_notas_ausentes(self):
        (self.raiz / "docs" / "release-notes-v0.1.4.md").unlink()
        self.assertIn("falta docs/release-notes", " ".join(self.fallos()))


class TestSalidaDelComando(unittest.TestCase):
    def ejecutar(self, *argumentos):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = vr.main(list(argumentos))
        return codigo, salida.getvalue()

    def test_version_invalida(self):
        codigo, texto = self.ejecutar("no-es-version")
        self.assertEqual(codigo, 1)
        self.assertIn("versión no válida", texto)

    def test_devuelve_1_con_fallos(self):
        with mock.patch.object(vr, "verificar",
                               return_value=[(False, "algo falla")]):
            codigo, texto = self.ejecutar("0.1.2")
        self.assertEqual(codigo, 1)
        self.assertIn("⛔ algo falla", texto)
        self.assertIn("1 comprobación(es) fallida(s)", texto)

    def test_devuelve_0_si_todo_pasa(self):
        with mock.patch.object(vr, "verificar", return_value=[(True, "todo ok")]):
            codigo, texto = self.ejecutar("0.1.2")
        self.assertEqual(codigo, 0)
        self.assertIn("✅ todo ok", texto)
        self.assertIn("v0.1.2 verificada", texto)

    def test_acepta_la_version_con_v(self):
        with mock.patch.object(vr, "verificar", return_value=[(True, "ok")]) as v:
            self.assertEqual(self.ejecutar("v0.1.2")[0], 0)
        v.assert_called_once_with("0.1.2")

    def test_previo_usa_el_modo_previo(self):
        with mock.patch.object(vr, "verificar_previo",
                               return_value=[(True, "libre")]) as previo, \
                mock.patch.object(vr, "verificar") as posterior:
            codigo, texto = self.ejecutar("--previo", "0.1.4")
        self.assertEqual(codigo, 0)
        previo.assert_called_once_with("0.1.4")
        posterior.assert_not_called()
        self.assertIn("lista para etiquetar", texto)
        self.assertIn("✅ libre", texto)


if __name__ == "__main__":
    unittest.main()
