/* RF-39 — Integración con VS Code (§29). Sin dependencias ni build:
 * paleta con un comando por comando CLI, vista lateral alimentada por
 * `toolkit export` (mismo estado central, §32) y barra de estado con la
 * fase. Sin .specify/ se declara y se ofrece Init; nada se inventa. */
'use strict';

const vscode = require('vscode');
const { execFile } = require('child_process');
const path = require('path');

/* id de paleta, título, CLI y pregunta por el argumento cuando lo exige. */
const COMMANDS = [
  { id: 'sdd.init', cli: 'init' },
  { id: 'sdd.status', cli: 'status' },
  { id: 'sdd.tablero', cli: 'tablero' },
  { id: 'sdd.arbol', cli: 'arbol' },
  { id: 'sdd.siguiente', cli: 'siguiente' },
  { id: 'sdd.cierre', cli: 'cierre', prompt: 'TASK-ID o PLAN-ID (vacío = foto)', opcional: true },
  { id: 'sdd.enrich', cli: 'enrich', prompt: 'Idea a enriquecer' },
  { id: 'sdd.specify', cli: 'specify', prompt: 'ENR-ID (vacío = listar)', opcional: true, siVacio: '--list' },
  { id: 'sdd.clarify', cli: 'clarify', prompt: 'SPEC-ID' },
  { id: 'sdd.investigar', cli: 'investigar' },
  { id: 'sdd.plan', cli: 'plan', prompt: 'SPEC-ID' },
  { id: 'sdd.tasks', cli: 'tasks', prompt: 'PLAN-ID' },
  { id: 'sdd.analyze', cli: 'analyze', prompt: 'PLAN-ID' },
  { id: 'sdd.build', cli: 'build', prompt: 'PLAN-ID' },
  { id: 'sdd.test', cli: 'test', prompt: 'TASK-ID' },
  { id: 'sdd.validate', cli: 'validate', prompt: 'TASK-ID' },
  /* El pin es por tarea: con un solo campo respondía «indique PLAN-ID y
   * --task» desde la paleta. */
  { id: 'sdd.pin', cli: 'pin', prompt: 'PLAN-ID',
    siguiente: { prompt: 'TASK-ID', flag: '--task' } },
  { id: 'sdd.journal', cli: 'journal', prompt: 'PLAN-ID' },
  { id: 'sdd.recover', cli: 'recover', prompt: 'PLAN-ID' },
  { id: 'sdd.checkpoint', cli: 'checkpoint', prompt: 'TASK-ID o PLAN-ID' },
  { id: 'sdd.context', cli: 'context', prompt: 'TASK-ID' },
  { id: 'sdd.flush', cli: 'flush', prompt: 'PLAN-ID' },
  { id: 'sdd.rollback', cli: 'rollback', prompt: 'TASK-ID' },
  { id: 'sdd.ast', cli: 'ast', prompt: 'TASK-ID' },
  { id: 'sdd.reporte', cli: 'reporte', prompt: 'TASK-ID' },
  { id: 'sdd.traza', cli: 'traza', prompt: 'SPEC-ID' },
  { id: 'sdd.historia', cli: 'historia', prompt: 'TASK-ID' },
  { id: 'sdd.restricciones', cli: 'restricciones', prompt: 'SPEC-ID o TASK-ID (vacío = activa)', opcional: true },
  { id: 'sdd.diff', cli: 'diff', prompt: 'TASK-ID' },
  { id: 'sdd.export', cli: 'export' },
];

function cfg() {
  const c = vscode.workspace.getConfiguration('sddToolkit');
  return { python: c.get('python', 'python3'), cliPath: c.get('cliPath', 'cli/main.py') };
}

function carpeta() {
  const f = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  return f ? f.uri.fsPath : null;
}

function terminal() {
  let t = vscode.window.terminals.find((x) => x.name === 'SDD Toolkit');
  if (!t) t = vscode.window.createTerminal('SDD Toolkit');
  t.show();
  return t;
}

/* Lo conecta `activate` para refrescar la vista y la barra tras cambiar el
 * estado fuera del terminal. */
let refrescar = () => {};
/* Canal de salida: hace de consola de la paleta y conserva lo que imprimió
 * la CLI, que ya no corre en un terminal. */
let canal = null;

/* Comandos que preguntan por stdin: solo tienen sentido en un terminal, donde
 * se puede escribir la respuesta. `clarify` sin `--answer` es ese caso. */
const INTERACTIVOS = new Set(['clarify']);

/* La CLI empieza sus avisos con 🟢 o ⛔: en una notificación sobra el símbolo.
 * Van en alternancia y no en una clase: 🟢 está fuera del BMP y una clase sin
 * el flag `u` solo descarta medio par sustituto, dejando un � en el mensaje. */
function primeraLinea(texto) {
  const linea = (texto || '').split('\n').find((l) => l.trim()) || '';
  return linea.replace(/^(?:🟢|⛔)\s*/, '').trim();
}

