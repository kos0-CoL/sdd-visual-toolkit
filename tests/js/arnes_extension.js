/* Arnés de la extensión sin editor: stub de `vscode`, providers reales y la
 * CLI real sobre un proyecto de prueba.
 *
 * Uso: node tests/js/arnes_extension.js REPO PROYECTO [PYTHON]
 *
 * No sustituye la pasada manual (`ide/PRUEBA-MANUAL.md`): no hay editor,
 * pintado ni interacción. Ejercita los caminos de `extension.js` —qué nodos
 * arma la vista, qué comando lleva cada uno, qué corre la paleta y qué avisa—
 * contra el mismo `export` que lee el IDE.
 *
 * Sale con 0 si todas las comprobaciones pasan, 1 si alguna falla y 2 si el
 * propio arnés se rompe.
 */
'use strict';

const Module = require('module');
const fs = require('fs');
const path = require('path');

const REPO = path.resolve(process.argv[2] || process.cwd());
const PROYECTO = path.resolve(process.argv[3] || '/tmp/sdd-manual');
const PYTHON = process.argv[4] || process.env.SDD_PYTHON || 'python3';
const EXTENSION = path.join(REPO, 'ide', 'vscode', 'extension.js');

const registros = {
  comandos: {}, providers: {}, mensajes: [], canal: [], terminal: [], ejecutados: [],
};
const settings = {
  'sddToolkit.python': PYTHON,
  'sddToolkit.cliPath': path.join(REPO, 'cli', 'main.py'),
  'sddToolkit.timeoutMinutos': 5,
};
let carpetas = [{ uri: { fsPath: PROYECTO } }];
let respuestas = []; // cola de showInputBox

class TreeItem {
  constructor(label, collapsibleState) {
    this.label = label;
    this.collapsibleState = collapsibleState;
  }
}
class EventEmitter {
  constructor() {
    this._h = [];
    this.event = (f) => { this._h.push(f); return { dispose() {} }; };
  }
  fire(e) { this._h.forEach((f) => f(e)); }
}
class ThemeIcon { constructor(id) { this.id = id; } }

