# Checklist de prueba manual: VS Code y Antigravity

`ide/COMPATIBILIDAD.md` dice qué está verificado hoy: nada dentro de un IDE.
Esto es lo que hay que abrir para pasar cada superficie de «escrito» a
«verificado», en el orden en que conviene probarlo.

## Estado de esta lista (2026-11-11)

**Ninguna casilla está marcada: no se ejecutó nada en un editor real.** Las
pruebas automáticas cubren la estructura de lo que el editor carga y —con el
arnés de `tests/js/arnes_extension.js`— los caminos del código contra un
proyecto real, y eso no convierte ninguna superficie en verificada (§47): sigue
haciendo falta ver el editor. Una casilla se marca solo
después de dejar su registro en `ide/COMPATIBILIDAD.md` según «Cómo se anota».

| Bloque | Qué cubren los tests (no es prueba de editor) | En editor real |
|---|---|---|
| VS Code — extensión | `tests/test_ide.py` (manifiesto, paleta, vistas, canal, cancelación, tope, clic derecho) · `tests/test_extension_headless.py` y `tests/js/arnes_extension.js` (el `extension.js` con un stub de `vscode` contra un proyecto real) · `tests/test_cli_init.py::TestInitDejaElIDEListo` (`.vscode/settings.json` y `tasks.json`) · `tests/test_export.py` (contrato del que lee la vista) | sin probar |
| VS Code — comandos de barra | `tests/test_agent_commands.py` (los catorce, formato por cliente y ruta absoluta en el cuerpo) | sin probar |
| Antigravity | lo anterior, más `tests/test_compatibilidad_formato.py` y la matriz de la extensión | sin probar |

La pasada del 2026-11-11 se hizo **sin editor** (arnés headless, 41/41 en
verde): no habilita ninguna casilla. El detalle de lo cubierto y de lo que
falta está en `ide/COMPATIBILIDAD.md`.

Ese mismo día hubo una segunda pasada **dentro del editor**, sobre una instancia
con perfil aislado. Se marcaron ocho casillas de la superficie extensión —barra
de estado con su tooltip, vista `Fases y tareas`, vista `Flujo SDD` con tooltip,
clic derecho que abre `PLAN-001.md` en vista previa, paleta `SDD: Estado +
siguiente` y el fallo de `build PLAN-999`—, más el clic derecho en el flujo
(`Arquitectura` → `PLAN-001.md`, `Especificación` → `SPEC-001.md`) y en
`📍 Fase`, que **no aparecía** y quedó arreglado en esa misma pasada. Una
tercera pasada comprobó el progreso y su «Cancelar» —dos casillas más— y una
cuarta midió el tope `timeoutMinutos`, una quinta el `pin` de dos datos, el
vacío obligatorio y `Escape`, y una sexta el estado vacío y la CLI rota:
diecisiete en total. El resto sigue sin marcar: el «Cancelar» con `pytest` en marcha, las dos de `SDD: Inicializar
proyecto` y todas las de comandos de barra (no hay sesión de Copilot en ese
perfil).

Ojo con el estado: ejecutar comandos lo mueve. Tras `build`, la tarea actual
deja de ser `—` y las píldoras cambian; para repetir la lista desde la línea
base hace falta `scripts/preparar-manual.sh --force`.

Eso se vio al arrancar la pasada siguiente: `--solo-verificar` devolvió
`⛔ arnés FAIL vista: tarea actual vacía` sobre el proyecto que la pasada en
editor había dejado en `TASK-002`. Tras `--force`, la tabla volvió a dar seis
`✓`, un `☐` y cero `⛔`. El orden del bloque de arriba sale de ahí.

## Preparación

Se prueba sobre un proyecto ya inicializado, no sobre uno vacío (para el
estado vacío hay un bloque aparte). Un solo comando deja el proyecto, los
ajustes, las skills y el `.vsix`:

```bash
scripts/preparar-manual.sh                         # /tmp/sdd-manual y /tmp/sdd-manual-vsix
scripts/preparar-manual.sh --instalar              # y además instala el .vsix
scripts/preparar-manual.sh --destino /tmp/x --sin-vsix
scripts/preparar-manual.sh --solo-verificar        # solo mira: tabla de resultados
```

