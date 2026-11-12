# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado [SemVer](https://semver.org/lang/es/).

## [No publicado]

### Añadido

- El cliente `copilot` escribe `.github/skills/<nombre>/SKILL.md`. En VS Code
  1.142 una skill la listan los dos arneses del chat: `Copilot`, el que trae
  por defecto, y `Local`, en retirada para febrero de 2027.

### Cambiado

- `copilot` ya no escribe `.github/prompts/<nombre>.prompt.md`. Con las dos
  formas el menú `/` del chat de VS Code listaba cada comando dos veces, una
  por el prompt y otra por la skill, y el prompt file solo lo veía el arnés
  `Local`. Esa carpeta se puede borrar de los proyectos que la tengan.

### Corregido

- Las skills generadas piden el dato antes de ejecutar. El cuerpo decía «si
  falta un identificador, pídelo antes de ejecutar», pero el agente lanzaba
  `plan` a secas y dejaba que la CLI contestara «indique la SPEC-ID». Ahora el
  primer punto de las reglas nombra el dato del comando
  (`**Antes de ejecutar**: este comando necesita la SPEC-ID…`) y aclara que el
  ⛔ de la CLI no sustituye a la pregunta.

## [0.1.6] — 2026-11-12

### Corregido

- Dos filas de `Fases y tareas` ejecutaban un comando que no podía funcionar:
  `Progreso` pasaba el SPEC-ID a `tasks` (que pide PLAN-ID) y `Pruebas` llamado
  `reporte` sin argumento. Ahora son `tasks --list PLAN-001` y
  `reporte TASK-001` (o `--history PLAN-001` si la etiqueta no trae tarea).
- El arnés comprueba el argv de esas filas, no solo su etiqueta: era el hueco
  por el que pasaron los dos fallos.
- El clic derecho sobre `📍 Fase` en `Fases y tareas` no ofrecía *Abrir
  artefacto de la fase*: la fila compara `🧪 Pruebas` contra las claves de
  `flujo` (`Pruebas`) y no encontraba el artefacto. Ahora compara sin emoji,
  tildes ni mayúsculas, y el arnés exige que esa fila traiga `contextValue`,
  `_artefacto` y el aviso en el tooltip (43 comprobaciones).
- `init` tampoco deja un `current_task.json` ni un `execution_history.jsonl`
  en `.specify/`: el journal escribe el estado y el historial en
  `.specify/memory/`, así que la copia de la raíz nunca se actualizaba. El
  flujo del IDE apunta al historial real (`memory/execution_history.jsonl`).
- `init` ya no deja `plans/` ni `tasks/` en la raíz: nadie escribía ahí,
  porque `plan`, `tasks` y `analyze` guardan bajo `.specify/`. Ahora crea
  `.specify/planes/`, `.specify/tareas/` y `.specify/informes/`, y la salida
  de la instalación nombra esas rutas en vez de las vacías.
- `init` respeta `--root`, la opción global que usan los demás comandos y que
  la extensión de VS Code pasa siempre; antes la ignoraba y creaba `.specify/`
  en la carpeta actual, así que `Inicializar proyecto` desde la paleta
  inicializaba una carpeta distinta de la abierta. El path posicional sigue
  mandando cuando se indica.
- `init` se niega a crear un `.specify/` anidado cuando ya hay un proyecto
  toolkit en una carpeta superior: los comandos suben hasta el estado más
  cercano, así que el segundo dejaría dos raíces contradictorias. Volver a
  inicializar el mismo proyecto sigue siendo inocuo.
- La paleta de VS Code ejecuta los comandos capturando la salida y los
  muestra en el canal `SDD Toolkit`: cuando la CLI sale con 1 el fallo
  aparece como notificación con «Ver salida», en vez de perderse al fondo de
  un terminal. `clarify` sigue en la terminal porque pregunta por stdin, y
  `init` además confirma por notificación y refresca la vista y la barra.
- `clarify` desde la paleta valida el `SPEC-ID` con `clarify --list` antes de
  abrir el terminal: un ID inexistente se notifica con «Ver salida» en vez de
  quedar al fondo de la terminal, que solo se abre cuando la validación pasa.
