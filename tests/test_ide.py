"""Pruebas de RF-39 — Integración con VS Code (§29).

La extensión es declarativa (package.json + extension.js sin build):
se verifica que cada comando de paleta exista en la CLI real, que la
vista lateral y la barra de estado estén declaradas, y que el JS
tenga sintaxis válida cuando hay node disponible.
"""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from cli.main import construir_parser  # noqa: E402

IDE = Path("ide/vscode")


def _comandos_cli() -> set:
    parser = construir_parser()
    subs = parser._actions[-1]  # subparsers de comandos
    nombres = set(subs.choices)
    req = subs.choices["req"]._actions[-1]
    nombres |= {"req %s" % c for c in req.choices}
    specs = subs.choices["specs"]._actions[-1]
    nombres |= {"specs %s" % c for c in specs.choices}
    return nombres


class TestManifiesto(unittest.TestCase):
    def test_package_valido_y_completo(self):
        manifiesto = json.loads((IDE / "package.json").read_text(
            encoding="utf-8"))
        comandos = manifiesto["contributes"]["commands"]
        self.assertGreaterEqual(len(comandos), 25)
        for c in comandos:
            self.assertTrue(c["command"].startswith("sdd."))
            self.assertTrue(c["title"].startswith("SDD:"))
        vistas = manifiesto["contributes"]["views"]["sdd-explorer"]
        self.assertTrue(any(v["id"] == "sddFases" for v in vistas))
        self.assertIn("sdd-explorer",
                      [c["id"] for c in manifiesto["contributes"]
                       ["viewsContainers"]["activitybar"]])
        props = manifiesto["contributes"]["configuration"]["properties"]
        self.assertIn("sddToolkit.python", props)
        self.assertIn("sddToolkit.cliPath", props)

    def test_paleta_solo_invoca_cli_real(self):
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        invocados = re.findall(r"cli:\s*'([^']+)'", fuente)
        self.assertGreaterEqual(len(invocados), 25)
        cli_reales = _comandos_cli()
        for inv in invocados:
            primero = inv.split()[0]
            self.assertIn(primero, cli_reales,
                          "la paleta invoca un comando inexistente: %s" % inv)

    def test_paleta_y_manifiesto_coinciden(self):
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        en_js = set(re.findall(r"id:\s*'(sdd\.[a-z]+)'", fuente))
        manifiesto = json.loads((IDE / "package.json").read_text(
            encoding="utf-8"))
        en_json = {c["command"] for c in manifiesto["contributes"]["commands"]}
        # La paleta registrada en JS existe en el manifiesto (más 2 internos).
        self.assertTrue(en_js <= (en_json | {"sdd.ejecutarEnChat", "sdd.actualizar"}))

    def test_pin_pide_plan_y_tarea(self):
        """`pin` es por tarea: con un solo campo la paleta respondía ⛔."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        entrada = re.search(r"\{ id: 'sdd\.pin'.*?\}", fuente, re.S)
        self.assertIsNotNone(entrada)
        pin = entrada.group(0)
        self.assertIn("prompt: 'PLAN-ID'", pin)
        self.assertIn("TASK-ID", pin)
        self.assertIn("flag: '--task'", pin)
        self.assertIn("entrada.siguiente", fuente)

    def test_los_fallos_se_notifican(self):
        """Un comando que sale con 1 no puede dejar el aviso al fondo de un
        terminal: la paleta captura la salida y notifica."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        corrida = re.search(r"function correr\(dir, argv.*?\n\}", fuente, re.S)
        self.assertIsNotNone(corrida, "falta la ejecución capturada")
        cuerpo = corrida.group(0)
        # `spawn` y no `execFile`: es el único que respeta `detached`. El
        # comando puede ser el intérprete o el `sdd` instalado.
        self.assertIn("spawn(resuelta.bin || cfg().python", cuerpo)
        self.assertIn("[...resuelta.args, '--root', dir, ...argv]", cuerpo)
        self.assertIn("codigo !== 0", cuerpo)
        self.assertIn("reportarFallo", cuerpo)
        # El aviso ofrece la salida completa de la CLI, no solo su primera línea.
        aviso = re.search(r"function reportarFallo\(.*?\n\}", fuente, re.S)
        self.assertIsNotNone(aviso, "falta el aviso de fallo")
        cuerpo_aviso = aviso.group(0)
        self.assertIn("showErrorMessage", cuerpo_aviso)
        self.assertIn("'Ver salida'", cuerpo_aviso)
        self.assertIn("mostrarSalida", cuerpo_aviso)
        self.assertIn("createOutputChannel", fuente)

    def test_la_cli_se_busca_si_la_carpeta_no_la_tiene(self):
        """En una carpeta sin `cli/main.py` la ruta relativa no existe: se usa
        el paquete instalado y, si tampoco está, se avisa de qué ajustar en vez
        de dejar el «can't open file» de python."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("'import cli.main'", fuente)
        self.assertIn("['-m', 'cli.main']", fuente)
        helper = re.search(r"function cli\(dir\).*?\n\}", fuente, re.S)
        self.assertIsNotNone(helper, "falta la resolución de la CLI")
        self.assertIn("existsSync", helper.group(0))
        corrida = re.search(r"function correr\(dir, argv.*?\n\}", fuente, re.S)
        self.assertIn("no encuentro la CLI en", corrida.group(0))
        self.assertIn("pip install -e .", corrida.group(0))

    def test_sin_ruta_local_usa_el_sdd_instalado(self):
        """Con el comando instalado no hace falta `cliPath` ni `python3`: la
        extensión ejecuta `sdd`, que es lo que instala `uv tool install`."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("const BINARIOS = ['sdd', 'toolkit'];", fuente)
        self.assertIn("process.env.PATH", fuente)
        helper = re.search(r"function cli\(dir\).*?\n\}", fuente, re.S)
        self.assertIsNotNone(helper, "falta la resolución de la CLI")
        cuerpo = helper.group(0)
        self.assertIn("binarioGlobal()", cuerpo)
        self.assertIn("bin, args: []", cuerpo)
        # El binario instalado gana al módulo de python y al error.
        self.assertLess(cuerpo.index("binarioGlobal()"),
                        cuerpo.index("tieneModulo()"))
        corrida = re.search(r"function correr\(dir, argv.*?\n\}", fuente, re.S)
        self.assertIn("resuelta.bin || cfg().python", corrida.group(0))

    def test_el_enoent_explica_que_falta(self):
        """`spawn python3 ENOENT` no dice nada: el aviso nombra el comando."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("error.code === 'ENOENT'", fuente)
        self.assertIn("no encontré «", fuente)
        self.assertIn("uv tool install", fuente)

    def test_las_pildoras_con_hueco_piden_el_dato(self):
        """La píldora `enrich «idea»` mandaba «idea» literal a la CLI."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("const HUECO = /«[^»]*»/;", fuente)
        cuerpo = re.search(r"function ejecutarOrden\(comando\).*?\n\}",
                           fuente, re.S)
        self.assertIsNotNone(cuerpo, "falta el manejo del hueco")
        texto = cuerpo.group(0)
        self.assertIn("pedirYCorrer(entrada, partes.slice(hueco + 1))", texto)
        self.assertIn("necesita un dato", texto)
        # Todo clic del panel y de las píldoras pasa por `ejecutarOrden`.
        self.assertIn(
            "registerCommand('sdd.ejecutarEnChat', (cliArgs) => ejecutarOrden(cliArgs))",
            fuente)

    def test_sin_carpeta_ofrece_abrirla(self):
        """El panel lee el estado de una carpeta: sin ella el aviso debe decir
        cómo abrirla, y la vista vacía trae el enlace para hacerlo."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("'Abrir carpeta…'", fuente)
        self.assertIn("workbench.action.files.openFolder", fuente)
        # Paleta ("ejecutar"), clic derecho ("abrirArtefacto"), chat y
        # auto-actualización del toolkit (`actualizarToolkit`).
        self.assertEqual(fuente.count("sinCarpeta();"), 5)
        manifiesto = json.loads((IDE / "package.json").read_text(
            encoding="utf-8"))
        bienvenidas = {v["view"]: v
                       for v in manifiesto["contributes"]["viewsWelcome"]}
        self.assertEqual(set(bienvenidas), {"sddFases", "sddFlujo"})
        for vista in bienvenidas.values():
            self.assertIn("workbench.action.files.openFolder",
                          vista["contents"])
            self.assertEqual(vista["when"], "workspaceFolderCount == 0")

    def test_el_chat_dibuja_las_pildoras_en_un_panel(self):
        """VS Code no deja botones dentro de Copilot Chat: el panel los dibuja."""
        fuente = (IDE / "chat.js").read_text(encoding="utf-8")
        self.assertIn("createWebviewPanel(", fuente)
        self.assertIn("'sddChat'", fuente)
        self.assertIn("const HUECO = /«[^»]*»|…/;", fuente)
        # Las píldoras se construyen como botones y avisan a la extensión.
        self.assertIn("createElement('button')", fuente)
        self.assertIn("postMessage({ tipo: 'orden'", fuente)
        # Las píldoras reales traen `…` de hueco, no solo «».
        self.assertIn("const HUECO = /«[^»]*»|…/;", fuente)
        # La orden se parte respetando comillas: la respuesta de clarify lleva
        # espacios y sin esto llegaba partida en varias palabras.
        self.assertIn("function partirOrden(texto)", fuente)
        self.assertIn("if (letra === '\"')", fuente)
        manifiesto = json.loads((IDE / "package.json").read_text(
            encoding="utf-8"))
        ids = {c["command"] for c in manifiesto["contributes"]["commands"]}
        self.assertIn("sdd.chat", ids)
        self.assertIn("view/title", manifiesto["contributes"]["menus"])
        extension = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("registerCommand('sdd.chat'", extension)
        self.assertIn("correrParaChat", extension)

    def test_clarify_valida_antes_de_abrir_el_terminal(self):
        """`clarify` es interactivo, pero un SPEC-ID inexistente falla antes:
        ese ⛔ tiene que notificarse y no abrir el terminal."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        validador = re.search(r"function validarYTerminal\(dir, argv\).*?\n\}",
                              fuente, re.S)
        self.assertIsNotNone(validador, "falta la validación previa de clarify")
        cuerpo = validador.group(0)
        self.assertIn("'--list', argv[1]", cuerpo)
        self.assertIn("terminal().sendText(orden)", cuerpo)
        self.assertIn("reportarFallo", cuerpo)
        despacho = re.search(r"function ejecutar\(cliArgs\).*?\n\}", fuente, re.S)
        self.assertIsNotNone(despacho, "falta el despacho de comandos")
        self.assertIn("validarYTerminal(dir, argv)", despacho.group(0))

    def test_solo_clarify_va_al_terminal(self):
        """`clarify` pregunta por stdin: el resto se puede capturar."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("INTERACTIVOS = new Set(['clarify'])", fuente)
        despacho = re.search(r"function ejecutar\(cliArgs\).*?\n\}",
                             fuente, re.S)
        self.assertIsNotNone(despacho, "falta el despacho de comandos")
        cuerpo = despacho.group(0)
        self.assertIn("INTERACTIVOS.has(argv[0])", cuerpo)
        self.assertIn("validarYTerminal(dir, argv)", cuerpo)
        self.assertIn("correr(dir, argv)", cuerpo)
        # El terminal se abre desde la validación, no desde el despacho.
        self.assertIn("terminal().sendText(orden)", fuente)

    def test_comando_largo_muestra_progreso(self):
        """`build` y `test` tardan: la paleta avisa en vez de esperar callada."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        corrida = re.search(r"function correr\(dir, argv.*?\n\}", fuente, re.S)
        self.assertIsNotNone(corrida, "falta la ejecución capturada")
        cuerpo = corrida.group(0)
        self.assertIn("withProgress", cuerpo)
        self.assertIn("ProgressLocation.Notification", cuerpo)
        self.assertIn("ESPERA_PROGRESO", cuerpo)
        # El indicador se cierra antes de notificar, en la misma devolución.
        self.assertLess(cuerpo.index("cerrar();"), cuerpo.index("const completo"))

    def test_cancelar_un_comando_largo(self):
        """El indicador se puede cancelar y el corte no se reporta como fallo."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        corrida = re.search(r"function correr\(dir, argv.*?\n\}", fuente, re.S)
        self.assertIsNotNone(corrida, "falta la ejecución capturada")
        cuerpo = corrida.group(0)
        self.assertIn("cancellable: true", cuerpo)
        self.assertIn("onCancellationRequested", cuerpo)
        self.assertIn("matarArbol(hijo)", cuerpo)
        self.assertIn("detached: process.platform !== 'win32'", cuerpo)
        # El corte alcanza a los nietos: `build` corre pytest como subproceso.
        arbol = re.search(r"function matarArbol\(hijo\).*?\n\}", fuente, re.S)
        self.assertIsNotNone(arbol, "falta el corte del árbol de procesos")
        corte = arbol.group(0)
        self.assertIn("process.kill(-hijo.pid, 'SIGTERM')", corte)
        self.assertIn("taskkill", corte)
        self.assertIn("hijo.kill()", corte)
        corte = cuerpo.split("if (cancelado)")[1].split("}")[0]
        self.assertIn("showInformationMessage", corte)
        self.assertIn("refrescar()", corte)
        self.assertNotIn("reportarFallo", corte)

    def test_el_tope_de_espera_se_configura(self):
        """Cinco minutos fijos no sirven para todos: el tope es un ajuste."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("'timeoutMinutos'", fuente)
        self.assertIn("minutos * 60000", fuente)
        self.assertIn("cfg().timeoutMinutos", fuente)
        manifiesto = (IDE / "package.json").read_text(encoding="utf-8")
        self.assertIn('"sddToolkit.timeoutMinutos"', manifiesto)
        self.assertIn('"default": 5', manifiesto)

    def test_el_panel_de_flujo_muestra_skill_y_artefacto(self):
        """VISUAL: el flujo va aparte de la lista de fases y fases, con su
        skill y su artefacto."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("class VistaFlujo", fuente)
        self.assertIn("registerTreeDataProvider('sddFlujo'", fuente)
        self.assertIn("doc.flujo", fuente)
        self.assertIn("fila.skill", fuente)
        self.assertIn("fila.artefacto", fuente)
        manifiesto = (IDE / "package.json").read_text(encoding="utf-8")
        self.assertIn('"sddFlujo"', manifiesto)
        self.assertIn('"Flujo SDD"', manifiesto)

    def test_clic_secundario_abre_el_artefacto(self):
        """El artefacto de la fase se abre desde el panel, sin buscar la ruta."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("it.contextValue = fila.artefacto ? 'sddFaseConArtefacto' : 'sddFaseSinArtefacto'",
                      fuente)
        self.assertIn("it._artefacto = fila.artefacto", fuente)
        abrir = re.search(r"async function abrirArtefacto\(nodo\).*?\n\}",
                          fuente, re.S)
        self.assertIsNotNone(abrir, "falta abrir el artefacto de la fase")
        cuerpo = abrir.group(0)
        self.assertIn("nodo._artefacto", cuerpo)
        self.assertIn("path.join(dir, relativo)", cuerpo)
        self.assertIn("fs.stat(uri)", cuerpo)
        self.assertIn("todavía no existe", cuerpo)
        self.assertIn("FileType.Directory", cuerpo)
        self.assertIn("revealInExplorer", cuerpo)
        self.assertIn("markdown.showPreview", cuerpo)
        self.assertIn("vscode.open", cuerpo)
        self.assertIn("registerCommand('sdd.abrirArtefacto'", fuente)
        manifiesto = json.loads((IDE / "package.json").read_text(
            encoding="utf-8"))
        comandos = {c["command"] for c in manifiesto["contributes"]["commands"]}
        self.assertIn("sdd.abrirArtefacto", comandos)
        menu = manifiesto["contributes"]["menus"]["view/item/context"]
        for vista in ("sddFlujo", "sddFases"):
            self.assertTrue(any(m["command"] == "sdd.abrirArtefacto"
                                and "view == %s" % vista in m["when"]
                                and "sddFaseConArtefacto" in m["when"]
                                for m in menu), vista)
        # La vista de fases reutiliza el artefacto que publica el flujo.
        fases = re.search(r"class VistaFases.*?\n\}", fuente, re.S)
        self.assertIsNotNone(fases, "falta la vista de fases")
        cuerpo = fases.group(0)
        self.assertIn("(d.flujo || [])", cuerpo)
        self.assertIn("conArtefacto", cuerpo)
        self.assertIn("conArtefacto(item(`📍 Fase: ${d.fase}`", cuerpo)
        self.assertIn(".map((n) => conArtefacto(", cuerpo)

    def test_el_paquete_lleva_licencia_y_lo_que_no_viaja(self):
        """Sin LICENSE y sin .vscodeignore, `vsce` avisa en cada empaquetado."""
        self.assertTrue((IDE / "LICENSE").is_file())
        ignorados = (IDE / ".vscodeignore").read_text(encoding="utf-8")
        self.assertIn(".vscodeignore", ignorados)
        self.assertEqual(
            Path("LICENSE").read_text(encoding="utf-8"),
            (IDE / "LICENSE").read_text(encoding="utf-8"),
            "la licencia de la extensión se separó de la del repo")

    def test_la_vista_avisa_de_skills_con_ruta_muerta(self):
        """El aviso lo calcula `export`; la extensión solo lo pinta."""
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        self.assertIn("d.avisos && d.avisos.skills", fuente)
        self.assertIn("Comandos de barra desactualizados", fuente)
        self.assertIn("avisos.rutas", fuente)
        self.assertIn("raiz.unshift(nodo)", fuente)
        self.assertIn("'↻ Regenerar los comandos'", fuente)
        self.assertIn("['comandos', '--regenerar']", fuente)
        self.assertIn("avisoExito: 'comandos de barra al día'", fuente)

    def test_init_avisa_y_refresca(self):
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        init = re.search(r"function inicializar\(dir\).*?\n\}", fuente, re.S)
        self.assertIsNotNone(init, "falta el atajo de init")
        cuerpo = init.group(0)
        self.assertIn("correr(dir, ['init']", cuerpo)
        self.assertIn("refrescar: true", cuerpo)

    def test_diez_puntos_del_29_cubiertos(self):
        fuente = (IDE / "extension.js").read_text(encoding="utf-8")
        # paleta, vista lateral, estado, fases, SPEC, tareas, pruebas,
        # historial, recuperación y acceso CLI (terminal).
        marcas = ["registerCommand", "registerTreeDataProvider",
                  "createStatusBarItem", "arbol", "traza",
                  "Progreso", "Pruebas", "historia",
                  "recover", "createTerminal"]
        for marca in marcas:
            self.assertIn(marca, fuente)

    def test_js_sintaxis_valida_si_hay_node(self):
        if shutil.which("node") is None:
            self.skipTest("sin node en este equipo")
        r = subprocess.run(["node", "--check", str(IDE / "extension.js")],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