const vscode = {
  TreeItem,
  ThemeIcon,
  TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
  StatusBarAlignment: { Left: 1, Right: 2 },
  ProgressLocation: { Notification: 15 },
  FileType: { File: 1, Directory: 2 },
  ViewColumn: { Active: -1, Beside: -2, One: 1, Two: 2 },
  EventEmitter,
  Uri: { file: (p) => ({ fsPath: p, scheme: 'file', toString: () => 'file://' + p }) },
  window: {
    terminals: [],
    createTerminal(name) {
      const t = {
        name, sendText: (texto) => registros.terminal.push(texto), show() {}, dispose() {},
      };
      return t;
    },
    createOutputChannel() {
      return {
        appendLine: (linea) => registros.canal.push(linea),
        show() { registros.canal_visible = true; },
        dispose() {},
      };
    },
    showInformationMessage: (m) => {
      registros.mensajes.push({ tipo: 'info', texto: m });
      return Promise.resolve(undefined);
    },
    showErrorMessage: (m) => {
      registros.mensajes.push({ tipo: 'error', texto: m });
      return Promise.resolve(undefined);
    },
    showWarningMessage: (m) => {
      registros.mensajes.push({ tipo: 'warning', texto: m });
      return Promise.resolve(undefined);
    },
    showInputBox: () => Promise.resolve(respuestas.length ? respuestas.shift() : undefined),
    withProgress: (_opciones, tarea) => tarea(
      { report: () => {} }, { onCancellationRequested: () => ({ dispose() {} }) }),
    createStatusBarItem: () => {
      const b = {
        text: '', tooltip: '', command: '', visible: false,
        show() { b.visible = true; }, hide() { b.visible = false; }, dispose() {},
      };
      registros.barra = b;
      return b;
    },
    registerTreeDataProvider: (id, provider) => {
      registros.providers[id] = provider;
      return { dispose() {} };
    },
    /* El panel del chat vive en un webview: el stub guarda lo que la extensión
     * le manda y simula el «listo» que el script real avisa al arrancar. Sin
     * ese aviso cada apertura esperaría 10 s de tiempo de seguridad. */
    createWebviewPanel(vista, titulo) {
      const manejadores = [];
      const panel = {
        title: titulo,
        visible: true,
        webview: {
          html: '',
          cspSource: 'arnes',
          asWebviewUri: (uri) => uri,
          postMessage: (mensaje) => {
            (registros.mensajes_webview ||= []).push(mensaje);
            return Promise.resolve(true);
          },
          onDidReceiveMessage: (fn) => {
            manejadores.push(fn);
            setTimeout(() => manejadores.forEach((f) => f({ tipo: 'listo' })), 0);
            return { dispose() {} };
          },
        },
        onDidDispose: () => ({ dispose() {} }),
        onDidChangeViewState: () => ({ dispose() {} }),
        reveal() {},
        dispose() { panel.visible = false; },
      };
      registros.panel = panel;
      return panel;
    },
  },
  workspace: {
    getConfiguration: (seccion) => ({
      get: (clave, defecto) => {
        const completa = seccion ? `${seccion}.${clave}` : clave;
        return completa in settings ? settings[completa] : defecto;
      },
    }),
    get workspaceFolders() { return carpetas; },
    /* La extensión se reengancha al abrir una carpeta o un documento: el
     * stub guarda los manejadores por si una prueba necesita dispararlos. */
    onDidChangeWorkspaceFolders: (fn) => {
      (registros.cambio_carpetas ||= []).push(fn);
      return { dispose() {} };
    },
    onDidOpenTextDocument: (fn) => {
      (registros.documentos_abiertos ||= []).push(fn);
      return { dispose() {} };
    },
    fs: {
      stat: (uri) => new Promise((resolve, reject) => {
        try {
          const st = fs.statSync(uri.fsPath);
          resolve({ type: st.isDirectory() ? vscode.FileType.Directory : vscode.FileType.File });
        } catch (e) { reject(e); }
      }),
    },
  },
  commands: {
    registerCommand: (id, handler) => {
      registros.comandos[id] = handler;
      return { dispose() {} };
    },
    executeCommand: (id, ...args) => {
      registros.ejecutados.push({ id, args });
      return Promise.resolve();
    },
  },
};

const cargar = Module._load;
Module._load = function (request) {
  if (request === 'vscode') return vscode;
  return cargar.apply(this, arguments);
};

const extension = require(EXTENSION);
const espera = (ms) => new Promise((r) => setTimeout(r, ms));

/* Espera a que se cumpla una condición en vez de dormir a ciegas: la CLI tarda
 * lo que tarde y un tiempo fijo hace la prueba lenta y frágil. */
async function hasta(condicion, ms = 20000) {
  const limite = Date.now() + ms;
  while (Date.now() < limite) {
    if (condicion()) return true;
    await espera(100);
  }
  return condicion();
}

const resultados = [];
function check(nombre, condicion, detalle = '') {
  resultados.push({ nombre, ok: !!condicion });
  console.log(`${condicion ? 'PASS' : 'FAIL'}  ${nombre}${detalle ? '  [' + detalle + ']' : ''}`);
}
const textos = (nodos) => nodos.map((n) => n.label);

