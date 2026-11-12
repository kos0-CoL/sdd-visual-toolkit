/* RF-39 — Integración con VS Code (§29). Sin dependencias ni build:
 * paleta con un comando por comando CLI, vista lateral alimentada por
 * `toolkit export` (mismo estado central, §32) y barra de estado con la
 * fase. Sin .specify/ se declara y se ofrece Init; nada se inventa. */
'use strict';

const vscode = require('vscode');
const { execFile, spawn, spawnSync } = require('child_process');
const fs = require('fs');
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
  const minutos = Number(c.get('timeoutMinutos', 5));
  return {
    python: c.get('python', 'python3'),
    cliPath: c.get('cliPath', 'cli/main.py'),
    /* Un valor absurdo en los ajustes no debe dejar sin tope a la paleta. */
    timeoutMinutos: Number.isFinite(minutos) && minutos > 0 ? minutos : 5,
  };
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

/* ¿Este intérprete trae el paquete instalado (`pip install -e .`)? Es lo que
 * permite arrancar en una carpeta vacía, donde la ruta relativa no está. Se
 * prueba una vez por intérprete: cada comprobación costaría un proceso más. */
let cacheModulo = null;
function tieneModulo() {
  const interprete = cfg().python;
  if (cacheModulo && cacheModulo.interprete === interprete) {
    return cacheModulo.sirve;
  }
  let sirve = false;
  try {
    /* `-I`: sin la carpeta actual en `sys.path`, para no confundir un `cli`
     * cualquiera con el del toolkit. */
    const prueba = spawnSync(interprete, ['-I', '-c', 'import cli.main'],
      { timeout: 5000, windowsHide: true });
    sirve = prueba.status === 0;
  } catch (error) {
    sirve = false;
  }
  cacheModulo = { interprete, sirve };
  return sirve;
}

/* Instalado con `uv tool install` o `pipx`, el comando `sdd` resuelve la CLI
 * sin ruta relativa ni intérprete que adivinar. Se busca a mano en el `PATH`
 * para poder mostrarlo tal cual y porque `spawn` de un binario inexistente
 * devuelve un ENOENT que no dice qué falta. */
const BINARIOS = ['sdd', 'toolkit'];
function binarioGlobal() {
  const sufijos = process.platform === 'win32' ? ['.exe', '.cmd', ''] : [''];
  const carpetas = (process.env.PATH || '').split(path.delimiter);
  for (const carpeta of carpetas) {
    if (!carpeta) continue;
    for (const nombre of BINARIOS) {
      for (const sufijo of sufijos) {
        const ruta = path.join(carpeta, nombre + sufijo);
        try {
          if (fs.existsSync(ruta)) return ruta;
        } catch (error) { /* entradas de PATH que no se pueden leer */ }
      }
    }
  }
  return null;
}

/* Argumento que nombra la CLI. La ruta configurada manda; si es relativa y no
 * está en la carpeta —un proyecto todavía sin inicializar— se usa el `sdd`
 * instalado (o el módulo, si alguien hizo `pip install -e .`), que es la misma
 * CLI sin una ruta que adivinar. */
function cli(dir) {
  const { cliPath } = cfg();
  if (path.isAbsolute(cliPath)) {
    return { args: [cliPath], texto: citar(cliPath), existe: true };
  }
  const ruta = path.join(dir, cliPath);
  if (fs.existsSync(ruta)) {
    return { args: [ruta], texto: citar(ruta), existe: true };
  }
  const bin = binarioGlobal();
  if (bin) {
    return { bin, args: [], texto: citar(bin), existe: true };
  }
  if (tieneModulo()) {
    return { args: ['-m', 'cli.main'], texto: '-m cli.main', existe: true };
  }
  return { args: [ruta], texto: citar(ruta), existe: false, ruta };
}

/* Orden completa, para mostrarla y poder copiarla tal cual. */
function comando(dir, argv) {
  const resuelta = cli(dir);
  return [resuelta.bin ? citar(resuelta.bin) : cfg().python, resuelta.texto,
    '--root', citar(dir), ...argv.map(citar)].join(' ');
}

/* «Ver salida» de la notificación y consola de los comandos: la orden exacta
 * con su código y todo lo que imprimió la CLI. Se acumula como un terminal. */