/* Argumento tal como se escribiría a mano: con comillas si lleva espacios. */
function citar(argumento) {
  return /\s/.test(argumento) ? `"${argumento}"` : argumento;
}

function rutaCli(dir) {
  const { cliPath } = cfg();
  return path.isAbsolute(cliPath) ? cliPath : path.join(dir, cliPath);
}

/* Orden completa, para mostrarla y poder copiarla tal cual. */
function comando(dir, argv) {
  return [cfg().python, citar(rutaCli(dir)), '--root', citar(dir),
    ...argv.map(citar)].join(' ');
}

/* «Ver salida» de la notificación y consola de los comandos: la orden exacta
 * con su código y todo lo que imprimió la CLI. Se acumula como un terminal. */
function mostrarSalida(orden, codigo, texto) {
  if (!canal) canal = vscode.window.createOutputChannel('SDD Toolkit');
  canal.appendLine(`$ ${orden}   (código ${codigo})`);
  canal.appendLine((texto || '').trim() || '(sin salida)');
  canal.appendLine('');
  canal.show(true);
}

/* La paleta ejecuta capturando la salida: así el código de salida llega al
 * IDE y un fallo se ve como notificación con la salida a un clic, en vez de
 * quedar al fondo de un terminal que nadie mira. */
function correr(dir, argv, opciones = {}) {
  const orden = comando(dir, argv);
  execFile(cfg().python, [rutaCli(dir), '--root', dir, ...argv],
    { cwd: dir, timeout: 300000 }, (err, stdout, stderr) => {
      const completo = [stdout, stderr].filter(Boolean).join('\n');
      const aviso = primeraLinea(stdout) || primeraLinea(stderr);
      if (err) {
        const mensaje = 'SDD: ' +
          (aviso || `${argv[0]} falló (código ${err.code || 'error'})`);
        Promise.resolve(
          vscode.window.showErrorMessage(mensaje, 'Ver salida')
        ).then((elegido) => {
          if (elegido === 'Ver salida') {
            mostrarSalida(orden, err.code || 'error', completo);
          }
        });
        return;
      }
      mostrarSalida(orden, 0, completo);
      if (opciones.refrescar) refrescar();
      if (opciones.avisoExito) {
        vscode.window.showInformationMessage(
          'SDD: ' + (aviso || opciones.avisoExito));
      }
    });
}

/* `init` es el único que además confirma con notificación y refresca: crea la
 * estructura y la vista tiene que reflejarlo. */
function inicializar(dir) {
  correr(dir, ['init'], {
    avisoExito: 'proyecto inicializado',
    refrescar: true,
  });
}

/* Acceso a la CLI desde la paleta y desde la vista lateral. `cliArgs` llega
 * como array (texto libre con espacios) o como la orden que trae `export`. */
function ejecutar(cliArgs) {
  const dir = carpeta();
  if (!dir) {
    vscode.window.showErrorMessage('SDD: abra una carpeta primero.');
    return;
  }
  const argv = Array.isArray(cliArgs) ? cliArgs : cliArgs.trim().split(/\s+/);
  if (argv[0] === 'init') {
    inicializar(dir);
    return;
  }
  if (INTERACTIVOS.has(argv[0])) {
    terminal().sendText(comando(dir, argv));
    return;
  }
  correr(dir, argv);
}

/* `null` si se canceló, para distinguirlo de un campo vacío. */
async function pedir(texto) {
  const valor = await vscode.window.showInputBox({ prompt: 'SDD: ' + texto });
  return valor === undefined ? null : (valor || '').trim();
}

async function pedirYCorrer(entrada) {
  if (!entrada.prompt) {
    ejecutar([entrada.cli]);
    return;
  }
  const valor = await pedir(entrada.prompt);
  if (valor === null) return; // cancelado
  if (!valor) {
    if (entrada.opcional) {
      ejecutar(entrada.siVacio
        ? [entrada.cli, entrada.siVacio] : [entrada.cli]);
      return;
    }
    vscode.window.showErrorMessage('SDD: falta el identificador pedido.');
    return;
  }
  /* Array y no cadena: el texto libre de `enrich` lleva espacios. */
  const argv = [entrada.cli, valor];
  if (entrada.siguiente) {
    const extra = await pedir(entrada.siguiente.prompt);
    if (extra === null) return; // cancelado
    if (!extra) {
      vscode.window.showErrorMessage('SDD: falta el identificador pedido.');
      return;
    }
    argv.push(entrada.siguiente.flag, extra);
  }
  ejecutar(argv);
}