- El panel de flujo apunta a los artefactos donde la CLI los escribe de
  verdad: `.specify/planes/PLAN-001.md`, `.specify/tareas/TASKS-PLAN-001.md`
  y `.specify/informes/INFORME-PLAN-001.md`, en vez de rutas que no existían.
- `arbol` y el flujo del IDE respetan el orden §21 de las fases: la
  recuperación aparecía antes de la implementación y las pruebas porque el
  orden lo dictaba la inserción en el diccionario, no el método.
- `specify` y `restricciones` avisan con `⛔` cuando el ID no existe, en vez de
  terminar con un traceback: son los dos últimos comandos que reventaban al
  escribir un identificador equivocado.
- El IDE gana el panel **Flujo SDD**: una fila por fase con su estado, el
  artefacto que deja y la skill que la ejecuta, y un clic que lanza el
  comando de la fase. Los datos salen de `export`, que ahora publica `flujo`
  (fase → artefacto → skill → comando) para cualquier adaptador.
- `init` deja el proyecto listo para el IDE: escribe `.vscode/settings.json`
  con el intérprete y la ruta del toolkit, y `.vscode/tasks.json` con las
  tareas `SDD: …`. Al abrir la carpeta la extensión funciona sin configurar
  nada, y los archivos existentes no se sobrescriben.

### Añadido

- La extensión lleva su `LICENSE` (copia del del repo) y un `.vscodeignore`:
  `vsce` empaqueta solo `extension.js`, `package.json`, el `readme.md` y la
  licencia, sin avisos de archivos faltantes ni de sobrantes.
- `tests/test_extension_headless.py` lleva el marcador `lento`, registrado en
  `pyproject.toml`: `pytest -m "not lento"` deja fuera el arnés y sus catorce
  invocaciones a la CLI (medido: 30,2 s frente a 38,7 s). Con `-q` sin filtro
  se sigue corriendo todo, también en CI.
- Primera pasada **dentro de un editor**: la extensión `0.1.5` en VS Code
  1.142.0, sobre un perfil aislado, con ocho casillas de 29 en verde (barra de
  estado y tooltip, `Fases y tareas`, `Flujo SDD` con tooltip, clic derecho a
  `Preview PLAN-001.md`, paleta `status` y fallo de `build PLAN-999`). Las demás
  siguen sin marcar y no se promueve ninguna fila a `✅ verificado`.
- `ide/COMPATIBILIDAD.md` deja una plantilla prellenada con los datos del
  entorno (versión, proyecto, sistema, fecha) para que la pasada en editor sea
  escribir lo observado y cambiar tres filas, sin tocar la tabla a mano.
- `scripts/preparar-manual.sh --solo-verificar` mira un entorno ya preparado
  sin rehacerlo: ajustes, `src/`, los tres `.md`, `comandos --verificar`, el
  estado, la extensión instalada y el arnés, lo imprime como tabla y termina
  diciendo qué bloques de `ide/PRUEBA-MANUAL.md` quedan a mano. Las filas se
  separan en comprobado (`✓`) y pendiente de editor (`☐`): el arnés nunca sale
  en verde, porque el editor no lo vio, y **cuenta como fallo en el código de
  salida** (`exit 1` mientras quede un `☐`), aunque en la tabla siga siendo
  `☐` para no confundir «sin mirar» con «roto». `ide/PRUEBA-MANUAL.md` documenta el
  orden de cada pasada: la tabla primero, y ninguna casilla marcada por ella.
- `ide/COMPATIBILIDAD.md` registra la primera pasada del IDE: la del
  2026-11-11, hecha **sin editor** con el arnés (41/41) sobre el entorno
  materializado. Queda en ⚠️ parcial, con la lista de lo que sigue necesitando
  ojos; ninguna casilla de la checklist se marcó.
- El arnés comprueba además que los tres `.md` que materializa la preparación
  son el artefacto de su fase en el flujo y que el plan se abre en vista
  previa, que es el camino que antes no se podía ejercitar con el fixture.