(async () => {
  extension.activate({ subscriptions: [] });
  await hasta(() => registros.barra && registros.barra.text !== '');

  /* 1. Barra de estado y vista con el proyecto preparado */
  check('barra: fase actual', /SDD: .*Pruebas/.test(registros.barra.text), registros.barra.text);
  check('barra: tooltip con siguiente',
    /build PLAN-001/.test(String(registros.barra.tooltip)), String(registros.barra.tooltip));

  const raiz = await registros.providers.sddFases.getChildren();
  const etiquetas = textos(raiz);
  check('vista: fase', etiquetas.includes('📍 Fase: 🧪 Pruebas'), etiquetas[0]);
  check('vista: progreso 1/18', etiquetas.includes('Progreso: 1/18'));
  check('vista: tarea actual vacía', etiquetas.includes('Tarea actual: —'));
  check('vista: pruebas', etiquetas.some((t) => String(t).startsWith('Pruebas: ✅ P=2 F=0 cob=100%')));
  check('vista: siguiente', etiquetas.includes('➡ Siguiente: build PLAN-001'));
  /* Cada fila clicable lleva un argv coherente: mirar solo la etiqueta dejó
   * pasar `tasks SPEC-001` y un `reporte` sin ID. */
  const argvDe = (prefijo) => {
    const nodo = raiz.find((n) => String(n.label).startsWith(prefijo));
    return nodo && nodo.command ? String(nodo.command.arguments[0]) : null;
  };
  check('vista: «Progreso» pide las tareas del plan',
    argvDe('Progreso:') === 'tasks --list PLAN-001', argvDe('Progreso:'));
  check('vista: «Pruebas» pide el reporte de la tarea',
    argvDe('Pruebas:') === 'reporte TASK-001', argvDe('Pruebas:'));
  check('vista: «Tarea actual» sin tarea abre el tablero',
    argvDe('Tarea actual:') === 'tablero', argvDe('Tarea actual:'));

  /* El `📍 Fase` llega con emoji (`🧪 Pruebas`) y el flujo usa el nombre
   * pelado: si no se comparan sin marcas, el clic derecho no ofrece nada. */
  const filaFase = raiz[0];
  check('vista: «📍 Fase» trae el artefacto de su fase',
    filaFase && filaFase.contextValue === 'sddFaseConArtefacto' && !!filaFase._artefacto,
    filaFase && `${filaFase.contextValue || 'sin contextValue'} · ${filaFase._artefacto || 'sin artefacto'}`);
  check('vista: «📍 Fase» avisa del clic derecho en el tooltip',
    filaFase && /clic derecho: .+/.test(String(filaFase.tooltip)),
    filaFase && filaFase.tooltip);

  const grupoPildoras = raiz.find((n) => n.label === 'Píldoras');
  const pildoras = grupoPildoras
    ? await registros.providers.sddFases.getChildren(grupoPildoras) : [];
  check('vista: cuatro píldoras', pildoras.length === 4, String(pildoras.length));
  check('vista: píldoras sin candado', pildoras.every((p) => !String(p.label).includes('🔒')));
  check('vista: sin bloqueos', !etiquetas.includes('Bloqueos'));

  const grupoArbol = raiz.find((n) => n.label === 'Árbol de estados');
  const arbol = grupoArbol
    ? await registros.providers.sddFases.getChildren(grupoArbol) : [];
  check('vista: nueve fases', arbol.length === 9, String(arbol.length));
  check('vista: cinco completadas',
    arbol.filter((n) => String(n.label).startsWith('✅')).length === 5,
    String(arbol.filter((n) => String(n.label).startsWith('✅')).length));
  check('vista: sin aviso de skills', !etiquetas.some((t) => String(t).includes('desactualizados')));

  /* 2. Flujo SDD */
  const flujo = await registros.providers.sddFlujo.getChildren();
  check('flujo: nueve fases', flujo.length === 9, String(flujo.length));
  const especificacion = flujo.find((n) => String(n.label).includes('Especificación'));
  check('flujo: artefacto de la especificación',
    especificacion && especificacion._artefacto === 'specs/SPEC-001.md',
    especificacion && especificacion._artefacto);
  check('flujo: tooltip con skill y artefacto',
    especificacion && /skill \/sdd-specify/.test(String(especificacion.tooltip)),
    especificacion && especificacion.tooltip);
  const aclaraciones = flujo.find((n) => String(n.label).includes('Aclaraciones'));
  const argvAclarar = aclaraciones && aclaraciones.command
    ? aclaraciones.command.arguments[0] : null;
  check('flujo: clic ejecuta clarify',
    aclaraciones && aclaraciones.command
      && aclaraciones.command.command === 'sdd.ejecutarEnChat'
      && (argvAclarar === 'clarify SPEC-001'
        || JSON.stringify(argvAclarar) === JSON.stringify(['clarify', 'SPEC-001'])),
    aclaraciones && JSON.stringify(aclaraciones.command));

  /* 3. Clic derecho: abre el artefacto real */
  registros.ejecutados.length = 0;
  await registros.comandos['sdd.abrirArtefacto'](especificacion);
  const abierto = registros.ejecutados.find((e) => e.id === 'markdown.showPreview');
  check('clic derecho: vista previa del .md',
    abierto && /SPEC-001\.md$/.test(abierto.args[0].fsPath), abierto && abierto.args[0].fsPath);

  /* 3b. Los tres `.md` que materializa la preparación (§0.1.0 solo trae JSON) */
  const nodoDe = (fase) => flujo.find((n) => String(n.label).includes(fase));
  for (const [fase, ruta] of [
    ['Arquitectura', '.specify/planes/PLAN-001.md'],
    ['Tareas', '.specify/tareas/TASKS-PLAN-001.md'],
    ['Análisis', '.specify/informes/INFORME-PLAN-001.md'],
  ]) {
    const nodo = nodoDe(fase);
    check(`materializado: ${fase}`,
      nodo && nodo._artefacto === ruta, nodo && nodo._artefacto);
  }
  registros.ejecutados.length = 0;
  await registros.comandos['sdd.abrirArtefacto'](nodoDe('Arquitectura'));
  const planMd = registros.ejecutados.find((e) => e.id === 'markdown.showPreview');
  check('clic derecho: el plan abre su .md',
    planMd && /PLAN-001\.md$/.test(planMd.args[0].fsPath),
    planMd && planMd.args[0].fsPath);

  /* 4. Fase sin artefacto (si queda alguna): avisa y no abre nada */
  const sinArtefacto = flujo.find((n) => !n._artefacto);
  if (sinArtefacto) {
    registros.ejecutados.length = 0;
    registros.mensajes.length = 0;
    await registros.comandos['sdd.abrirArtefacto'](sinArtefacto);
    check('clic derecho: fase sin artefacto avisa',
      registros.mensajes.some((m) => /artefacto/.test(m.texto)),
      registros.mensajes.map((m) => m.texto).join(' | '));
    check('clic derecho: no abre nada sin artefacto',
      registros.ejecutados.length === 0, String(registros.ejecutados.length));
  } else {
    check('clic derecho: todas las fases con artefacto', true, 'nada que avisar');
  }

  /* 5. Paleta */
  registros.canal.length = 0;
  registros.comandos['sdd.status']();
  const corrio = await hasta(() => registros.canal.some((l) => l.startsWith('$ ')));
  check('paleta: status corre sin preguntar', corrio,
    registros.canal.find((l) => l.startsWith('$')) || '');

  registros.canal.length = 0;
  registros.mensajes.length = 0;
  respuestas = ['SPEC-001'];
  registros.comandos['sdd.plan']();
  await hasta(() => registros.canal.length || registros.mensajes.length);
  check('paleta: plan recibe el ID',
    registros.canal.some((l) => /plan SPEC-001/.test(l))
      || registros.mensajes.some((m) => /plan/i.test(m.texto)),
    registros.canal.find((l) => l.startsWith('$'))
      || registros.mensajes.map((m) => m.texto).join(' | '));

  registros.canal.length = 0;
  registros.mensajes.length = 0;  // el mensaje del paso anterior haría salir el `hasta`
  respuestas = ['PLAN-001', 'TASK-001'];
  registros.comandos['sdd.pin']();
  await hasta(() => registros.canal.some((l) => /pin PLAN-001/.test(l))
    || registros.mensajes.length);
  check('paleta: pin pide los dos datos',
    registros.canal.some((l) => /pin PLAN-001 --task TASK-001/.test(l)),
    registros.canal.find((l) => l.startsWith('$')) || '');

  registros.canal.length = 0;
  registros.mensajes.length = 0;
  respuestas = [''];  // campo vacío, no Escape
  registros.comandos['sdd.specify']();
  await hasta(() => registros.canal.length || registros.mensajes.length);
  check('paleta: opcional vacío corre --list',
    registros.canal.some((l) => /specify --list/.test(l)),
    registros.canal.find((l) => l.startsWith('$')) || '');

  registros.canal.length = 0;
  registros.mensajes.length = 0;
  respuestas = ['PLAN-001', undefined]; // el segundo dato, cancelado
  registros.comandos['sdd.pin']();
  await espera(400);
  check('paleta: Escape en el segundo no ejecuta',
    !registros.canal.some((l) => /pin PLAN-001/.test(l)) && registros.mensajes.length === 0);

  /* 6. Aclarar: abre el panel del chat y le pasa el resultado de la CLI. El
   * fixture no tiene preguntas pendientes, así que la CLI contesta por stdout;
   * un ID inexistente también se ve en el panel, sin abrir terminal. */
  registros.terminal.length = 0;
  registros.mensajes.length = 0;
  registros.mensajes_webview.length = 0;
  respuestas = ['SPEC-001'];
  registros.comandos['sdd.clarify']();
  await hasta(() => registros.mensajes_webview
    .some((m) => m.tipo === 'resultado' && /clarify SPEC-001/.test(String(m.orden))), 40000);
  check('clarify: abre el panel con la orden',
    Boolean(registros.panel) && registros.mensajes_webview
      .some((m) => m.tipo === 'resultado'),
    registros.mensajes_webview.map((m) => `${m.tipo}:${m.orden || ''}`).join(' | '));

  registros.terminal.length = 0;
  registros.mensajes.length = 0;
  registros.mensajes_webview.length = 0;
  respuestas = ['SPEC-999'];
  registros.comandos['sdd.clarify']();
  await hasta(() => registros.mensajes_webview
    .some((m) => m.tipo === 'resultado' && m.codigo !== 0), 40000);
  check('clarify: ID inexistente se ve en el panel',
    registros.mensajes_webview.some((m) => m.tipo === 'resultado' && m.codigo !== 0
      && /SPEC inexistente/.test(String(m.salida))),
    registros.mensajes_webview.map((m) => `${m.tipo}:${m.codigo}`).join(' | '));
  check('clarify: no abre terminal', registros.terminal.length === 0);

  /* 7. Fallo visible */
  registros.mensajes.length = 0;
  registros.canal.length = 0;
  registros.canal_visible = false;
  registros.comandos['sdd.ejecutarEnChat'](['build', 'PLAN-999']);
  await hasta(() => registros.mensajes.length);
  check('fallo: notificación con el mensaje de la CLI',
    registros.mensajes.some((m) => m.tipo === 'error' && /plan inexistente: PLAN-999/.test(m.texto)),
    registros.mensajes.map((m) => m.texto).join(' | '));
  check('fallo: cerrar sin «Ver salida» no abre el canal',
    !registros.canal_visible && registros.canal.length === 0,
    `canal=${registros.canal.length} visible=${registros.canal_visible}`);

  /* 8. Aviso de skills: romper la ruta, refrescar, regenerar con un clic */
  const prompt = path.join(PROYECTO, '.github', 'skills', 'sdd-status', 'SKILL.md');
  const original = fs.readFileSync(prompt, 'utf8');
  fs.writeFileSync(prompt, original.replace(path.join(REPO, 'cli', 'main.py'),
    '/tmp/toolkit-viejo/cli/main.py'));
  registros.providers.sddFases.actualizar();
  await espera(300);
  let nodos = await registros.providers.sddFases.getChildren();
  const aviso = nodos.find((n) => String(n.label).includes('desactualizados'));
  check('aviso: aparece con el total',
    aviso && aviso.label === '⚠️ Comandos de barra desactualizados: 1',
    aviso && aviso.label);
  const hijosAviso = aviso
    ? await registros.providers.sddFases.getChildren(aviso) : [];
  check('aviso: primera fila regenera',
    hijosAviso[0] && hijosAviso[0].label === '↻ Regenerar los comandos'
      && JSON.stringify(hijosAviso[0].command.arguments[0])
        === JSON.stringify(['comandos', '--regenerar']),
    hijosAviso[0] && JSON.stringify(hijosAviso[0].command));
  check('aviso: hijo con la ruta muerta',
    hijosAviso.some((n) => String(n.label).includes('/tmp/toolkit-viejo/cli/main.py')),
    hijosAviso.map((n) => n.label).join(' | '));

  registros.mensajes.length = 0;
  if (hijosAviso[0] && hijosAviso[0].command) {
    await registros.comandos['sdd.ejecutarEnChat'](...hijosAviso[0].command.arguments);
  }
  await hasta(() => registros.mensajes.length);
  check('aviso: confirmación al terminar',
    registros.mensajes.some((m) => m.tipo === 'info'),
    registros.mensajes.map((m) => m.texto).join(' | '));
  nodos = await registros.providers.sddFases.getChildren();
  check('aviso: desaparece tras regenerar',
    !nodos.some((n) => String(n.label).includes('desactualizados')));
  check('aviso: la skill recuperó la ruta buena',
    fs.readFileSync(prompt, 'utf8').includes(path.join(REPO, 'cli', 'main.py')));
  fs.writeFileSync(prompt, original); // dejar el proyecto como estaba

  /* 9. Estado vacío y CLI rota */
  const vacio = path.join(path.dirname(PROYECTO), 'vacio-arnes');
  fs.rmSync(vacio, { recursive: true, force: true });
  fs.mkdirSync(vacio, { recursive: true });
  carpetas = [{ uri: { fsPath: vacio } }];
  registros.providers.sddFases.actualizar();
  await espera(400);
  nodos = await registros.providers.sddFases.getChildren();
  check('vacío: declara y ofrece init',
    nodos.some((n) => String(n.label).includes('sin inicializar'))
      && nodos.some((n) => n.label === 'Inicializar proyecto'),
    textos(nodos).join(' | '));
  fs.rmSync(vacio, { recursive: true, force: true });

  carpetas = [{ uri: { fsPath: PROYECTO } }];
  settings['sddToolkit.python'] = path.join(PROYECTO, 'no-existe-python');
  registros.providers.sddFases.actualizar();
  await espera(600);
  nodos = await registros.providers.sddFases.getChildren();
  check('CLI rota: cae en el estado de error',
    nodos.some((n) => String(n.label).includes('sin inicializar o CLI no disponible')),
    textos(nodos).join(' | '));
  settings['sddToolkit.python'] = PYTHON;

  /* El script del webview viaja dentro de un template literal: una barra
   * invertida suelta se pierde al armar el HTML (`\s` queda como `s`) y el
   * regex deja de servir. Se revisa el HTML ya servido, no el fuente. */
  const chat = require(path.join(REPO, 'ide', 'vscode', 'chat.js'));
  const servido = chat.html({ cspSource: 'vscode-webview:' });
  const inline = (servido.match(/<script nonce="[^"]*">([\s\S]*?)<\/script>/) || [])[1] || '';
  check('webview: el escapado sobrevive al template',
    inline.includes('/[\\s"]/') && inline.includes('clarify\\s+SPEC-\\d+'),
    inline.includes('/[s"]/') ? 'el regex perdió la barra invertida' : '');

  const fallos = resultados.filter((r) => !r.ok).length;
  console.log(`\n== ${resultados.length - fallos}/${resultados.length} comprobaciones en verde ==`);
  process.exit(fallos ? 1 : 0);
})().catch((error) => {
  console.error('ARNÉS ROTO:', error);
  process.exit(2);
});