Hace lo que antes se copiaba a mano: copia el fixture
`tests/fixtures/estado-0.1.0`, escribe `.vscode/settings.json` con
`sddToolkit.python` y la ruta absoluta a `cli/main.py`, restaura
`src/productos.py` desde el snapshot 0 (lo que compara `validate`), genera los
14 comandos de copilot y comprueba con `toolkit comandos --verificar` que sus
rutas existen. Además materializa los `.md` que el fixture de 0.1.0 no trae
—plan, tareas e informe— para poder probar el clic derecho, sin mover el estado. Sin `--sin-vsix` empaqueta además
`sdd-visual-toolkit-<versión>.vsix`, falla si `vsce` deja algún `WARNING` y
comprueba con `scripts/verificar_vsix.py` que el paquete lleve la extensión, el
manifiesto, el `readme.md` y la licencia, sin archivos vacíos ni sobrantes; si
el destino ya existe se niega a borrarlo salvo con `--force`. Con `--instalar` corre
`code --install-extension <vsix> --force` al terminar (necesita empaquetar, así
que no se combina con `--sin-vsix`).

La ruta de `--root` va **antes** del subcomando cuando se corre a mano.

### Cada pasada, en este orden

```bash
scripts/preparar-manual.sh --force            # línea base, si la anterior ejecutó algo
scripts/preparar-manual.sh --solo-verificar   # ¿sirve lo que ya hay?
```

1. Un `⛔` en la tabla se arregla antes de abrir el editor: es un entorno roto,
   no una casilla pendiente. El comando sale con código 1 también cuando solo
   queda un `☐`: lo pendiente de editor cuenta como fallo de salida, aunque en
   la tabla se distinga. En la fila del arnés hay una excepción conocida:
   si la pasada anterior ejecutó comandos, el proyecto ya no está en la línea
   base y el arnés falla con `FAIL vista: tarea actual vacía` (espera
   `Tarea actual: —`). Eso es estado movido, no una extensión rota: `--force`
   lo devuelve a la línea base y la tabla vuelve a verde.
2. Los `✓` son hechos comprobados en archivos y CLI; no autorizan a marcar una
   casilla.
3. Los `☐` son lo que falta mirar; el arnés sale siempre así, porque el editor
   no lo vio.
4. Al recorrer una casilla se marca en este archivo y se deja su línea en
   `ide/COMPATIBILIDAD.md`. La tabla no marca casillas por sí sola.

## VS Code — extensión

`ide/vscode/package.json` declara `0.1.5`; sirve el `.vsix` de esa release o el
que arma `scripts/preparar-manual.sh`, que sale de la copia actual del repo.

- [x] Instalar: `code --install-extension sdd-visual-toolkit-0.1.5.vsix`.
      Recargar la ventana. *(2026-11-11: instalada en un perfil aislado; el
      registro de la extensión muestra `onStartupFinished`.)*
- [x] Abrir `/tmp/sdd-manual` como carpeta. *(2026-11-11: título de la ventana
      `sdd-manual`.)*
- [ ] Ajustar `sddToolkit.cliPath` con la ruta absoluta a `cli/main.py`
      del repo. El valor por defecto es relativa al proyecto y el fixture
      no trae la CLI.
- [x] Recargar y mirar la barra de estado: el icono, `SDD: <fase>` a la
      izquierda,
      con tooltip «Siguiente: …». Si no aparece, revisar la salida de la
      extensión.
- [x] Vista `SDD → Fases y tareas`. Con el fixture debe leerse: fase
      `🧪 Pruebas`, `Progreso: 1/18`, `Tarea actual: —`,
      `Pruebas: ✅ P=2 F=0 cob=100% (TASK-001)`,
      `➡ Siguiente: build PLAN-001`, un grupo `Píldoras` con cuatro entradas
      (`Seguir con la próxima tarea`, `Ver reporte`, `Ver diff`, `Ver tareas`)
      sin `🔒`, ningún grupo `Bloqueos`, y nueve fases en `Árbol de estados`
      (cinco completadas; Tareas e Implementación en progreso; Análisis y
      Recuperación pendientes). Cualquier diferencia es un hallazgo.
- [ ] Clic en un nodo con comando: corre ese comando y su salida aparece en
      el canal `SDD Toolkit`. Clic en una píldora bloqueada: no pasa nada.
- [x] Fallo visible: `SDD: Implementar (build)` con `PLAN-999` muestra una
      notificación de error con `plan inexistente: PLAN-999`; su botón `Ver
      salida` abre el canal con la orden, el código y la salida completa.
      Cerrar la notificación sin pulsarlo no abre el canal.
- [x] Comando largo (`SDD: Correr pruebas` con `TASK-001`, o cualquiera que
      tarde más de medio segundo): aparece una notificación de progreso con
      la orden en curso y desaparece al terminar. Los rápidos no la muestran.
      *Visto*: `SDD: tablero` mostró el progreso con su orden y desapareció con
      `(código 0)` en el canal; los clics rápidos solo escribieron ahí.