- La extensión tiene arnés propio: `tests/js/arnes_extension.js` carga el
  `extension.js` real con un stub de `vscode` y `tests/test_extension_headless.py`
  lo corre contra el fixture preparado (vista, paleta, clic derecho, fallos,
  aviso de skills, estado vacío y CLI rota). Si no hay `node`, se salta.
- `scripts/materializar_md.py` reescribe los `.md` de plan y tareas a partir
  de sus JSON con los renderizadores de la CLI, sin tocar el estado: el fixture
  de 0.1.0 solo trae los JSON (`plan --force` movería el proyecto a
  Arquitectura 0/18). La preparación lo usa y corre `analyze` —que tampoco
  cambia el estado— para que el clic derecho del IDE tenga los tres artefactos.
- La checklist manual corrige dos esperados que no coincidían con el editor:
  al regenerar los comandos la notificación muestra la primera línea de la CLI
  (`🧩 copilot: 14 comando(s)…`), no un texto propio, y el fixture de 0.1.0 no
  permite abrir los `.md` de plan, tareas e informe porque solo trae sus JSON y
  no tiene `.specify/informes/`.
- `scripts/verificar_vsix.py` revisa un `.vsix`: manifiesto y extensión
  presentes, ningún archivo vacío, sin `.vscodeignore` ni `.vsix` dentro y sin
  sobrantes en `extension/`. Antes solo se sabía abriendo el zip a mano.
- `scripts/preparar-manual.sh` deja lista la pasada manual del IDE en un paso:
  copia el fixture, escribe `.vscode/settings.json` con la ruta absoluta,
  restaura `src/productos.py` del snapshot 0, genera los comandos de copilot,
  verifica sus rutas y empaqueta el `.vsix` (`--sin-vsix` lo omite); con
  `--destino`/`--vsix-dir` cambia las rutas, sin `--force` no borra nada y
  `--instalar` corre `code --install-extension … --force` al terminar para
  dejar la extensión puesta de una vez.
- Una prueba extrae las rutas que cita el LEEME del fixture de 0.1.0 y exige
  que existan, y el LEEME aclara que aquel formato era solo JSON: la CLI
  actual escribe el JSON y también el `.md` al lado.
- `init` deja escrita la elección del cliente tras la pregunta, en su propia
  línea (`· cliente: copilot`, `· cliente: todos (…)` o `· cliente:
  ninguno`): lo tecleado en un `input()` no queda en la salida capturada y el
  eco salía pegado a la pregunta. No se imprime ninguna línea en blanco de
  más: en un terminal el Enter ya abre el renglón del eco, y una captura sin
  eco lo deja pegado, que es el precio de no ensuciar la salida interactiva.
- `init` puede dejar los comandos del agente generados en el acto: pregunta
  por el cliente cuando hay terminal, acepta `--cliente` repetible para no
  preguntar y `--sin-comandos` para omitirlo. Sin terminal no pregunta, porque
  la extensión y los scripts quedarían esperando una respuesta inexistente.
- `toolkit comandos --regenerar` reescribe solo los clientes que ya tienen
  archivos, con la ruta de la copia en uso; no estrena carpetas. Sin nada
  instalado avisa y sale con código 1.
- El aviso de skills de la vista `Fases y tareas` trae una fila «↻ Regenerar
  los comandos» que corre `comandos --regenerar` y refresca la vista al
  terminar, así que el aviso desaparece sin salir del IDE.
- `export` publica `avisos.skills` con las rutas de skills que ya no existen
  (total y cuántos archivos usa cada una), y la vista `Fases y tareas` abre con
  ese aviso cuando hay alguno. La extensión no lee los archivos generados: usa
  lo que ya calcula la CLI.
- `toolkit status` avisa al final cuando las skills instaladas apuntan a una
  ruta del toolkit que ya no existe: total de archivos, rutas muertas y cómo
  regenerarlas. Sin comandos instalados o con rutas vivas no añade nada a la
  salida; la comprobación vive en `core.agent_commands.rutas_muertas` y es la
  misma que usa `comandos --verificar`.
