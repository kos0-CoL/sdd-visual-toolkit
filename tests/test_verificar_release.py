"""Pruebas de `scripts/verificar_release.py` (paso posterior a publicar)."""

from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest import mock

from scripts import verificar_release as vr

TAG = "v0.1.2"
SLUG = "kos0-CoL/sdd-visual-toolkit"
RELEASE = json.dumps({"tagName": TAG, "isDraft": False,
                      "isPrerelease": False})


def _salida(codigo: int = 0, stdout: str = "", stderr: str = "") -> vr.Salida:
    return vr.Salida(codigo, stdout, stderr)


def _notas(ref: str = TAG) -> str:
    return ("# Notas\n\n"
            f"- [Changelog](https://github.com/{SLUG}/blob/{ref}/CHANGELOG.md)\n")


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
        ("git", "show", f"{TAG}:pyproject.toml"):
            _salida(stdout='[project]\nversion = "0.1.2"\n'),
        ("git", "show", f"{TAG}:CHANGELOG.md"):
            _salida(stdout="## [No publicado]\n\nSin cambios.\n\n"
                           "## [0.1.2] — 2026-11-10\n"),
        ("gh", "release", "view", TAG, "--json",
         "tagName,isDraft,isPrerelease"): _salida(stdout=RELEASE),
        ("git", "show", f"{TAG}:docs/release-notes-{TAG}.md"):
            _salida(stdout=_notas()),
        ("gh", "api", f"repos/{SLUG}/contents/CHANGELOG.md?ref={TAG}",
         "--jq", ".path"): _salida(stdout="CHANGELOG.md"),
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
        self.assertEqual(len(resultados), 6)

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
        self.assertFalse(resultados[2][0])
        self.assertIn("0.1.1", resultados[2][1])

    def test_changelog_sin_la_version(self):
        resultados = self.verificar({
            ("git", "show", f"{TAG}:CHANGELOG.md"):
                _salida(stdout="## [0.1.1] — 2026-11-10\n")})
        self.assertFalse(resultados[3][0])
        self.assertIn("0.1.1", resultados[3][1])

    def test_release_en_borrador(self):
        resultados = self.verificar({
            ("gh", "release", "view", TAG, "--json",
             "tagName,isDraft,isPrerelease"):
                _salida(stdout=json.dumps({"tagName": TAG, "isDraft": True,
                                           "isPrerelease": False}))})
        self.assertFalse(resultados[4][0])
        self.assertIn("sin publicar", resultados[4][1])

    def test_release_inexistente(self):
        resultados = self.verificar({
            ("gh", "release", "view", TAG, "--json",
             "tagName,isDraft,isPrerelease"):
                _salida(1, stderr="release not found")})
        self.assertFalse(resultados[4][0])
        self.assertIn("release not found", resultados[4][1])

    def test_enlace_a_otra_ref(self):
        resultados = self.verificar({
            ("git", "show", f"{TAG}:docs/release-notes-{TAG}.md"):
                _salida(stdout=_notas("main"))})
        self.assertFalse(resultados[-1][0])
        self.assertIn("main", resultados[-1][1])

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


if __name__ == "__main__":
    unittest.main()