- [x] Cancelar: pulsar «Cancelar» en ese progreso. Aparece `SDD: <comando>
      cancelado`, el canal guarda lo que alcanzó a imprimir con
      `(cancelado)` y la vista se refresca; **no** sale notificación de error.
      *Visto* con `SDD: Correr pruebas` y `TASK-001`: el botón dice «Cancel»
      con la IU en inglés; al pulsarlo salieron `SDD: test cancelado`, la línea
      `(cancelado)` en el canal y ninguna notificación de error, y la vista se
      refrescó sola.
- [ ] Cancelar un `SDD: Correr pruebas` que tenga `pytest` en marcha: al
      cancelar, el subproceso también desaparece (comprobar en el gestor de
      procesos del sistema, no solo que la notificación se cierre).
- [x] Tope configurable: poner `sddToolkit.timeoutMinutos` en 1 y lanzar un
      comando que tarde más. A ~1 minuto se corta con `tiempo agotado` en el
      canal y la notificación de error con «Ver salida»; el proceso y sus
      hijos desaparecen. Volver a 5 al terminar.
      *Visto*: `SDD: Correr pruebas` con `TASK-001` sobre un `pytest` de 90 s;
      al minuto salió `SDD: test excedió 1 minuto(s) y se cortó` con `Ver
      salida`, el clic en ese botón dejó `(tiempo agotado)` en el canal y ni el
      `pytest` ni la CLI quedaron vivos.
- [ ] Abrir un proyecto recién inicializado (`python3 cli/main.py --root
      /tmp/sdd-init init`) en VS Code: la vista `SDD → Fases y tareas`
      funciona sin configurar `cliPath` (lo dejó `.vscode/settings.json`) y
      *Terminal → Ejecutar tarea* lista las tareas `SDD: …`.
- [x] Vista `SDD → Flujo SDD`: nueve fases en orden, cada una con su estado
      a la derecha y, al pasar el mouse, la skill (`skill /sdd-plan`) y el
      artefacto. En un proyecto con SPEC, la fila Especificación muestra
      `specs/SPEC-001.md`, y un clic en Aclaraciones ejecuta `clarify
      SPEC-001`. En un proyecto vacío, las filas sin ID no ofrecen clic.
- [x] Clic derecho en una fase del `Flujo SDD` con artefacto: *Abrir artefacto
      de la fase* abre `specs/SPEC-001.md` en vista previa, los `.md` de
      `Arquitectura` (`.specify/planes/PLAN-001.md`), `Tareas`
      (`.specify/tareas/TASKS-PLAN-001.md`) y `Análisis`
      (`.specify/informes/INFORME-PLAN-001.md`), los JSON de `Enriquecimiento`,
      `Aclaraciones`, `Implementación` y `Pruebas` en su archivo, y
      `Recuperación` revela `.specify/checkpoints` en el explorador.
      En una fase sin ejecutar, la notificación dice qué ruta falta y no abre
      nada.

      **El fixture de 0.1.0 solo trae `.specify/planes/PLAN-001.json` y
      `.specify/tareas/TASKS-PLAN-001.json`**, y no tiene
      `.specify/informes/`. La preparación materializa los tres `.md`
      (`scripts/materializar_md.py` reescribe plan y tareas con los
      renderizadores de la CLI y `analyze PLAN-001` crea el informe) sin mover
      el estado: sigue en `1/18` y `🧪 Pruebas`. Si se salta ese paso,
      `Arquitectura`, `Tareas` y `Análisis` aparecen sin artefacto.
- [x] Clic derecho en `SDD → Fases y tareas`: sobre `📍 Fase: …` y sobre la
      fila de esa misma fase en *Árbol de estados* aparece *Abrir artefacto de
      la fase* y abre el mismo archivo que desde el flujo; en las fases sin
      artefacto no aparece.
- [ ] Aviso de skills desactualizadas: reescribir la ruta horneada de un
      archivo de `.github/prompts/` a `/tmp/toolkit-viejo/cli/main.py`,
      recargar y comprobar que `Fases y tareas` abre con
      `⚠️ Comandos de barra desactualizados: 1` y que el hijo dice cuántos
      archivos apuntan a esa ruta. Hacer clic en `↻ Regenerar los comandos`
      y comprobar que la notificación muestra la primera línea de la CLI
      —`SDD: 🧩 copilot: 14 comando(s) en .github/prompts/{nombre}.prompt.md`,
      no un texto propio de la extensión—, que la vista se refresca sin el
      aviso y que el archivo recuperó la ruta buena.