- `toolkit comandos --verificar` revisa lo ya generado sin reescribirlo: saca
  la ruta absoluta que lleva cada archivo y falla si ya no existe, indicando
  cuántos archivos apuntan a ella, dónde está este toolkit y la orden para
  regenerarlos. Sin comandos instalados avisa y no falla.
- `init` termina diciendo cómo generar los comandos del agente, con el comando
  exacto (`<python> "<ruta>/cli/main.py" comandos --cliente copilot`) y la
  advertencia de que la ruta absoluta queda grabada, así que hay que
  regenerarlos si el toolkit cambia de sitio; los pasos sugeridos incluyen
  `[ comandos ]`.
- Una prueba recorre los documentos del repo y falla si un enlace relativo
  apunta a una ruta que no existe, si un documento cita `archivo.py::símbolo`
  y ese símbolo ya no está, o si la prosa cita como código una ruta del repo
  —«`cli/main.py`», «`tests/test_ide.py`»— que ya no existe; los bloques de
  código y las carpetas que el toolkit escribe en el proyecto del usuario
  quedan fuera.
- Otra prueba levanta un proyecto real (de `init` a `instrucciones --guardar`)
  y exige que cada ruta del proyecto citada en las guías —`specs/SPEC-001.md`,
  `.specify/planes/PLAN-001.md`, `.specify/cache/analisis.json`…— exista ahí;
  las que solo se crean a pedido (`.specify/hooks/`, `.specify/spec_history/`,
  `.specify/sugerencias/`) se buscan en el código. La primera corrida encontró
  que el filtro inicial descartaba todo `.specify/…` por el punto; ya corregido.
- La misma corrida comprueba el **contenido** prometido en esos artefactos: la
  SPEC va `status: approved`, el plan deriva de la SPEC, las tareas listan
  `TASK-001`, el informe trae su veredicto y las instrucciones sus reglas.
- El verificador posterior exige que la release adjunte
  `sdd-visual-toolkit-X.Y.Z.vsix` con tamaño mayor que cero desde la 0.1.5, en
  vez de dejar ese adjunto a una revisión a mano.
- La paleta de VS Code muestra una notificación de progreso con la orden en
  curso cuando un comando tarda más de 400 ms: `build` y `test` ya no se
  esperan en silencio, y los rápidos no dejan un parpadeo.
- Ese progreso se puede cancelar: el proceso recibe SIGTERM, el corte se
  informa como cancelación y no como fallo, lo impreso queda en el canal con
  `(cancelado)` y la vista se refresca. El estado JSON se escribe con
  temporal y renombrado, así que un corte no lo deja truncado. La señal va al
  grupo de procesos, así que también termina el `pytest` que lanza `build`
  (en Windows, `taskkill /T`); el tope de espera corta igual.
- En los paneles `Flujo SDD` y `Fases y tareas`, el clic derecho sobre una fase
  abre su artefacto:
  los `.md` en vista previa, el JSON en el editor y las carpetas en el
  explorador. Si la fase todavía no lo escribió, avisa cuál falta en vez de
  abrir un archivo vacío; las fases sin artefacto no ofrecen el menú.
- El tope de espera de la paleta es configurable en
  `sddToolkit.timeoutMinutos` (5 por defecto): un valor inválido vuelve al
  defecto en vez de dejar los comandos sin límite.

## [0.1.5] — 2026-11-11

### Añadido

- Las descripciones de los catorce comandos dicen también cuándo usarlos
  («Úsalo cuando la SPEC está clara…»): en una skill es lo único que el
  agente ve antes de decidir si la aplica.
- `ide/PRUEBA-MANUAL.md` recorre casilla por casilla la extensión y los
  comandos de barra en VS Code, y las skills en Antigravity, con el formato
  de registro para anotar el resultado.
- La matriz de `ide/COMPATIBILIDAD.md` separa extensión y comandos de barra
  por cliente, deja dicho que ninguno está probado dentro del IDE y detalla,
  cliente por cliente, qué hay que abrir y qué anotar para cerrarlo.
