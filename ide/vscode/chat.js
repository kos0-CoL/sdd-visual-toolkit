/* Chat del flujo SDD dentro de VS Code (§29/§32).
 *
 * VS Code deprecó los chat participants para el arnés Copilot, así que no se
 * puede dibujar dentro de *Copilot Chat*. Esto es un panel propio: escribe el
 * usuario, contesta la CLI y las píldoras son botones de verdad. El estado que
 * muestra sale de `export`, igual que las vistas laterales: una sola verdad.
 */
'use strict';

const vscode = require('vscode');

/* Un hueco en una píldora (`enrich «idea»`, `clarify SPEC-001 --answer …`) no
 * se ejecuta tal cual: se completa en el campo de texto. */
const HUECO = /«[^»]*»|…/;

/* Separa una orden respetando las comillas dobles: `clarify SPEC-001 --answer
 * CLA-001 "sí"` son cinco argumentos, no seis. */
function partirOrden(texto) {
  const partes = [];
  let actual = '';
  let comillas = false;
  for (const letra of String(texto || '')) {
    if (letra === '"') { comillas = !comillas; continue; }
    if (!comillas && /\s/.test(letra)) {
      if (actual) partes.push(actual);
      actual = '';
      continue;
    }
    actual += letra;
  }
  if (actual) partes.push(actual);
  return partes;
}