- [ ] `SDD: Aclarar SPEC` con `SPEC-001` se abre en la terminal `SDD
      Toolkit`, porque pregunta por stdin.
- [ ] `SDD: Aclarar SPEC` con `SPEC-999`: la validación previa falla, aparece
      la notificación `SPEC inexistente: SPEC-999` y **no** se abre el
      terminal; `Ver salida` muestra la salida de `clarify --list SPEC-999`.
- [ ] Paleta, comando sin argumentos (`SDD: Estado + siguiente`): corre
      `status` sin preguntar.
- [ ] Paleta, comando con argumento (`SDD: Generar / ver plan`): pide
      `SPEC-ID`; escribir `SPEC-001` lo pasa al final del comando.
- [x] Comando que pide dos datos (`SDD: Spec pinning`): pregunta `PLAN-ID`,
      después `TASK-ID`, y ejecuta `pin PLAN-001 --task TASK-001`. Cancelar en
      el segundo no ejecuta nada; dejarlo vacío avisa y no ejecuta.
      *Visto*: los dos cuadros piden `SDD: PLAN-ID` y `SDD: TASK-ID`, la
      corrida deja `pin PLAN-001 --task TASK-001 (código 0)` en el canal, con
      `Escape` en el segundo no se suma ninguna línea y el vacío tampoco
      ejecuta.
- [x] Vacío en un comando opcional: `SDD: Generar / ver SPEC` con vacío corre
      `specify --list`; `SDD: Mensaje final de fase` con vacío corre `cierre`.
      *Visto*: los cuadros avisan `SDD: ENR-ID (vacío = listar)` y
      `SDD: TASK-ID o PLAN-ID (vacío = foto)`; el canal registró
      `specify --list   (código 0)` y `cierre   (código 0)`, el segundo con
      «Foto actual sin cerrar una fase concreta: use `cierre TASK-ID` o
      `cierre PLAN-ID`».
- [x] Vacío en un comando que exige ID: aparece
      «SDD: falta el identificador pedido.» y no se ejecuta nada.
      *Visto* en el segundo cuadro de `SDD: Spec pinning`: el aviso sale y el
      canal no suma líneas. El primer cuadro de un comando de un solo dato
      sigue sin observar.
- [x] Cancelar con `Escape` en el cuadro de entrada: no se ejecuta nada.
      *Visto*: el cuadro se cierra, el canal no suma líneas y no aparece
      ninguna notificación.
- [ ] Volver a pulsar `SDD: Actualizar vista lateral` refresca los datos.
- [x] Estado vacío: abrir una carpeta sin `.specify/` y comprobar que la
      vista muestra `⛔ sin inicializar o CLI no disponible` junto a
      `Inicializar proyecto` (la CLI responde «no hay proyecto toolkit aquí»)
      y que la barra de estado se oculta, en vez de inventar fase.
      *Visto* en `/tmp/sdd-vacio`: la vista muestra esa fila y `Inicializar
      proyecto`, la CLI responde `⛔ no hay proyecto toolkit aquí (falta
      .specify/); ejecute toolkit init` con código 1, y la barra no tiene
      ningún elemento `SDD: …`. **Hallazgo**: con el perfil recién abierto en
      esa carpeta la extensión no se activó —no había vista SDD— hasta abrir
      la ventana con `--disable-workspace-trust`; el modo restringido la deja
      fuera.
- [ ] `SDD: Inicializar proyecto` en una carpeta vacía: aparece la
      notificación con la ruta inicializada y la vista deja de mostrar
      `sin inicializar` sin recargar la ventana.
- [ ] `SDD: Inicializar proyecto` con la carpeta abierta dentro de otro
      proyecto (`/tmp/sdd-manual/sub`): notificación de error con
      `YA HAY UN PROYECTO TOOLKIT POR ENCIMA: /tmp/sdd-manual` y ningún
      `.specify/` nuevo en `sub/`. El botón `Ver salida` abre el canal
      `SDD Toolkit` con la orden, el código y lo que imprimió la CLI;
      cerrar la notificación sin pulsarlo no abre nada.
- [x] CLI rota: poner `sddToolkit.python` en algo inexistente y comprobar
      que la vista cae en `⛔ sin inicializar o CLI no disponible` y la barra
      se oculta. Restaurar el valor.
      *Visto* con `/no/existe/python3`: la vista cae en esa fila con
      `Inicializar proyecto` y la barra no muestra `SDD: …`; el valor quedó
      restaurado.

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