- Cada release adjunta `sdd-visual-toolkit-X.Y.Z.vsix`, la extensión del IDE
  empaquetada con `vsce` desde el mismo commit que el tag, y el README
  documenta ese camino de instalación en lugar de la depuración desde el
  código.
- La comprobación previa a etiquetar exige que `ide/vscode/package.json`
  declare la versión del release, para que el `.vsix` no se adjunte con otro
  número.
- `toolkit comandos` escribe los comandos de barra del flujo en la carpeta
  que cada agente lee (`.claude/skills/`, `.cursor/commands/`,
  `.github/prompts/`, `.windsurf/workflows/`, `.agents/skills/`), con la ruta
  absoluta de la CLI adentro: `/sdd-plan-gate` ejecuta `plan --gate SPEC`.
- El verificador posterior exige que el commit etiquetado tenga todos sus
  checks en verde y terminados, para que un tag sobre un commit roto no pase
  por bueno.
- La comprobación previa a etiquetar exige que el commit de `HEAD` tenga
  todos sus checks terminados y en verde: un tag sobre un `main` con el CI
  roto o a medias ya no llega a crearse.
- El fixture de compatibilidad de 0.1.0 incluye ya las aclaraciones, el
  checkpoint de `TASK-001`, el estado del journal y el enriquecimiento del
  que salieron sus 21 requerimientos, así que la prueba ejercita también
  `specify --revise`.

### Corregido

- La paleta `SDD: Spec pinning` pedía solo el plan, pero `pin` es por tarea:
  desde VS Code respondía «indique PLAN-ID y --task». Ahora pide también el
  identificador de la tarea y ejecuta `pin PLAN-001 --task TASK-001`.
- Los comandos de barra se escribían con el frontmatter roto cuando la
  descripción llevaba «: »: 12 de los 56 archivos no eran YAML válido y el
  cliente podía no cargar el comando. Los valores van entre comillas simples.
- La pista de `/sdd-enrich` pedía «idea en una frase», pero `enrich` toma un
  solo argumento: sin comillas la orden acababa en `unrecognized arguments`.
  Ahora pide la idea entre comillas.
- La matriz de compatibilidad afirmaba que Cursor no recibe texto detrás del
  comando y que Windsurf sustituye `$ARGUMENTS`; ninguna de las dos cosas es
  así, y los pasos de prueba se corrigieron.
- `build` y su alias `implement` respondían «sin informe para PLAN-999;
  ejecute `analyze PLAN-999` primero» cuando el plan no existía: ahora dicen
  «plan inexistente» y el Quality Gate 4 sigue igual para los planes que sí
  existen.
- `pin --task` decía «línea base registrada» también cuando reutilizaba la
  que ya existía; ahora distingue las dos cosas y, al reutilizarla, aclara
  que no se vuelve a registrar.
- Los comandos de la CLI avisan cuando el ID no existe en vez de morir con un
  traceback: `ast`, `diff`, `historia`, `reporte`, `test`, `validate`,
  `flush`, `pin`, `recover`, `traza` y `clarify` capturaban solo el error de
  su propio módulo, no el de cargar la SPEC, el plan o la tarea.
- `pin --task` guarda la línea base y ya no revienta con `NameError` por una
  llamada a `_guardar_pin` que nadie importaba; tampoco borra las
  desviaciones ya registradas.
- `specify --revise` copiaba la SPEC a `.specify/spec_history/` antes de
  comprobar que su ENR de origen existiera: si faltaba, dejaba una copia
  huérfana y moría con un traceback. Ahora arma la revisión primero y avisa
  con un `⛔` sin escribir nada.
- El verificador solo miraba los enlaces `blob` de las notas y dejaba pasar
  el resto: un relativo o un `/tree/` no lo hacían fallar. Ahora todo enlace
  a un repositorio debe ser `blob` del tag en el repositorio propio, y se
  rechazan los relativos, los `tree` y los que apuntan a otro repositorio.