function mostrarSalida(orden, codigo, texto) {
  if (!canal) canal = vscode.window.createOutputChannel('SDD Toolkit');
  canal.appendLine(`$ ${orden}   (${codigo})`);
  canal.appendLine((texto || '').trim() || '(sin salida)');
  canal.appendLine('');
  canal.show(true);
}

/* Un fallo se ve siempre igual: la primera línea en la notificación y el
 * resto detrás de «Ver salida», se haya ejecutado capturado o no. */
function reportarFallo(orden, codigo, stdout, stderr, nombre, motivo = '') {
  const completo = [stdout, stderr].filter(Boolean).join('\n');
  /* `motivo` gana a la salida: en un corte por tiempo lo útil es saber que se
   * cortó, no el fallback de una salida que está vacía. */
  const aviso = motivo || primeraLinea(stdout) || primeraLinea(stderr);
  const mensaje = 'SDD: ' +
    (aviso || `${nombre} falló (código ${codigo || 'error'})`);
  /* Código numérico o etiqueta («tiempo agotado»): el canal no tiene que decir
   * «código tiempo agotado». */
  const etiqueta = typeof codigo === 'number' ? `código ${codigo}` : codigo;
  Promise.resolve(
    vscode.window.showErrorMessage(mensaje, 'Ver salida')
  ).then((elegido) => {
    if (elegido === 'Ver salida') {
      mostrarSalida(orden, etiqueta || 'error', completo);
    }
  });
}

/* Cancelar tiene que alcanzar al árbol completo: `build` lanza `pytest` como
 * subproceso y matar solo al intérprete de la CLI lo dejaba huérfano. En
 * POSIX el hijo abre su propio grupo (`detached`), así que la señal va a
 * `-pid`; en Windows no hay grupos y se corta con `taskkill /T`. */
function matarArbol(hijo) {
  if (!hijo || !hijo.pid) return;
  if (process.platform === 'win32') {
    execFile('taskkill', ['/pid', String(hijo.pid), '/T', '/F'], () => {});
    return;
  }
  try {
    process.kill(-hijo.pid, 'SIGTERM');
  } catch (error) {
    hijo.kill();
  }
}

/* Los comandos rápidos no deben dejar un parpadeo de progreso; a partir de
 * aquí el usuario ya está esperando y necesita saber que algo corre. */
const ESPERA_PROGRESO = 400;

/* La paleta ejecuta capturando la salida: así el código de salida llega al
 * IDE y un fallo se ve como notificación con la salida a un clic, en vez de
 * quedar al fondo de un terminal que nadie mira. */
