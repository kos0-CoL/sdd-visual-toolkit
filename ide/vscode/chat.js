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
/* Panel de clarificaciones visuales */
#clarificaciones { padding: 12px; border-top: 1px solid var(--vscode-panel-border); }
.clarif-titulo { font-size: 13px; font-weight: 600; margin: 0 0 8px;
  color: var(--vscode-foreground); }
.clarif-pregunta { margin-bottom: 10px; padding: 10px; border: 1px solid var(--vscode-input-border);
  border-radius: 6px; background: var(--vscode-input-background); }
.clarif-texto { font-size: 13px; margin-bottom: 6px; color: var(--vscode-foreground); }
.clarif-contexto { font-size: 11.5px; color: var(--vscode-descriptionForeground);
  margin-bottom: 8px; font-style: italic; }
.clarif-opciones { display: flex; flex-direction: column; gap: 5px; }
.clarif-opcion { display: flex; align-items: flex-start; gap: 8px; flex-wrap: wrap;
  padding: 6px 10px; border-radius: 4px; cursor: pointer;
  border: 1px solid var(--vscode-input-border);
  background: var(--vscode-input-background); }
.clarif-opcion input { margin-top: 2px; flex-shrink: 0; }
.clarif-opcion:hover { background: var(--vscode-list-hoverBackground); }
.clarif-opcion.seleccionada { background: var(--vscode-list-activeSelectionBackground);
  border-color: var(--vscode-list-activeSelectionForeground); color: var(--vscode-list-activeSelectionForeground); }
.clarif-etiqueta { font-size: 12.5px; font-weight: 500; }
.clarif-descripcion { flex: 1 0 100%; font-size: 11px;
  color: var(--vscode-descriptionForeground);
  margin-top: 3px; margin-left: 22px; line-height: 1.4; }
.clarif-recomendada::after { content: ' ★ (recomendado)';
  font-size: 10.5px; color: var(--vscode-testing-iconPassed); font-weight: 600; margin-left: 6px; }
.clarif-multiple { font-size: 10.5px; color: var(--vscode-descriptionForeground);
  margin-bottom: 6px; font-style: italic; }
.clarif-libre { width: 100%; min-height: 44px; padding: 6px 8px; font-family: inherit;
  font-size: 12.5px; resize: vertical; border-radius: 4px;
  color: var(--vscode-input-foreground); background: var(--vscode-input-background);
  border: 1px solid var(--vscode-input-border, transparent); }
.clarif-botones { display: flex; gap: 8px; margin-top: 12px; padding-top: 10px;
  border-top: 1px solid var(--vscode-input-border); }