- Las notas de 0.1.0 enlazaban en relativo y la página de la release los
  resolvía contra la raíz del repo: los cuatro daban 404. Ahora apuntan a
  `blob/v0.1.0`, y el verificador compara esa versión con las notas del árbol
  porque su tag es inmutable.

## [0.1.4] — 2026-11-10

Versión de mantenimiento: sin cambios en la CLI, en el motor ni en el
formato de `.specify/`, así que sigue siendo compatible con proyectos
creados con 0.1.0 a 0.1.3. Es PARCHE por la misma razón que 0.1.3: lo
que cambia son las herramientas de release, las pruebas y la
documentación.

### Añadido

- `scripts/verificar_release.py --previo` comprueba antes de crear el tag
  lo que se revisaba a mano y tarde: tag libre en local y en `origin`, árbol
  limpio, `HEAD` en `origin/main`, versión y CHANGELOG en el árbol,
  `[No publicado]` vacía, enlaces del pie a la versión nueva, notas con
  enlaces al tag futuro y versión posterior a la última etiquetada.
- El fixture de compatibilidad incluye la línea base del pin y dos snapshots
  de `TASK-001` escritos por 0.1.0, y la prueba los ejercita con `validate`
  y `rollback`: restaurar el estado previo deja la validación limpia,
  restaurar el intento fallido la deja en OBSERVADO con un cambio de cuerpo,
  y el estado antiguo se restaura sin tocar nada ajeno.

### Corregido

- `verificar_release.py` daba por buena una release cuyo cuerpo no era el de
  `docs/release-notes-vX.Y.Z.md`: solo miraba que las notas existieran en el
  tag. Ahora compara el cuerpo publicado —sin espacios ni saltos finales— y
  señala el `gh release edit --notes-file` para arreglarlo. Aplicado hacia
  atrás, **v0.1.0 queda marcada**: su cuerpo tiene enlaces absolutos y el
  archivo del tag, relativos.
- `docs/RELEASES.md` describía el orden al revés: las notas aparecían
  después del tag, la release se creaba sin `--notes-file` —GitHub autogenera
  el «What's Changed»— y el modo `--previo` quedaba fuera del checklist, así
  que se podía etiquetar sin haberlo ejecutado. Ahora las notas se escriben
  antes de etiquetar, el último paso del checklist es
  `verificar_release.py --previo X.Y.Z` y la release se crea con
  `--verify-tag` y `--notes-file`.

## [0.1.3] — 2026-11-10

Versión de mantenimiento: documentación, pruebas y herramientas. Sin cambios
en el motor ni en el formato de `.specify/`: es compatible con proyectos
creados con 0.1.0 a 0.1.2.

### Añadido

- `tests/test_compatibilidad_formato.py` abre con la CLI actual un estado
  real creado por 0.1.0 (fixture sin regenerar, con su procedencia
  documentada) y comprueba que se lee, que leer no lo reescribe y que
  escribir conserva lo anterior. Así el CI avisa si el formato deja de ser
  compatible, sin depender del juicio de quien publica.
- `docs/RELEASES.md` incluye el paso posterior a publicar: comprobar que el
  tag anotado existe en el remoto y apunta al commit con la versión, que la
  release no quedó en borrador y que los enlaces de las notas resuelven en
  la ref del tag.
- El workflow de CI acepta `workflow_dispatch`, para arrancar los checks
  sobre una rama cuando GitHub tarda en crear el run del PR, sin duplicar
  runs cerrando y reabriendo, y solo si no existe ya uno para ese commit.
  `CONTRIBUTING.md` y `docs/BRANCH_PROTECTION.md` lo explican.
- `scripts/verificar_release.py` hace esas comprobaciones en un solo
  comando: tag anotado local y remoto, versión en `pyproject.toml` y
  CHANGELOG dentro del tag, release publicada y enlaces de las notas
  resueltos en la ref del tag. Sin dependencias: solo usa `git` y `gh`.

### Corregido

- `status` y `siguiente` avisaban «Pruebas con rojo: corrija y repita el
  test» aunque la última corrida estuviera en verde: `core/navigation.py`
  no consultaba el resultado. Ahora recomienda cerrar la tarea en curso o
  seguir con la próxima, y solo habla de rojo cuando lo hay.