function correr(dir, argv, opciones = {}) {
  const resuelta = cli(dir);
  if (!resuelta.existe) {
    /* Sin ruta ni paquete, python solo diría «can't open file»: se dice qué
     * ajustar antes de lanzarlo. */
    vscode.window.showErrorMessage(
      `SDD: no encuentro la CLI en ${resuelta.ruta}. Ajuste «sddToolkit.cliPath»` +
      ' a la ruta de cli/main.py o instale el paquete con «pip install -e .».');
    return;
  }
  const orden = comando(dir, argv);
  let terminado = false;
  let cancelado = false;
  let excedido = false;
  let cerrarIndicador = () => {};
  let hijo = null;
  const indicador = setTimeout(() => {
    if (terminado) return;
    vscode.window.withProgress({
      location: vscode.ProgressLocation.Notification,
      title: `SDD: ${argv.join(' ')}`,
      cancellable: true,
    }, (_progreso, token) => {
      token.onCancellationRequested(() => {
        /* SIGTERM, no SIGKILL: el estado JSON se escribe con temporal +
         * renombrado, así que lo que alcance a guardar queda entero. */
        cancelado = true;
        matarArbol(hijo);
      });
      return new Promise((listo) => { cerrarIndicador = listo; });
    });
  }, ESPERA_PROGRESO);
  /* El tope va aquí y no en las opciones de spawn para que corte también a
   * los nietos, igual que la cancelación. Es configurable
   * (`sddToolkit.timeoutMinutos`, 5 por defecto). */
  const minutos = cfg().timeoutMinutos;
  const limite = setTimeout(() => {
    excedido = true;
    matarArbol(hijo);
  }, minutos * 60000);
  const cerrar = () => {
    terminado = true;
    clearTimeout(indicador);
    clearTimeout(limite);
    cerrarIndicador();
  };
  /* `spawn` y no `execFile`: solo el primero respeta `detached` y deja al hijo
   * como líder de su grupo, que es lo que permite alcanzar a los nietos. */
  hijo = spawn(resuelta.bin || cfg().python,
    [...resuelta.args, '--root', dir, ...argv], {
    cwd: dir,
    detached: process.platform !== 'win32',
    windowsHide: true,
  });
  let stdout = '';
  let stderr = '';
  hijo.stdout.on('data', (dato) => { stdout += dato; });
  hijo.stderr.on('data', (dato) => { stderr += dato; });
  hijo.on('error', (error) => {
    if (terminado) return;
    cerrar();
    /* ENOENT suele ser el intérprete: se dice cuál y qué ajustar, porque el
     * mensaje crudo («spawn python3 ENOENT») no lleva a ningún sitio. */
    const detalle = error.code === 'ENOENT'
      ? `no encontré «${resuelta.bin || cfg().python}»: ajuste «sddToolkit.python» ` +
        'o instale el comando con «uv tool install …»'
      : String(error.message || error);
    reportarFallo(orden, 'error', stdout, detalle, argv[0]);
  });
  hijo.on('close', (codigo) => {
    if (terminado) return;
    cerrar();
    const completo = [stdout, stderr].filter(Boolean).join('\n');
    if (cancelado) {
      /* Un corte pedido por el usuario no es un fallo del comando: se dice
       * que se canceló, se deja lo impreso en el canal y se relee el estado
       * real, que puede haber cambiado antes de la señal. */
      mostrarSalida(orden, 'cancelado', completo);
      refrescar();
      vscode.window.showInformationMessage(`SDD: ${argv[0]} cancelado`);
      return;
    }
    if (excedido) {
      reportarFallo(orden, 'tiempo agotado', stdout, stderr, argv[0],
        `${argv[0]} excedió ${minutos} minuto(s) y se cortó`);
      return;
    }
    if (codigo !== 0) {
      reportarFallo(orden, codigo, stdout, stderr, argv[0]);
      return;
    }
    const aviso = primeraLinea(stdout) || primeraLinea(stderr);
    mostrarSalida(orden, 'código 0', completo);
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

/* `clarify` pregunta por stdin, así que corre en el terminal; pero un SPEC-ID
 * inexistente falla antes de preguntar nada y ese ⛔ se perdía al fondo. Se
 * valida con `--list`, que solo lee, y el terminal se abre si pasa. */
function validarYTerminal(dir, argv) {
  const orden = comando(dir, argv);
  if (argv.length < 2) {
    terminal().sendText(orden);
    return;
  }
  const resuelta = cli(dir);
  execFile(resuelta.bin || cfg().python,
    [...resuelta.args, '--root', dir, argv[0], '--list', argv[1]],
    { cwd: dir, timeout: 300000 }, (err, stdout, stderr) => {
      if (!err) {
        terminal().sendText(orden);
        return;
      }
      reportarFallo(orden, err.code, stdout, stderr, argv[0]);
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
    validarYTerminal(dir, argv);
    return;
  }
  /* Regenerar los comandos de barra cambia lo que avisa la vista, así que se
   * refresca al terminar en vez de esperar al intervalo. */
  if (argv[0] === 'comandos') {
    correr(dir, argv, { avisoExito: 'comandos de barra al día', refrescar: true });
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

/* Foto del estado para las vistas (§32): una lectura de `export` por refresco. */
function cargarDoc() {
  return new Promise((resolve) => {
    const dir = carpeta();
    if (!dir) {
      resolve({ doc: null, error: 'sin carpeta abierta' });
      return;
    }
    execFile(cfg().python, [...cli(dir).args, '--root', dir, 'export'],
      { cwd: dir, timeout: 30000 }, (err, stdout) => {
        if (err) {
          resolve({ doc: null, error: 'sin inicializar o CLI no disponible' });
          return;
        }
        try {
          resolve({ doc: JSON.parse(stdout), error: '' });
        } catch (e) {
          resolve({ doc: null, error: 'export no devolvió JSON válido' });
        }
      });
  });
}

/* Símbolos del árbol §21, para que el flujo y el árbol hablen igual. */
const SIMBOLOS = {
  pendiente: '○',
  'en progreso': '●',
  completado: '✔',
  'requiere intervención': '⚠',
  fallido: '✘',
  recuperado: '♻',
};

/* Panel VISUAL del flujo (§29): cada fase con su estado, el artefacto que
 * deja y la skill que la ejecuta; el clic lanza el comando de la fase. */
class VistaFlujo {
  constructor() {
    this._cambio = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._cambio.event;
  }
  actualizar() {
    this._cambio.fire();
  }
  getTreeItem(nodo) {
    return nodo;
  }
  async getChildren() {
    const dir = carpeta();
    const { doc, error } = await cargarDoc();
    if (!doc) {
      const it = new vscode.TreeItem('⛔ ' + error,
        vscode.TreeItemCollapsibleState.None);
      it.command = { command: 'sdd.ejecutar', title: 'Ejecutar', arguments: ['init'] };
      return [it];
    }
    return (doc.flujo || []).map((fila) => {
      const it = new vscode.TreeItem(
        `${SIMBOLOS[fila.estado] || '·'} ${fila.fase}`,
        vscode.TreeItemCollapsibleState.None);
      it.description = fila.estado;
      it.tooltip = [
        fila.skill ? `skill /${fila.skill}` : 'sin skill',
        fila.artefacto || 'sin artefacto',
        fila.artefacto ? 'clic derecho: abrir el artefacto' : '',
      ].filter(Boolean).join(' · ');
      /* El clic normal ejecuta el comando de la fase; el secundario abre el
       * artefacto. `_artefacto` es relativo a la raíz del proyecto. */
      it.contextValue = fila.artefacto ? 'sddFaseConArtefacto' : 'sddFaseSinArtefacto';
      it._artefacto = fila.artefacto || null;
      it._raiz = dir;
      if (fila.comando) {
        it.command = {
          command: 'sdd.ejecutar',
          title: 'Ejecutar',
          arguments: [fila.comando],
        };
      }
      return it;
    });
  }
}

/* Clic secundario en el flujo: abre el artefacto que dejó la fase. Si la fase
 * todavía no lo escribió se dice cuál falta; no se crea nada vacío. */
async function abrirArtefacto(nodo) {
  const relativo = nodo && nodo._artefacto;
  const dir = (nodo && nodo._raiz) || carpeta();
  if (!relativo) {
    vscode.window.showInformationMessage('SDD: esta fase no deja artefacto.');
    return;
  }
  if (!dir) {
    vscode.window.showErrorMessage('SDD: abra una carpeta primero.');
    return;
  }
  const ruta = path.isAbsolute(relativo) ? relativo : path.join(dir, relativo);
  const uri = vscode.Uri.file(ruta);
  let info;
  try {
    info = await vscode.workspace.fs.stat(uri);
  } catch (error) {
    vscode.window.showWarningMessage(
      `SDD: ${relativo} todavía no existe; ejecute la fase primero.`);
    return;
  }
  if (info.type === vscode.FileType.Directory) {
    await vscode.commands.executeCommand('revealInExplorer', uri);
    return;
  }
  if (/\.md$/i.test(ruta)) {
    await vscode.commands.executeCommand('markdown.showPreview', uri);
    return;
  }
  await vscode.commands.executeCommand('vscode.open', uri);
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
    return cargarDoc().then(({ doc, error }) => {
      this.doc = doc;
      this.error = error;
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
    /* El artefacto de cada fase vive en `flujo`: se reutiliza aquí para que el
     * clic derecho abra lo mismo desde las dos vistas. */
    /* `d.fase` llega con su emoji («🧪 Pruebas») y el flujo usa el nombre
     * pelado: se comparan sin marcas, tildes ni mayúsculas para que el clic
     * derecho abra lo mismo desde `📍 Fase` que desde `Árbol de estados`. */
    const sinMarca = (texto) => String(texto || '')
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[^A-Za-z0-9 ]/g, '')
      .replace(/\s+/g, ' ').trim().toLowerCase();
    const artefactos = new Map((d.flujo || [])
      .filter((fila) => fila.artefacto)
      .map((fila) => [sinMarca(fila.fase), fila.artefacto]));
    const conArtefacto = (it, fase) => {
      const relativo = artefactos.get(sinMarca(fase));
      if (!relativo) return it;
      it.contextValue = 'sddFaseConArtefacto';
      it._artefacto = relativo;
      it._raiz = carpeta();
      it.tooltip = [it.tooltip, `clic derecho: ${relativo}`]
        .filter(Boolean).join(' · ');
      return it;
    };
    /* Cada fila lleva su argv: `tasks` pide PLAN-ID (no el SPEC) y `reporte`
     * exige TASK-ID o `--history PLAN-ID`. El ID de pruebas ya viene en la
     * etiqueta; si no está, se muestra el historial del plan. El `export` solo
     * trae `plan_id` a veces, así que se toma también de la navegación, que ya
     * lo nombra («build PLAN-001»). */
    const pistas = [d.plan_id, nav.recomendada]
      .concat((nav.pildoras || []).map((p) => p && p.comando))
      .filter(Boolean).join(' ');
    const planId = (pistas.match(/PLAN-\d+/) || [])[0] || null;
    const tareaDePruebas = (String(d.pruebas || '').match(/\((TASK-\d+)\)/) || [])[1];
    const reportePruebas = tareaDePruebas
      ? `reporte ${tareaDePruebas}`
      : (planId ? `reporte --history ${planId}` : null);
    const raiz = [
      conArtefacto(item(`📍 Fase: ${d.fase}`, 'tablero', 'milestone'), d.fase),
      item(`Progreso: ${d.progreso.hechas}/${d.progreso.total}`,
        planId ? `tasks --list ${planId}` : 'tablero', 'checklist'),
      item(`Tarea actual: ${d.tarea_actual || '—'}`, d.tarea_actual ? `context ${d.tarea_actual}` : 'tablero', 'play'),
      item(`Pruebas: ${d.pruebas}`, reportePruebas || 'tablero', 'beaker'),
    ];
    if (nav.recomendada) {
      raiz.push(item(`➡ Siguiente: ${nav.recomendada}`, nav.recomendada, 'arrow-right'));
    }
    const pills = (nav.pildoras || []).map((p) =>
      item(`${p.bloqueada ? '🔒' : '▫'} ${p.etiqueta}: ${p.comando}`, p.bloqueada ? null : p.comando, p.bloqueada ? 'lock' : 'zap'));
    if (pills.length) raiz.push(grupo('Píldoras', pills));
    const bloqueos = (nav.bloqueos || []).map((b) => item(`⛔ ${b}`, null, 'error'));
    if (bloqueos.length) raiz.push(grupo('Bloqueos', bloqueos));
    /* Aviso de skills desactualizadas: lo calcula la CLI en `export`, así que
     * la vista no lee archivos generados por su cuenta. */
    const avisos = (d.avisos && d.avisos.skills) || { total: 0, rutas: [] };
    if (avisos.total > 0) {
      /* La primera fila arregla: `comandos --regenerar` reescribe solo los
       * clientes ya instalados, con la ruta de la copia en uso. */
      const hijos = [
        item('↻ Regenerar los comandos', ['comandos', '--regenerar'], 'refresh'),
      ].concat((avisos.rutas || []).map((r) =>
        item(`${r.archivos} archivo(s) → ${r.ruta}`, null, 'warning')));
      const nodo = grupo(
        `⚠️ Comandos de barra desactualizados: ${avisos.total}`, hijos);
      nodo.tooltip = 'Clic en «Regenerar los comandos» para reescribirlos con la ruta actual.';
      raiz.unshift(nodo);
    }
    const fases = (d.arbol || []).map((n) => conArtefacto(
      item(`${n.estado === 'completado' ? '✅' : n.estado === 'en progreso' ? '🔄' : '○'} ${n.fase}`, 'arbol', 'circle-outline'),
      n.fase));
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
  /* Menú contextual del panel de flujo. */
  contexto.subscriptions.push(
    vscode.commands.registerCommand('sdd.abrirArtefacto', (nodo) => abrirArtefacto(nodo))
  );
  const vista = new VistaFases();
  const flujo = new VistaFlujo();
  contexto.subscriptions.push(
    vscode.window.registerTreeDataProvider('sddFases', vista),
    vscode.window.registerTreeDataProvider('sddFlujo', flujo),
    vscode.commands.registerCommand('sdd.actualizar', () => {
      vista.actualizar();
      flujo.actualizar();
    })
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
    flujo.actualizar();
    refrescarBarra();
  };
  contexto.subscriptions.push(barra);
  refrescarBarra();
  const intervalo = setInterval(refrescarBarra, 30000);
  contexto.subscriptions.push({ dispose: () => clearInterval(intervalo) });
}

function deactivate() {}

module.exports = { activate, deactivate, COMMANDS };