button.clarif-aplicar { padding: 6px 14px; font-family: inherit; font-size: 12.5px;
  cursor: pointer; color: var(--vscode-button-foreground, #ffffff);
  background: var(--vscode-button-background, #0e639c); border: none; border-radius: 4px; }
button.clarif-aplicar:disabled { opacity: .5; cursor: default; }
button.clarif-cancelar { padding: 6px 14px; font-family: inherit; font-size: 12.5px;
  cursor: pointer; color: var(--vscode-button-secondaryForeground, var(--vscode-foreground, #ccc));
  background: var(--vscode-button-secondaryBackground, rgba(127,127,127,.18));
  border: 1px solid var(--vscode-panel-border); border-radius: 4px; }
</style>
</head>
<body>
  <header>
    <strong>SDD</strong>
    <span id="contexto">cargando…</span>
  </header>
  <div id="hilo"></div>
  <div id="pildoras"></div>
  <div id="clarificaciones" style="display:none;"></div>
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

  /* Mensaje de error visible dentro del panel (no solo en un canal oculto). */
  function mostrarErrorPanel(mensaje) {
    const aviso = document.createElement('div');
    aviso.className = 'fila sdd error';
    const caja = document.createElement('div');
    caja.className = 'burbuja';
    caja.textContent = mensaje;
    aviso.appendChild(caja);
    hilo.appendChild(aviso);
    hilo.scrollTop = hilo.scrollHeight;
  }

  /* Botón para forzar refresco del estado desde el panel. */
  function agregarBotonRefrescar() {
    const btn = document.createElement('button');
    btn.className = 'pildora';
    btn.textContent = '↻ Refrescar estado';
    btn.title = 'Vuelve a leer el estado del proyecto (toolkit export).';
    btn.addEventListener('click', () => {
      vscode.postMessage({ tipo: 'refrescarEstado' });
    });
    pildoras.appendChild(btn);
  }

  /* Botón para forzar refresco del estado desde el panel. */
  function agregarBotonRefrescar() {
    const btn = document.createElement('button');
    btn.className = 'pildora';
    btn.textContent = '↻ Refrescar estado';
    btn.title = 'Vuelve a leer el estado del proyecto (toolkit export).';
    btn.addEventListener('click', () => {
      vscode.postMessage({ tipo: 'refrescarEstado' });
    });
    pildoras.appendChild(btn);
  }

  function pintarPildoras(doc) {
    pildoras.innerHTML = '';
    const nav = (doc && doc.navegacion) || {};
    const lista = (nav.pildoras || []).filter((p) => p && p.comando);
    if (nav.recomendada && !lista.some((p) => p.comando === nav.recomendada)) {
      lista.unshift({ etiqueta: 'Siguiente paso', comando: nav.recomendada, recomendada: true });
    }
    /* Píldora para actualizar el toolkit: consulta PyPI, pregunta al usuario
     * y aplica solo si acepta. Nunca es automática. */
    lista.push({ etiqueta: 'Actualizar toolkit', comando: 'update', recomendada: false });
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
    /* Si escriben clarify SPEC-001 directamente en el campo, abrir el panel
     * visual de clarificaciones (no tratarlo como idea). */
    if (/^clarify\\s+SPEC-\\d+\\s*$/i.test(valor)) {
      burbuja('yo', valor);
      vscode.postMessage({ tipo: 'orden', comando: valor + ' --panel' });
      texto.value = '';
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

  /* Estado del panel de clarificaciones: qué preguntas hay y qué se seleccionó. */
let clarifPreguntas = [];
let clarifSeleccion = {};  // id de pregunta -> array de valores seleccionados
let clarifSpecId = null;
let clarifCola = [];       // respuestas pendientes de enviar, una por vez
let clarifAplicando = false;  // hay un «Aplicar respuestas» en curso

/* Este script corre aislado del módulo de la extensión: una copia del lado
 * Node no existe aquí. Sin esta función, mostrarClarificaciones lanzaba
 * «escaparHtml is not defined» y el panel quedaba vacío. */
function escaparHtml(texto) {
  return String(texto == null ? '' : texto)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function mostrarClarificaciones(preguntas) {
  clarifPreguntas = preguntas || [];
  clarifSeleccion = {};
  const contenedor = document.getElementById('clarificaciones');
  contenedor.style.display = clarifPreguntas.length ? 'block' : 'none';
  if (!clarifPreguntas.length) return;

  let html = '<div class="clarif-titulo">❓ Clarificaciones pendientes</div>';
  html += '<div class="clarif-multiple">Puedes seleccionar una o más opciones por pregunta. Las marcadas con ★ son recomendadas.</div>';

  for (const p of clarifPreguntas) {
    html += '<div class="clarif-pregunta">';
    html += '<div class="clarif-texto">' + escaparHtml(p.texto) + '</div>';
    if (p.descripcion) {
      html += '<div class="clarif-contexto">' + escaparHtml(p.descripcion) + '</div>';
    }
    if (p.es_multiple) {
      html += '<div class="clarif-multiple">Seleccioná todas las que correspondan.</div>';
    }
    /* Pregunta de texto libre: sin campo no había forma de responderla desde
     * el panel y se quedaba pendiente para siempre. */
    if (!p.opciones.length) {
      const previo = (clarifSeleccion[p.id] || [])[0] || '';
      html += '<textarea class="clarif-libre" data-id="' + escaparHtml(p.id) +
        '" rows="2" placeholder="Escribí la respuesta…">' + escaparHtml(previo) + '</textarea>';
    }
    html += '<div class="clarif-opciones">';
    for (const op of p.opciones) {
      const checked = (clarifSeleccion[p.id] || []).includes(op.valor) ? 'checked' : '';
      const rec = op.recomendada ? 'class="clarif-etiqueta clarif-recomendada"' : 'class="clarif-etiqueta"';
      const tipoInput = p.es_multiple ? 'checkbox' : 'radio';
      const name = p.es_multiple ? ('op_' + p.id) : ('op_' + p.id);
      html += '<div class="clarif-opcion" data-id="' + escaparHtml(p.id) +
        '" data-valor="' + escaparHtml(op.valor) + '">';
      html += '<input type="' + tipoInput + '" name="' + escaparHtml(name) + '" value="' +
        escaparHtml(op.valor) + '" ' + checked + '>';
      html += '<label ' + rec + '>' + escaparHtml(op.etiqueta) + '</label>';
      if (op.descripcion) {
        html += '<div class="clarif-descripcion">' + escaparHtml(op.descripcion) + '</div>';
      }
      html += '</div>';
    }
    html += '</div>'; // clarif-opciones
    html += '</div>'; // clarif-pregunta
  }

  html += '<div class="clarif-botones">';
  html += '<button class="clarif-aplicar" id="clarif-aplicar">Aplicar respuestas</button>';
  html += '<button class="clarif-cancelar" id="clarif-cancelar">Cerrar</button>';
  html += '</div>';

  contenedor.innerHTML = html;

  document.getElementById('clarif-aplicar').addEventListener('click', aplicarClarificaciones);
  document.getElementById('clarif-cancelar').addEventListener('click', () => {
    contenedor.style.display = 'none';
    clarifPreguntas = [];
    clarifSeleccion = {};
  });

  // Texto libre: lo escrito se guarda como la única respuesta de su pregunta.
  contenedor.querySelectorAll('.clarif-libre').forEach((area) => {
    area.addEventListener('input', () => {
      const idPreg = area.dataset.id;
      const valor = area.value.trim();
      clarifSeleccion[idPreg] = valor ? [valor] : [];
    });
  });

  // Recolectar selección al cambiar cualquier input
  contenedor.querySelectorAll('.clarif-opcion input').forEach((input) => {
    input.addEventListener('change', () => {
      const nodo = input.closest('.clarif-opcion');
      const idPreg = nodo.dataset.id;
      const valor = nodo.dataset.valor;
      if (!clarifSeleccion[idPreg]) clarifSeleccion[idPreg] = [];
      const idx = clarifSeleccion[idPreg].indexOf(valor);
      if (input.checked) {
        if (idx < 0) clarifSeleccion[idPreg].push(valor);
      } else {
        if (idx >= 0) clarifSeleccion[idPreg].splice(idx, 1);
      }
      // Si no es múltiple, desmarcar las otras de la misma pregunta
      const p = clarifPreguntas.find((x) => x.id === idPreg);
      if (p && !p.es_multiple) {
        contenedor.querySelectorAll('.clarif-opcion input').forEach((otro) => {
          const n2 = otro.closest('.clarif-opcion');
          if (n2.dataset.id === idPreg && otro !== input) {
            otro.checked = false;
            const id2 = n2.dataset.id;
            const v2 = n2.dataset.valor;
            const i2 = clarifSeleccion[id2] ? clarifSeleccion[id2].indexOf(v2) : -1;
            if (i2 >= 0) clarifSeleccion[id2].splice(i2, 1);
          }
        });
        clarifSeleccion[idPreg] = input.checked ? [valor] : [];
      }
    });
  });
}

function aplicarClarificaciones() {
  const respuestas = [];
  for (const idPreg of Object.keys(clarifSeleccion)) {
    const valores = clarifSeleccion[idPreg];
    if (!valores.length) continue;
    // Construir el comando: clarify SPEC --answer CLA-ID valor1 valor2 ...
    /* Un valor con espacios se manda entre comillas: la CLI recibe una sola
     * respuesta, no una lista de palabras sueltas. */
    const citados = valores.map((v) => (/[\\s"]/.test(v) ? '"' + v.replace(/"/g, '') + '"' : v));
    const comando = 'clarify ' + clarifSpecId + ' --answer ' + idPreg + ' ' + citados.join(' ');
    respuestas.push(comando);
  }
  if (!respuestas.length) {
    alert('Seleccioná al menos una respuesta antes de aplicar.');
    return;
  }
  /* Una por una y esperando cada resultado: mandarlas todas juntas se pisa
   * (cada «clarify --answer» reescribe clarifications.json) y la versión
   * anterior solo enviaba la primera, porque la cola nunca avanzaba. */
  clarifCola = respuestas.slice();
  clarifAplicando = true;
  aplicarSiguiente();
}

/* Envía la próxima respuesta de la cola; al vaciarse, cierra el panel. */
function aplicarSiguiente() {
  if (!clarifCola.length) {
    clarifAplicando = false;
    document.getElementById('clarificaciones').style.display = 'none';
    clarifPreguntas = [];
    clarifSeleccion = {};
    vscode.postMessage({ tipo: 'refrescarEstado' });
    return;
  }
  vscode.postMessage({ tipo: 'orden', comando: clarifCola.shift() });
}

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
      /* Si hay un «Aplicar respuestas» en curso, va la siguiente (o se
       * cierra el panel cuando la cola quedó vacía). */
      if (clarifAplicando) aplicarSiguiente();
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
    if (msg.tipo === 'clarificaciones') {
      /* La CLI devolvió un JSON con las preguntas pendientes para el panel. */
      clarifSpecId = msg.spec_id || '';
      mostrarClarificaciones(msg.preguntas || []);
      burbuja('sdd', 'Tenes ' + (msg.preguntas || []).length +
        ' clarificacion(es) pendiente(s). Seleccioná las respuestas y aplicá.');
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

  /* Sin esta asignación el webview se queda vacío: ni un `<body>`. El panel
   * se abría en negro, el script no corría y nunca llegaba el mensaje
   * «listo», así que las clarificaciones se enviaban a la nada. */
  panel.webview.html = html(panel.webview);

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
    if (mensaje.tipo === 'refrescarEstado') {
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
    /* Si la CLI devolvió un JSON de clarificaciones para el panel, reenviarlo
     * como mensaje 'clarificaciones' en vez de como texto de resultado. */
    if (argv[0] === 'clarify' && salida.trim().startsWith('{')) {
      try {
        const payload = JSON.parse(salida);
        if (payload.comando === 'abrir_panel_clarificaciones') {
          enviar({ tipo: 'clarificaciones', spec_id: payload.spec_id, preguntas: payload.preguntas });
          await refrescar();
          return;
        }
      } catch (e) { /* no es JSON válido: se muestra como resultado normal */ }
    }
    enviar({ tipo: 'resultado', orden, codigo, salida });
    await refrescar();
  });

  return panel;
}

module.exports = { abrir, HUECO, html, partirOrden };
