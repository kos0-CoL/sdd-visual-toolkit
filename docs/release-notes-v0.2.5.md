# SDD Visual Toolkit v0.2.5

Primera versión con la capa visual cerrada de punta a punta: el panel de
clarificaciones se abre dentro del editor y aplica las respuestas sin pasar por
la terminal, `sdd init` deja la extensión instalada o recomendada, y la release
trae el `.vsix` junto al wheel que lo lleva adentro. La versión del paquete
alcanza a la de la extensión, que había avanzado hasta 0.2.5.

Compatible con los proyectos creados con 0.2.1: no cambia el formato de
`.specify/` ni el protocolo MCP.

Cada release adjunta `sdd-visual-toolkit-0.2.5.vsix`, empaquetado con `vsce`
desde el mismo commit que el tag:

```bash
code --install-extension sdd-visual-toolkit-0.2.5.vsix
```

También adjunta el wheel y el sdist. El wheel lleva el `.vsix` en
`share/sdd-toolkit/`, así que `sdd init` puede instalarlo sin bajar nada aparte:

```bash
uv tool install sdd_toolkit-0.2.5-py3-none-any.whl
```

## Añadido

- **`sdd init` deja la extensión lista.** Escribe `.vscode/extensions.json`
  recomendando `sdd-toolkit.sdd-visual-toolkit` —el editor la ofrece al abrir la
  carpeta— y, si el CLI del IDE está en el `PATH` (`code`, `trae`, `cursor`,
  `windsurf`), instala el `.vsix` que viaja en el paquete. Sin CLI queda la
  recomendación y la orden manual; sin terminal no pregunta nada.
- **El panel de clarificaciones se abre solo en el editor.** `sdd clarify
  SPEC-001` con la extensión activa abre un webview con las preguntas (radios,
  casillas y texto libre), la opción recomendada marcada y «Aplicar
  respuestas», que ejecuta las órdenes una por una y refresca el estado.
- **`SDD: Abrir chat`.** Panel de chat propio, con burbujas y píldoras
  clickeables que ejecutan el paso siguiente; las que necesitan un dato lo piden
  antes de correr.
- **La extensión se empaqueta sola en cada release.** El workflow `Release`
  genera el `.vsix` con `vsce`, lo verifica y lo adjunta a la release.
- **La release adjunta el wheel y el sdist**, armados después del `.vsix` para
  que el wheel lo lleve adentro.

## Corregido

- Contestar una pregunta de opciones con la etiqueta («Descartar») o con «no sé»
  caía en la rama por defecto: «Descartar» aceptaba el requisito y «ns» lo
  confirmaba. Ahora las etiquetas y los sinónimos se traducen a su valor, y en
  una contradicción solo «fuera» saca el requerimiento.
- El panel de clarificaciones moría al abrirse (`escaparHtml` no está definido),
  la activación fallaba por un `sdd.update` registrado dos veces y «Aplicar
  respuestas» solo enviaba la primera.
- `scripts/verificar_vsix.py` daba por roto un `.vsix` correcto: `vsce`
  empaqueta `readme.md` en minúsculas y el verificador exigía `README.md`.
- Podar el último elemento de un enriquecimiento dejaba un ENR vacío para
  siempre en `enrich --list`.

## Verificación

- `python3 -m pytest tests/ -q` → 491 passed, 81 subtests passed, sin fallos.
  El arnés headless de la extensión cubre las APIs nuevas del webview
  (`createWebviewPanel`, `ViewColumn`), los avisos de carpeta y de documento
  abierto (`onDidChangeWorkspaceFolders`, `onDidOpenTextDocument`) y el camino
  de `clarify` por el panel: 46 comprobaciones en verde.
- `sdd --version` → `toolkit 0.2.5`; `ide/vscode/package.json` y `pyproject.toml`
  declaran la misma versión.
- Panel verificado dentro de VS Code real (instancia aislada): tres preguntas,
  «Aplicar respuestas» ejecutó las tres órdenes con código 0 y el estado quedó
  aplicado.
- `scripts/empaquetar_extension.py` genera el `.vsix` 0.2.5 y
  `scripts/verificar_vsix.py` lo da por bueno (7 entradas).
- El wheel y el sdist de la release contienen el `.vsix` en
  `share/sdd-toolkit/`.

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.5/CHANGELOG.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.5/docs/RELEASES.md)
- Compatibilidad por entorno: [`ide/COMPATIBILIDAD.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.5/ide/COMPATIBILIDAD.md)
- Checklist de prueba manual: [`ide/PRUEBA-MANUAL.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.5/ide/PRUEBA-MANUAL.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.2.5/CONTRIBUTING.md)
