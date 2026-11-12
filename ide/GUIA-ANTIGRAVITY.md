# Guía: pasada manual de Antigravity

Las siete casillas de `PRUEBA-MANUAL.md` que siguen sin marcar dependen de un
editor que no está instalado en la máquina donde se hizo el resto de la
pasada. Esto es lo mínimo para cerrarlas en una máquina que sí lo tenga.

No hay nada verificado de Antigravity todavía: esta guía no adelanta
resultados, solo el orden en que conviene mirar y qué anotar.

## Antes de empezar

- Antigravity instalado y una terminal con el repo del toolkit a mano.
- 15 minutos: el flujo es generar, abrir, invocar y anotar.
- Nada de esto se apoya en los tests: `tests/test_compatibilidad_formato.py`
  comprueba el formato de los archivos, no cómo los carga el agente.

## 1. Proyecto de prueba con las skills

```bash
python3 cli/main.py --root /tmp/sdd-anti init
python3 cli/main.py --root /tmp/sdd-anti comandos --cliente antigravity
```

Tiene que responder `🧩 antigravity: 14 comando(s) en
.agents/skills/{nombre}/SKILL.md` y dejar 14 `SKILL.md`. No se generan
*workflows*: ese mecanismo está deprecado en el manifiesto de Antigravity.

Ese paso ya está comprobado y su casilla está marcada; si no coincide, es un
hallazgo y merece una fila propia antes de seguir.

## 2. Que el agente vea las skills

Abre `/tmp/sdd-anti` como carpeta y busca el menú del agente (`/`, `@` o el
selector de skills, según la versión). Lo que hay que responder:

- ¿aparecen los catorce por nombre y descripción?
- ¿hizo falta recargar la ventana o reiniciar el agente?
- ¿se ven los `argument-hint`? En una skill el manifiesto solo documenta
  `name` y `description`, así que lo esperable es que **no**.

## 3. Que ejecute con la ruta horneada

Invoca `/sdd-status` (o la skill equivalente, eligiéndola a mano). En la orden
que el agente ejecute tiene que verse la ruta absoluta del `cli/main.py` de
este repo, no un `cli/main.py` relativo al proyecto del usuario:

```text
/usr/bin/python3 "/ruta/al/repo/cli/main.py" --root . status
```

Si pide aprobación, acepta una vez y repite para ver si la vuelve a pedir.

## 4. Terminal y permisos

- ¿el agente tiene terminal integrada y permiso de shell?
- ¿pide aprobación por comando, por sesión o ninguna?

Sin shell no hay comandos de barra: si es el caso, anótalo como bloqueo y no
sigas con las casillas siguientes.

## 5. Un comando con dato a mano

`/sdd-plan SPEC-001`: ¿toma el identificador del pedido y lo pasa al final de
la orden, o lo ignora? Prueba también `/sdd-plan` sin ID: lo esperable —por lo
que arreglamos en las skills— es que **pregunte** la SPEC-ID antes de ejecutar.

## 6. Que relaye la salida de la CLI

Corre `/sdd-status` y compara el texto con `python3 cli/main.py --root
/tmp/sdd-anti status` en una terminal aparte. La regla de la skill dice que la
salida de la CLI es la fuente de la verdad: si el agente la resume o la
reescribe con datos de memoria, es un hallazgo.

## 7. ¿Acepta el `.vsix`?

Si Antigravity instala extensiones de VS Code, prueba la extensión del
toolkit:

```bash
scripts/preparar-manual.sh --destino /tmp/sdd-anti2
```

Después instala el `.vsix` que deja en `/tmp/sdd-manual-vsix/` y mira paleta,
vista `SDD → Fases y tareas` y barra de estado, igual que en la pasada de VS
Code. Si no las acepta, anota el error tal cual.

Y por último, la casilla del manifiesto: `engines.vscode` declara `^1.80.0`;
comprueba la versión del editor (Ayuda → Acerca de) y di si es compatible.

## Cómo se anota

Cada casilla se marca solo después de su fila en `COMPATIBILIDAD.md`, con el
mismo formato que las demás:

```text
| 2026-11-12 | Antigravity <versión> · proyecto /tmp/sdd-anti | comandos de barra | ✅ <qué se vio> |
```

En `PRUEBA-MANUAL.md` la casilla pasa a `- [x]` y debajo va el detalle con la
fecha, igual que el resto:

```text
*visto* el 2026-11-12: <lo que salió, con el texto entre comillas>.
```

Si algo falla, no se marca la casilla: se anota el hallazgo, se abre un issue
y se deja la casilla como está. Una casilla marcada sin registro convierte la
matriz de compatibilidad en una promesa en vez de un dato.