- `pre-auditoria.md` y `docs/REMEDIACION.md` se leían como el estado actual:
  ninguno estaba fechado y el segundo decía «revisión en curso». Ahora abren
  con una nota de alcance que los sitúa en el 2026-11-10 y remite al estado
  vigente, y la frase sobre la falta de CI pasa al tiempo de entonces.
- `docs/RELEASES.md` pedía el CHANGELOG «sin dejar `No publicado`», lo que
  se lee como borrar la sección; ahora dice que las viñetas pasan a la
  sección nueva y que `[No publicado]` queda arriba, vacía.
- `CONTRIBUTING.md` seguía recomendando `--upgrade pip` al preparar el
  entorno, cuando el README y la CI no lo hacen y las notas de 0.1.2
  registran haberlo retirado por coste (4,0 s → 2,0 s de mediana por job).
- `ide/COMPATIBILIDAD.md` describía el MCP con tres herramientas de solo
  lectura y citaba como evidencia `tests/test_mcp.py`, que exige las seis:
  las tres de lectura y las tres operativas.
- `docs/BRANCH_PROTECTION.md` atribuía la espera del CI a GitHub en general.
  La medición de 31 runs de `push` (3–4 s, salvo un commit empujado diez
  minutos después de crearse) frente a 20 de `pull_request` (4 s a 447 s)
  sitúa la demora en el evento del PR, no en la cola de runners.
- El README anunciaba 269 pruebas en dos frases mientras su badge y la
  suite tenían 284. Los conteos se escriben a mano y solo el badge tenía
  prueba; ahora `tests/test_readme.py` compara también las menciones
  «N tests» de la prosa.

## [0.1.2] — 2026-11-10

Versión de mantenimiento y herramientas: sin cambios en el motor ni en el
formato de `.specify/`.

### Añadido

- `toolkit --version` imprime la versión, tomada de `pyproject.toml` en el
  árbol de fuentes y de los metadatos del paquete en una instalación normal.
  El servidor MCP declara esa misma versión en lugar de una constante.
- `docs/BRANCH_PROTECTION.md` describe las reglas de `main`, el motivo de
  cada una y cómo replicarlas; enlazado desde `CONTRIBUTING.md`.
- Caché de las dependencias de pip en la CI, con clave por versión de Python
  y hash de `requirements-dev.txt`.
- Pruebas que mantienen alineadas la versión de `pyproject.toml` con la
  primera entrada del CHANGELOG y el badge de tests del README con la suite.
- Los tags `v*` son inmutables: un ruleset impide moverlos o borrarlos una
  vez publicados. Los releases nuevos se siguen creando igual; detalles en
  `docs/BRANCH_PROTECTION.md`.

### Cambiado

- La CI ejecuta la suite en paralelo con `pytest-xdist -n 2` (16,1 s → 10,0 s
  por job en la medición); `pytest-xdist` queda como dependencia de
  desarrollo en `CONTRIBUTING.md`.
- La protección de `main` usa un ruleset de repositorio en vez de la
  protección clásica: todo cambio debe entrar por pull request, sin exención
  para administradores. Detalles en `docs/BRANCH_PROTECTION.md`.
- Las dependencias de desarrollo (`pytest`, `pytest-xdist`) se declaran en
  `requirements-dev.txt`; la CI y `CONTRIBUTING.md` instalan desde ahí en vez
  de repetir la lista, y la caché de pip usa esa clave.
- La CI ya no actualiza pip antes de instalar: el paso de instalación baja de
  4,0 s a 2,0 s de mediana por job (24 jobs antes, 20 después).

### Corregido

- El tablero buscaba el estado `"en curso"`, pero `build` marca `en_curso`:
  la «Tarea actual» nunca aparecía. `status`, `tablero` y `siguiente` usan
  ahora la constante del motor, con una prueba de regresión.
- El servidor MCP informaba `0.1.0` después de publicar la 0.1.1.
- El badge de tests del README anunciaba 259 pruebas frente a una suite
  mayor.
