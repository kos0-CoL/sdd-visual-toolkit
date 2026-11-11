# Checklist de prueba manual: VS Code y Antigravity

`ide/COMPATIBILIDAD.md` dice qué está verificado hoy: nada dentro de un IDE.
Esto es lo que hay que abrir para pasar cada superficie de «escrito» a
«verificado», en el orden en que conviene probarlo.

## Preparación

Se prueba sobre un proyecto ya inicializado, no sobre uno vacío (para el
estado vacío hay un bloque aparte). El fixture del repo sirve:

```bash
cp -a tests/fixtures/estado-0.1.0 /tmp/sdd-manual
python3 cli/main.py --root /tmp/sdd-manual comandos --cliente copilot
```

Si el toolkit está instalado, `toolkit --root /tmp/sdd-manual comandos …`.
La ruta de `--root` va **antes** del subcomando.

## VS Code — extensión

`ide/vscode/package.json` declara `0.1.5`; usa el `.vsix` de esa release.

- [ ] Instalar: `code --install-extension sdd-visual-toolkit-0.1.5.vsix`.
      Recargar la ventana.
- [ ] Abrir `/tmp/sdd-manual` como carpeta.
- [ ] Ajustar `sddToolkit.cliPath` con la ruta absoluta a `cli/main.py`
      del repo. El valor por defecto es relativa al proyecto y el fixture
      no trae la CLI.
- [ ] Recargar y mirar la barra de estado: el icono, `SDD: <fase>` a la
      izquierda,
      con tooltip «Siguiente: …». Si no aparece, revisar la salida de la
      extensión.
- [ ] Vista `SDD → Fases y tareas`. Con el fixture debe leerse: fase
      `🧪 Pruebas`, `Progreso: 1/18`, `Tarea actual: —`,
      `Pruebas: ✅ P=2 F=0 cob=100% (TASK-001)`,
      `➡ Siguiente: build PLAN-001`, un grupo `Píldoras` con cuatro entradas
      (`Seguir con la próxima tarea`, `Ver reporte`, `Ver diff`, `Ver tareas`)
      sin `🔒`, ningún grupo `Bloqueos`, y nueve fases en `Árbol de estados`
      (cinco completadas; Tareas e Implementación en progreso; Análisis y
      Recuperación pendientes). Cualquier diferencia es un hallazgo.
- [ ] Clic en un nodo con comando: se abre la terminal `SDD Toolkit` y corre
      ese comando. Clic en una píldora bloqueada: no pasa nada.
- [ ] Paleta, comando sin argumentos (`SDD: Estado + siguiente`): corre
      `status` sin preguntar.
- [ ] Paleta, comando con argumento (`SDD: Generar / ver plan`): pide
      `SPEC-ID`; escribir `SPEC-001` lo pasa al final del comando.
- [ ] Comando que pide dos datos (`SDD: Spec pinning`): pregunta `PLAN-ID`,
      después `TASK-ID`, y ejecuta `pin PLAN-001 --task TASK-001`. Cancelar en
      el segundo no ejecuta nada; dejarlo vacío avisa y no ejecuta.
- [ ] Vacío en un comando opcional: `SDD: Generar / ver SPEC` con vacío corre
      `specify --list`; `SDD: Mensaje final de fase` con vacío corre `cierre`.
- [ ] Vacío en un comando que exige ID: aparece
      «SDD: falta el identificador pedido.» y no se ejecuta nada.
- [ ] Cancelar con `Escape` en el cuadro de entrada: no se ejecuta nada.
- [ ] Volver a pulsar `SDD: Actualizar vista lateral` refresca los datos.
- [ ] Estado vacío: abrir una carpeta sin `.specify/` y comprobar que la
      vista muestra `⛔ sin inicializar o CLI no disponible` junto a
      `Inicializar proyecto` (la CLI responde «no hay proyecto toolkit aquí»)
      y que la barra de estado se oculta, en vez de inventar fase.
- [ ] `SDD: Inicializar proyecto` en una carpeta vacía: aparece la
      notificación con la ruta inicializada y la vista deja de mostrar
      `sin inicializar` sin recargar la ventana.