/* Vista lateral desde `toolkit export` (contrato RF-38). */
class VistaFases {
  constructor() {
    this._cambio = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._cambio.event;
    this.doc = null;
    this.error = '';
  }
  actualizar() {
    this._cambio.fire();
  }
  cargar() {
    return new Promise((resolve) => {
      const dir = carpeta();
      if (!dir) {
        this.doc = null;
        this.error = 'sin carpeta abierta';
        resolve();
        return;
      }
      const { python, cliPath } = cfg();
      const cli = path.isAbsolute(cliPath) ? cliPath : path.join(dir, cliPath);
      execFile(python, [cli, '--root', dir, 'export'], { cwd: dir, timeout: 30000 }, (err, stdout) => {
        if (err) {
          this.doc = null;
          this.error = 'sin inicializar o CLI no disponible';
        } else {
          try {
            this.doc = JSON.parse(stdout);
            this.error = '';
          } catch (e) {
            this.doc = null;
            this.error = 'export no devolvió JSON válido';
          }
        }
        resolve();
      });
    });
  }
  getTreeItem(nodo) {
    return nodo;
  }
  async getChildren(nodo) {
    await this.cargar();
    const item = (texto, cliArgs, icono) => {
      const it = new vscode.TreeItem(texto, vscode.TreeItemCollapsibleState.None);
      if (cliArgs) {
        it.command = { command: 'sdd.ejecutar', title: 'Ejecutar', arguments: [cliArgs] };
      }
      if (icono) it.iconPath = new vscode.ThemeIcon(icono);
      return it;
    };
    const grupo = (texto, hijos) => {
      const it = new vscode.TreeItem(texto, vscode.TreeItemCollapsibleState.Expanded);
      it._hijos = hijos;
      return it;
    };
    if (nodo && nodo._hijos) return nodo._hijos;
    if (!this.doc) {
      return [item('⛔ ' + this.error, 'init', 'warning'), item('Inicializar proyecto', 'init', 'plus')];
    }
    const d = this.doc;
    const nav = d.navegacion || {};
    const raiz = [
      item(`📍 Fase: ${d.fase}`, 'tablero', 'milestone'),
      item(`Progreso: ${d.progreso.hechas}/${d.progreso.total}`, d.spec_id ? `tasks ${d.spec_id}` : 'tablero', 'checklist'),
      item(`Tarea actual: ${d.tarea_actual || '—'}`, d.tarea_actual ? `context ${d.tarea_actual}` : 'tablero', 'play'),
      item(`Pruebas: ${d.pruebas}`, 'reporte', 'beaker'),
    ];
    if (nav.recomendada) {
      raiz.push(item(`➡ Siguiente: ${nav.recomendada}`, nav.recomendada, 'arrow-right'));
    }
    const pills = (nav.pildoras || []).map((p) =>
      item(`${p.bloqueada ? '🔒' : '▫'} ${p.etiqueta}: ${p.comando}`, p.bloqueada ? null : p.comando, p.bloqueada ? 'lock' : 'zap'));
    if (pills.length) raiz.push(grupo('Píldoras', pills));
    const bloqueos = (nav.bloqueos || []).map((b) => item(`⛔ ${b}`, null, 'error'));
    if (bloqueos.length) raiz.push(grupo('Bloqueos', bloqueos));
    const fases = (d.arbol || []).map((n) => item(`${n.estado === 'completado' ? '✅' : n.estado === 'en progreso' ? '🔄' : '○'} ${n.fase}`, 'arbol', 'circle-outline'));
    if (fases.length) raiz.push(grupo('Árbol de estados', fases));
    return raiz;
  }
}

function activate(contexto) {
  COMMANDS.forEach((entrada) => {
    contexto.subscriptions.push(
      vscode.commands.registerCommand(entrada.id, () => pedirYCorrer(entrada))
    );
  });
  /* Ejecutor genérico para los nodos clicables de la vista lateral. */
  contexto.subscriptions.push(
    vscode.commands.registerCommand('sdd.ejecutar', (cliArgs) => ejecutar(cliArgs))
  );
  const vista = new VistaFases();
  contexto.subscriptions.push(
    vscode.window.registerTreeDataProvider('sddFases', vista),
    vscode.commands.registerCommand('sdd.actualizar', () => vista.actualizar())
  );
  /* Panel de estado: fase actual + siguiente recomendado. */
  const barra = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  barra.command = 'sdd.status';
  const refrescarBarra = async () => {
    await vista.cargar();
    if (vista.doc) {
      barra.text = `$(graph) SDD: ${vista.doc.fase}`;
      barra.tooltip = vista.doc.navegacion.recomendada
        ? `Siguiente: ${vista.doc.navegacion.recomendada}` : 'Ver estado';
      barra.show();
    } else {
      barra.hide();
    }
  };
  refrescar = () => {
    vista.actualizar();
    refrescarBarra();
  };
  contexto.subscriptions.push(barra);
  refrescarBarra();
  const intervalo = setInterval(refrescarBarra, 30000);
  contexto.subscriptions.push({ dispose: () => clearInterval(intervalo) });
}

function deactivate() {}

module.exports = { activate, deactivate, COMMANDS };