- `README.md`: las instrucciones ejecutaban `pytest` sin instalarlo (un
  entorno limpio fallaba en ese paso), decían 259 pruebas, el ejemplo
  de sesión mostraba un formato de salida que ya no existe y el rango de RF
  omitía las primeras.

## [0.1.1] — 2026-11-10

Versión de mantenimiento: no cambia el comportamiento del motor ni el
formato de `.specify/`.

### Añadido

- Código de conducta (Contributor Covenant 2.1, español) con el canal
  privado de reporte y enlaces desde `README.md` y `CONTRIBUTING.md`.
- Plantillas de issues para errores y propuestas, con selector que enlaza la
  guía de contribución y la SPEC.
- Plantilla de pull request con tipo, alcance, checklist de verificación y
  evidencia.
- `SECURITY.md` con versiones soportadas, alcance y expectativas; el reporte
  privado de vulnerabilidades queda habilitado en el repositorio.
- `CODEOWNERS` para solicitar revisión automática al dueño en PR de terceros.
- Job de CI `instalación editable`: instala el paquete y ejecuta `toolkit`
  fuera del árbol del repositorio. Queda exigido en `main` junto con la suite
  en las cuatro versiones soportadas.

### Corregido

- `pip install -e .` fallaba con «Multiple top-level packages discovered»;
  ahora `pyproject.toml` declara el backend y los paquetes de espacio de
  nombres, y el comando `toolkit` queda disponible tras instalar.
- `.gitignore` cubre los artefactos de empaquetado (`*.egg-info/`, `build/`,
  `dist/`).

## [0.1.0] — 2026-11-10

Primera versión funcional: ciclo SDD completo desde una idea hasta código
verificado, con gates humanos y estado recuperable.

### Añadido

- Fases `enrich`, `specify`, `clarify` (Quality Gate 1), `plan`
  (Quality Gate 2), `tasks` (Quality Gate 3), `analyze` (Quality Gate 4)
  e implementación incremental supervisada.
- Verificación real de cierre: una tarea no se completa sin archivos
  objetivo y pruebas ejecutables (`PASSED` / `FAILED` / `NOT_VERIFIED`).
- Spec pinning con AST diff, detección de cambios de cuerpo y validación
  estructural.
- Testing harness por capas (unitarios, integración, regresión,
  aceptación, estructural) y testing adaptativo multi-lenguaje
  (pytest/unittest, npm, Go, Rust).
- Journal, checkpoints semánticos, snapshots por tarea y rollback con
  validación de rutas.
- Trazabilidad SPEC → tarea → test → evidencia, tablero, árbol de
  estados, píldoras de navegación y mensajes de cierre.
- Sugerencias de mejora separadas del alcance de la tarea (evento
  `sugerencia` y registro en `.specify/sugerencias/`).
- CLI completa, extensión de VS Code, servidor MCP stdio con
  herramientas de lectura y operativas, y hooks propios por evento.
- Integración continua en GitHub Actions: suite completa en Python
  3.11, 3.12, 3.13 y 3.14 para cada push a `main` y cada pull request.
- Licencia MIT (`LICENSE`), `CONTRIBUTING.md` y `docs/RELEASES.md` con el
  flujo de contribución y el proceso de release.
- Cero dependencias externas en tiempo de ejecución.

### Cambiado

- Persistencia más durable: `fsync` de archivo y directorio tras el
  renombrado atómico, y compactación del historial JSONL.
- Análisis de repositorio con caché incremental y detección de archivos
  afectados.
- Cada fase de testing se ejecuta en una sola invocación del runner.

[No publicado]: https://github.com/kos0-CoL/sdd-visual-toolkit/compare/v0.1.6...HEAD
[0.1.6]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.6
[0.1.5]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.5
[0.1.4]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.4
[0.1.3]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.3
[0.1.2]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.2
[0.1.1]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.1
[0.1.0]: https://github.com/kos0-CoL/sdd-visual-toolkit/releases/tag/v0.1.0