function escapeHtml(texto) {
  return String(texto == null ? '' : texto)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function html(webview) {
  const nonce = String(Date.now()) + Math.random().toString(36).slice(2);
  const csp = `default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';`;
  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0; height: 100vh; display: flex; flex-direction: column;
    font-family: var(--vscode-font-family); color: var(--vscode-foreground);
    background: var(--vscode-editor-background);
  }
  header {
    padding: 8px 12px; border-bottom: 1px solid var(--vscode-panel-border);
    font-size: 12px; color: var(--vscode-descriptionForeground);
    display: flex; gap: 10px; align-items: center;
  }
  header strong { color: var(--vscode-foreground); }
  #hilo { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
  .fila { display: flex; }
  .fila.yo { justify-content: flex-end; }
  .burbuja {
    max-width: 92%; padding: 8px 10px; border-radius: 8px; font-size: 12.5px;
    white-space: pre-wrap; word-break: break-word; line-height: 1.45;
  }
  .yo .burbuja {
    background: var(--vscode-button-background, #0e639c);
    color: var(--vscode-button-foreground, #ffffff);
  }
  .sdd .burbuja {
    background: var(--vscode-textBlockQuote-background, rgba(127,127,127,.12));
    border-left: 3px solid var(--vscode-textLink-foreground);
  }
  .meta { font-size: 11px; color: var(--vscode-descriptionForeground); margin-bottom: 4px; }
  .error .burbuja { border-left-color: var(--vscode-errorForeground); }
  #pildoras { padding: 8px 12px 0; display: flex; flex-wrap: wrap; gap: 6px; }
  button.pildora {
    font-family: inherit; font-size: 12px; padding: 6px 10px; cursor: pointer;
    color: var(--vscode-button-secondaryForeground, var(--vscode-foreground, #ccc));
    background: var(--vscode-button-secondaryBackground, rgba(127,127,127,.18));
    border: 1px solid var(--vscode-panel-border); border-radius: 20px;
  }
  button.pildora:hover { background: var(--vscode-button-secondaryHoverBackground, rgba(127,127,127,.3)); }
  button.pildora.recomendada {
    background: var(--vscode-button-background, #0e639c);
    color: var(--vscode-button-foreground, #ffffff);
    border-color: transparent; font-weight: 600;
  }
  button.pildora.bloqueada { opacity: .55; cursor: not-allowed; }
  footer { padding: 8px 12px 12px; border-top: 1px solid var(--vscode-panel-border); }
  #pista { font-size: 11px; color: var(--vscode-descriptionForeground); margin-bottom: 6px; }
  .entrada { display: flex; gap: 6px; }
  textarea {
    flex: 1; resize: none; height: 62px; padding: 8px; font-family: inherit; font-size: 12.5px;
    color: var(--vscode-input-foreground); background: var(--vscode-input-background);
    border: 1px solid var(--vscode-input-border, transparent); border-radius: 4px;
  }
  button.enviar {
    padding: 0 14px; font-family: inherit; font-size: 12.5px; cursor: pointer;
    color: var(--vscode-button-foreground, #ffffff);
    background: var(--vscode-button-background, #0e639c);
    border: none; border-radius: 4px;
  }
  button.enviar:disabled { opacity: .5; cursor: default; }
</style>
</head>
<body>
  <header>
    <strong>SDD</strong>
    <span id="contexto">cargando…</span>
  </header>
  <div id="hilo"></div>
  <div id="pildoras"></div>
  <footer>
    <div id="pista">Escribí lo que querés hacer o usá las píldoras.</div>
    <div class="entrada">
      <textarea id="texto" placeholder="ej: Quiero un sistema para el kiosco: cargar productos con precio y stock…"></textarea>
      <button class="enviar" id="enviar">Enviar</button>
    </div>
  </footer>
<script nonce="${nonce}">
  const vscode = acquireVsCodeApi();
  const hilo = document.getElementById('hilo');
  const pildoras = document.getElementById('pildoras');
  const contexto = document.getElementById('contexto');
  const pista = document.getElementById('pista');
  const texto = document.getElementById('texto');
  const enviarBoton = document.getElementById('enviar');
  const PLACEHOLDER = 'ej: Quiero un sistema para el kiosco: cargar productos con precio y stock…';
  let ocupado = false;
  /* El hueco de una píldora se completa en el campo: enrich «idea» o
   * clarify SPEC-001 --answer …. Se declara aquí dentro porque este script
   * corre en el webview, aislado del módulo de la extensión. */
  const HUECO = /«[^»]*»|…/;
  let presentado = false;
  /* Modo por defecto: lo que se escribe en el campo es la idea a enriquecer. */
  let modo = { tipo: 'idea' };

  /* Primer mensaje: qué proyecto, en qué fase y qué toca ahora. Sin esto el
   * panel abría vacío y parecía que no había pasado nada. */
  function presentar(doc) {
    if (presentado || !doc) return;
    presentado = true;
    const progreso = doc.progreso || {};
    const lineas = [
      'Proyecto: ' + (doc.proyecto || '—'),
      (doc.spec_id ? doc.spec_id + ' (' + doc.spec_status + ')' : 'Todavía sin SPEC'),
      'Fase: ' + (doc.fase || '—'),
      'Progreso: ' + (progreso.hechas || 0) + '/' + (progreso.total || 0),
    ];
    const nav = doc.navegacion || {};
    if (nav.recomendada) lineas.push('', 'Siguiente: ' + nav.recomendada);
    if (doc.proxima) lineas.push('Por qué: ' + doc.proxima);
    const bloqueos = nav.bloqueos || [];
    if (bloqueos.length) lineas.push('', ...bloqueos.map((b) => '⛔ ' + b));
    lineas.push('', 'Escribí tu idea abajo, o elegí una píldora.');
    burbuja('sdd', lineas.join(String.fromCharCode(10)));
  }

  function burbuja(quien, contenido, opciones) {
    const fila = document.createElement('div');
    fila.className = 'fila ' + quien + (opciones && opciones.error ? ' error' : '');
    const caja = document.createElement('div');
    caja.className = 'burbuja';
    if (opciones && opciones.meta) {
      const meta = document.createElement('div');
      meta.className = 'meta';
      meta.textContent = opciones.meta;
      caja.appendChild(meta);
    }
    caja.appendChild(document.createTextNode(contenido));
    fila.appendChild(caja);
    hilo.appendChild(fila);
    hilo.scrollTop = hilo.scrollHeight;
  }

  function pintarPildoras(doc) {
    pildoras.innerHTML = '';
    const nav = (doc && doc.navegacion) || {};
    const lista = (nav.pildoras || []).filter((p) => p && p.comando);
    if (nav.recomendada && !lista.some((p) => p.comando === nav.recomendada)) {
      lista.unshift({ etiqueta: 'Siguiente paso', comando: nav.recomendada, recomendada: true });
    }
    for (const p of lista) {
      const boton = document.createElement('button');
      boton.className = 'pildora'
        + (p.recomendada ? ' recomendada' : '')
        + (p.bloqueada ? ' bloqueada' : '');
      boton.textContent = (p.recomendada ? '★ ' : '') + (p.etiqueta || p.comando);
      boton.title = p.comando + (p.motivo ? ' — ' + p.motivo : '');
      if (p.bloqueada) {
        boton.disabled = true;
      } else {
        boton.addEventListener('click', () => usarPildora(p.comando, p.etiqueta));
      }
      pildoras.appendChild(boton);
    }
  }

  function usarPildora(comando, etiqueta) {
    if (ocupado) return;
    if (HUECO.test(comando)) {
      modo = { tipo: 'orden', base: comando.replace(HUECO, '').trim() };
      pista.textContent = 'Completá: ' + (etiqueta || comando);
      texto.value = '';
      texto.placeholder = etiqueta || comando;
      texto.focus();
      return;
    }
    enviarOrden(comando);
  }

  function enviarOrden(comando) {
    if (ocupado) return;
    burbuja('yo', comando);
    vscode.postMessage({ tipo: 'orden', comando });
  }

  function enviar() {
    const valor = texto.value.trim();
    if (!valor || ocupado) return;
    if (modo.tipo === 'orden') {
      const comando = (modo.base + ' ' + valor).trim();
      texto.value = '';
      texto.placeholder = PLACEHOLDER;
      modo = { tipo: 'idea' };
      pista.textContent = 'Escribí lo que querés hacer o usá las píldoras.';
      enviarOrden(comando);
      return;
    }
    burbuja('yo', valor);
    vscode.postMessage({ tipo: 'idea', texto: valor });
    texto.value = '';
  }

  enviarBoton.addEventListener('click', enviar);
  texto.addEventListener('keydown', (evento) => {
    if (evento.key === 'Enter' && !evento.shiftKey) {
      evento.preventDefault();
      enviar();
    }
  });

  window.addEventListener('message', (evento) => {
    const msg = evento.data || {};
    if (msg.tipo === 'estado') {
      const doc = msg.doc;
      if (doc) {
        contexto.textContent = [
          doc.proyecto || '—',
          doc.spec_id ? doc.spec_id + ' ' + doc.spec_status : 'sin SPEC',
          'fase ' + (doc.fase || '—'),
          'progreso ' + ((doc.progreso && doc.progreso.hechas) || 0)
            + '/' + ((doc.progreso && doc.progreso.total) || 0),
        ].join(' · ');
        pintarPildoras(doc);
        presentar(doc);
      } else {
        contexto.textContent = msg.error || 'sin inicializar';
        pintarPildoras(null);
      }
      return;
    }
    if (msg.tipo === 'resultado') {
      ocupado = false;
      enviarBoton.disabled = false;
      const salida = (msg.salida || '').trim() || '(sin salida)';
      burbuja('sdd', salida, {
        meta: '$ ' + msg.orden + '   (código ' + msg.codigo + ')',
        error: msg.codigo !== 0,
      });
      return;
    }
    if (msg.tipo === 'corriendo') {
      ocupado = true;
      enviarBoton.disabled = true;
      burbuja('sdd', 'ejecutando ' + msg.orden + '…');
      return;
    }
    if (msg.tipo === 'ordenDesdePanel') {
      /* Una orden que vino del panel integrado (fase, tarea, píldora).
       * Se muestra como burbuja de usuario y se ejecuta igual que si la
       * hubiera escrito el usuario. */
      const comando = msg.comando || '';
      burbuja('yo', comando);
      vscode.postMessage({ tipo: 'orden', comando });
      return;
    }
  });

  vscode.postMessage({ tipo: 'listo' });
</script>
</body>
</html>`;
}

/* Abre el panel. Recibe las piezas que ya resuelve `extension.js` para no
 * duplicar la búsqueda de la CLI ni el `export`. */
function abrir({ ejecutar, exportar, proyecto }) {
  const panel = vscode.window.createWebviewPanel(
    'sddChat', 'SDD Chat', vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true });

  const enviar = (mensaje) => panel.webview.postMessage(mensaje);

  async function refrescar() {
    const { doc, error } = await exportar();
    enviar({ tipo: 'estado', doc, error });
  }

  panel.webview.onDidReceiveMessage(async (mensaje) => {
    if (!mensaje) return;
    if (mensaje.tipo === 'listo') {
      await refrescar();
      return;
    }
    let argv = null;
    let orden = '';
    if (mensaje.tipo === 'idea') {
      orden = 'enrich «' + mensaje.texto + '»';
      argv = ['enrich', mensaje.texto];
    } else if (mensaje.tipo === 'orden') {
      orden = mensaje.comando;
      argv = partirOrden(orden);
    }
    if (!argv || !argv[0]) return;
    if (HUECO.test(orden)) {
      enviar({ tipo: 'resultado', orden, codigo: 1,
        salida: 'Esta orden necesita un dato: completala en el campo de abajo.' });
      return;
    }
    enviar({ tipo: 'corriendo', orden });
    const { codigo, salida } = await ejecutar(argv);
    enviar({ tipo: 'resultado', orden, codigo, salida });
    await refrescar();
  });

  return panel;
}

module.exports = { abrir, HUECO, html, partirOrden };