- [ ] `SDD: Inicializar proyecto` con la carpeta abierta dentro de otro
      proyecto (`/tmp/sdd-manual/sub`): notificación de error con
      `YA HAY UN PROYECTO TOOLKIT POR ENCIMA: /tmp/sdd-manual` y ningún
      `.specify/` nuevo en `sub/`.
- [ ] CLI rota: poner `sddToolkit.python` en algo inexistente y comprobar
      que la vista cae en `⛔ sin inicializar o CLI no disponible` y la barra
      se oculta. Restaurar el valor.

## VS Code — comandos de barra

Con el paso de preparación hecho, `.github/prompts/` tiene 14 archivos.

- [ ] Escribir `/sdd` en el chat y comprobar que aparecen los comandos.
- [ ] `/sdd-status`: la salida de la CLI llega tal cual, sin resumen.
- [ ] `/sdd-plan PLAN-001`: el ID se pasa al final del comando.
- [ ] `/sdd-plan` sin ID: lo pide antes de ejecutar; no lo inventa.
- [ ] `/sdd-build PLAN-999`: se detiene y muestra `⛔ plan inexistente:
      PLAN-999` sin rodearlo de otros comandos ni tocar el estado.
- [ ] Comprobar que la ruta de la CLI del archivo generado es la absoluta
      del repo, no `cli/main.py` relativa.

## Antigravity

No hay nada verificado aquí: la extensión puede no instalarse y las skills
pueden no aparecer. Cada casilla se anota con lo que pase, incluido «no
aplica».

```bash
python3 cli/main.py --root /tmp/sdd-manual comandos --cliente antigravity
```

- [ ] Generar y comprobar que quedan 14 skills en `.agents/skills/*/SKILL.md`.
      No se generan *workflows*: ese mecanismo está deprecado.
- [ ] Abrir el proyecto y ver si las skills aparecen en el agente (por nombre
      y descripción) o si hace falta recargar la ventana.
- [ ] Invocar `/sdd-status` o la skill equivalente: ¿ejecuta el comando con
      la ruta absoluta horneada?
- [ ] Comprobar si el agente tiene terminal integrada y permiso de shell, y
      si pide aprobación por comando.
- [ ] Comprobar si la skill se puede invocar a mano (`/sdd-plan`) y si toma el
      ID del pedido. El manifiesto de Antigravity solo documenta `name` y
      `description`, así que `argument-hint` no se muestra.
- [ ] Comprobar si respeta «la salida de la CLI es la fuente de la verdad».
- [ ] Si acepta extensiones de VS Code, intentar instalar el `.vsix` y mirar
      paleta, vista y barra de estado; si no lo acepta, anotar el error.
- [ ] Anotar si `engines.vscode ^1.80.0` es compatible con la versión que
      trae ese entorno.

## Cómo se anota

Una casilla no se marca por haber visto la paleta: cada una necesita su
resultado. Para cada superficie probada, esto se pega en el registro de
`ide/COMPATIBILIDAD.md`:

```
Entorno y versión:   VS Code 1.9x / Antigravity x.y
Superficie:          extensión | comandos de barra
Proyecto:            /tmp/sdd-manual (fixture 0.1.0)
Sistema:             (distro / versión)
Fecha:               2026-11-11
Resultado:           ✅ / ⚠️ / ❌
Fallos:              casilla, comando, mensaje obtenido, mensaje esperado
```

- **✅** exige todas las casillas de esa superficie en verde. Entonces la
  celda de la tabla de estado pasa de `sin probar` a
  `✅ verificado (VS Code 1.9x, 2026-11-11)`.
- **⚠️** es lo que funciona a medias: se anota qué sí y qué no, y la fila
  sigue sin ✅.
- **❌** o «no aplica» se escriben con la razón, nunca con un ✅. Si algo no
  se puede probar porque el entorno no lo ofrece (extensión en Antigravity),
  la degradación es CLI + `export` (§47).
- Un fallo se anota con lo mínimo para reproducirlo: comando, mensaje
  obtenido y esperado. Sin eso no sirve para abrir el arreglo.

## Criterio para cerrar

- **VS Code**: extensión y comandos de barra con todas las casillas. Es el
  único entorno que ya está verificado por pruebas automáticas, así que el
  hallazgo esperado son detalles de UX, no roturas.
- **Antigravity**: skills ejecutando la CLI y degradación documentada. Con
  eso deja de ser «pendiente de verificación» aunque no soporte extensión.
