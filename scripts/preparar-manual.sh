#!/usr/bin/env bash
# Prepara la pasada manual del IDE (§29) en un solo paso: empaqueta el .vsix,
# copia el fixture de 0.1.0, deja los ajustes del workspace, restaura el código
# que `validate` compara y genera los comandos del agente.
#
# Uso:
#   scripts/preparar-manual.sh [--destino DIR] [--vsix-dir DIR] [--sin-vsix]
#                              [--instalar] [--force] [--solo-verificar]
#
#   --destino   proyecto de prueba (defecto /tmp/sdd-manual)
#   --vsix-dir  dónde dejar el .vsix (defecto /tmp/sdd-manual-vsix)
#   --sin-vsix  no empaquetar la extensión
#   --instalar  instalar el .vsix en VS Code al terminar (exige empaquetarlo)
#   --force     borrar y rehacer el destino si ya existe
#   --solo-verificar  no rehace nada: comprueba el destino ya preparado y dice
#                     qué casillas de ide/PRUEBA-MANUAL.md quedan a mano
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINO="${SDD_MANUAL_DIR:-/tmp/sdd-manual}"
VSIX_DIR="${SDD_MANUAL_VSIX:-/tmp/sdd-manual-vsix}"
CON_VSIX=1
INSTALAR=0
FORZAR=0
SOLO_VERIFICAR=0
PYTHON="${PYTHON:-python3}"

uso() {
    sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --destino) DESTINO="${2:?falta la ruta}"; shift 2 ;;
        --vsix-dir) VSIX_DIR="${2:?falta la ruta}"; shift 2 ;;
        --sin-vsix) CON_VSIX=0; shift ;;
        --instalar) INSTALAR=1; shift ;;
        --force) FORZAR=1; shift ;;
        --solo-verificar) SOLO_VERIFICAR=1; shift ;;
        -h|--help) uso; exit 0 ;;
        *) echo "⛔ opción desconocida: $1" >&2; uso >&2; exit 2 ;;
    esac
done

if [ "$INSTALAR" -eq 1 ] && [ "$CON_VSIX" -eq 0 ]; then
    echo "⛔ --instalar necesita empaquetar el .vsix; quite --sin-vsix" >&2
    exit 2
fi

if [ "$SOLO_VERIFICAR" -eq 1 ] && { [ "$FORZAR" -eq 1 ] || [ "$INSTALAR" -eq 1 ]; }; then
    echo "⛔ --solo-verificar no rehace ni instala nada; quite --force/--instalar" >&2
    exit 2
fi

# Mira el destino sin tocarlo: lo que la checklist necesita para poder
# ejercitarse, y lo que ya se puede dar por comprobado sin editor.
verificar() {
    local destino="$1"
    local faltas=0

    if [ ! -d "$destino/.specify" ]; then
        echo "⛔ $destino no está preparado: falta .specify/" >&2
        echo "   scripts/preparar-manual.sh --destino $destino --force" >&2
        exit 1
    fi

    echo "Verificación de $destino (no se rehace nada)"
    echo

    "$PYTHON" - "$RAIZ" "$destino" <<'PY' || faltas=$((faltas + 1))
import json
import subprocess
import sys
from pathlib import Path

raiz, destino = Path(sys.argv[1]), Path(sys.argv[2])
fallos = []

ajustes_path = destino / ".vscode" / "settings.json"
if not ajustes_path.is_file():
    fallos.append("⛔ ajustes     falta .vscode/settings.json")
else:
    ajustes = json.loads(ajustes_path.read_text(encoding="utf-8"))
    cli = Path(ajustes.get("sddToolkit.cliPath", ""))
    if not cli.is_file():
        fallos.append(f"⛔ ajustes     cliPath no existe: {cli}")
    elif not ajustes.get("sddToolkit.python"):
        fallos.append("⛔ ajustes     falta sddToolkit.python")
    else:
        print(f"✓ ajustes     cliPath {cli}")
        print(f"              python {ajustes['sddToolkit.python']}"
              f" · tope {ajustes.get('sddToolkit.timeoutMinutos')} min")

productos = destino / "src" / "productos.py"
snapshot = destino / ".specify" / "snapshots" / "TASK-001" / "0" / "src" / "productos.py"
if productos.is_file():
    print("✓ snapshot    src/productos.py presente (lo compara validate)")
elif snapshot.is_file():
    fallos.append("⛔ snapshot    src/productos.py sin restaurar del snapshot 0")

esperados = {
    "Arquitectura": destino / ".specify" / "planes" / "PLAN-001.md",
    "Tareas": destino / ".specify" / "tareas" / "TASKS-PLAN-001.md",
    "Análisis": destino / ".specify" / "informes" / "INFORME-PLAN-001.md",
}
faltan = [nombre for nombre, ruta in esperados.items() if not ruta.is_file()]
if faltan:
    fallos.append("⛔ artefactos  sin .md: " + ", ".join(faltan)
                  + " (el clic derecho de esas fases no se puede probar)")
else:
    print("✓ artefactos  plan, tareas e informe con su .md")

prompts = sorted((destino / ".github" / "prompts").glob("*.prompt.md"))
if prompts:
    print(f"✓ comandos    .github/prompts/: {len(prompts)} archivo(s)")
else:
    fallos.append("⛔ comandos    .github/prompts/ vacío o ausente")

proceso = subprocess.run(
    [sys.executable, str(raiz / "cli" / "main.py"), "--root", str(destino), "export"],
    capture_output=True, text=True)
if proceso.returncode != 0:
    ultimo = (proceso.stderr.strip().splitlines() or ["sin mensaje"])[-1]
    fallos.append(f"⛔ estado      export falló: {ultimo}")
else:
    datos = json.loads(proceso.stdout)
    progreso = datos["progreso"]
    print(f"✓ estado      {datos['fase']} · {progreso['hechas']}/{progreso['total']}"
          f" · siguiente {datos['navegacion']['recomendada']}")
    sin = [fase["fase"] for fase in datos["flujo"] if not fase.get("artefacto")]
    if sin:
        print(f"  · fases sin artefacto: {', '.join(sin)}")

for fallo in fallos:
    print(fallo, file=sys.stderr)
raise SystemExit(1 if fallos else 0)
PY

    if ! "$PYTHON" "$RAIZ/cli/main.py" --root "$destino" comandos --verificar; then
        faltas=$((faltas + 1))
    fi

    if command -v code >/dev/null 2>&1; then
        local ident
        ident="$(code --list-extensions --show-versions 2>/dev/null \
            | grep -i '^sdd-toolkit\.' || true)"
        if [ -n "$ident" ]; then
            echo "✓ extensión    $ident"
        else
            echo "⚠️ extensión    no instalada: instale el .vsix y recargue la ventana"
        fi
    else
        echo "⚠️ extensión    sin comando code; no se puede comprobar"
    fi

    if command -v node >/dev/null 2>&1; then
        local salida
        salida="$(mktemp)"
        if node "$RAIZ/tests/js/arnes_extension.js" "$RAIZ" "$destino" "$PYTHON" \
                >"$salida" 2>&1; then
            echo "✓ arnés        $(tail -1 "$salida")"
            echo "               (rompe y restaura un archivo de .github/prompts)"
        else
            faltas=$((faltas + 1))
            echo "⛔ arnés        falló:" >&2
            grep -E '^FAIL' "$salida" >&2 || tail -3 "$salida" >&2
        fi
        rm -f "$salida"
    else
        echo "⚠️ arnés        sin node; la vista no se puede ejercitar sin editor"
    fi

    echo
    echo "Casillas de ide/PRUEBA-MANUAL.md que este entorno deja ejercitar:"
    "$PYTHON" - "$RAIZ" <<'PY'
import sys
from pathlib import Path

md = Path(sys.argv[1]) / "ide" / "PRUEBA-MANUAL.md"
seccion, cuenta = "", {}
for linea in md.read_text(encoding="utf-8").splitlines():
    if linea.startswith("## "):
        seccion = linea[3:].strip()
        cuenta.setdefault(seccion, 0)
    elif linea.startswith("- [ ]") and seccion:
        cuenta[seccion] += 1
for nombre, total in cuenta.items():
    if total:
        print(f"  {nombre}: {total}")
PY
    echo "  Necesitan otro proyecto o cliente: la carpeta vacía, /tmp/sdd-init,"
    echo "  /tmp/sdd-manual/sub y las skills de Antigravity."
    echo "  Necesitan ojos en el editor: pintado, tooltips, menú contextual,"
    echo "  notificaciones y «Cancelar»."
    echo
    if [ "$faltas" -eq 0 ]; then
        echo "Entorno listo: abra VS Code en $destino y recorra la checklist."
    else
        echo "⚠️ $faltas comprobación(es) en rojo; arregle eso antes de la pasada." >&2
    fi
    return "$faltas"
}

if [ "$SOLO_VERIFICAR" -eq 1 ]; then
    verificar "$DESTINO"
    exit $?
fi

FIXTURE="$RAIZ/tests/fixtures/estado-0.1.0"
if [ ! -d "$FIXTURE" ]; then
    echo "⛔ falta el fixture: $FIXTURE" >&2
    exit 1
fi

if [ -e "$DESTINO" ]; then
    if [ "$FORZAR" -ne 1 ]; then
        echo "⛔ ya existe $DESTINO; use --force para borrarlo y rehacerlo" >&2
        exit 1
    fi
    rm -rf "$DESTINO"
fi
mkdir -p "$DESTINO"
cp -a "$FIXTURE/." "$DESTINO/"
echo "· fixture copiado en $DESTINO"

# Ajustes del workspace y `src/productos.py`: sin eso la extensión no sabe qué
# ejecutar y `validate` no tiene contra qué comparar el snapshot.
"$PYTHON" - "$RAIZ" "$DESTINO" <<'PY'
import json
import shutil
import sys
from pathlib import Path

raiz, destino = Path(sys.argv[1]), Path(sys.argv[2])
cli = (raiz / "cli" / "main.py").resolve()
ajustes = {
    "sddToolkit.python": sys.executable or "python3",
    "sddToolkit.cliPath": str(cli),
    "sddToolkit.timeoutMinutos": 5,
}
(destino / ".vscode").mkdir(exist_ok=True)
(destino / ".vscode" / "settings.json").write_text(
    json.dumps(ajustes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"· .vscode/settings.json → cliPath {cli}")

origen = destino / ".specify" / "snapshots" / "TASK-001" / "0" / "src" / "productos.py"
if origen.is_file():
    (destino / "src").mkdir(exist_ok=True)
    shutil.copy2(origen, destino / "src" / "productos.py")
    print("· src/productos.py restaurado del snapshot 0")
PY

# El fixture trae los JSON de plan y tareas sin sus `.md`, y no tiene informe:
# sin ellos las fases Arquitectura, Tareas y Análisis aparecen sin artefacto y
# el clic derecho no se puede probar. Se materializan con los renderizadores y
# con `analyze`, que no mueve el estado (sigue en 1/18, fase Pruebas).
"$PYTHON" "$RAIZ/scripts/materializar_md.py" "$DESTINO"
if [ -f "$DESTINO/.specify/planes/PLAN-001.json" ]; then
    "$PYTHON" "$RAIZ/cli/main.py" --root "$DESTINO" analyze PLAN-001 >/dev/null
    echo "· .specify/informes/INFORME-PLAN-001.md materializado (analyze)"
fi

"$PYTHON" "$RAIZ/cli/main.py" --root "$DESTINO" comandos --cliente copilot
"$PYTHON" "$RAIZ/cli/main.py" --root "$DESTINO" comandos --verificar

VSIX=""
if [ "$CON_VSIX" -eq 1 ]; then
    if ! command -v npx >/dev/null 2>&1; then
        echo "⛔ falta npx para empaquetar el .vsix; use --sin-vsix" >&2
        exit 1
    fi
    VERSION="$("$PYTHON" - "$RAIZ" <<'PY'
import json
import sys
from pathlib import Path
manifiesto = Path(sys.argv[1]) / "ide" / "vscode" / "package.json"
print(json.loads(manifiesto.read_text(encoding="utf-8"))["version"])
PY
)"
    mkdir -p "$VSIX_DIR"
    VSIX="$VSIX_DIR/sdd-visual-toolkit-$VERSION.vsix"
    LOG="$(mktemp)"
    # Se guarda la salida para poder enseñarla: un aviso de `vsce` avisa de un
    # paquete mal armado, y silenciarlo sería empeorarlo.
    if ! ( cd "$RAIZ/ide/vscode" && npx --yes @vscode/vsce package \
            --out "$VSIX" --allow-missing-repository >"$LOG" 2>&1 ); then
        cat "$LOG" >&2
        rm -f "$LOG"
        echo "⛔ falló el empaquetado del .vsix" >&2
        exit 1
    fi
    if grep -q "WARNING" "$LOG"; then
        grep "WARNING" "$LOG" >&2
        rm -f "$LOG"
        echo "⛔ el empaquetado dejó avisos; revíselos antes de instalar" >&2
        exit 1
    fi
    rm -f "$LOG"
    # Y el contenido: un `.vsix` con la extensión vacía instala y no arranca.
    "$PYTHON" "$RAIZ/scripts/verificar_vsix.py" "$VSIX"
    echo "✓ .vsix: $VSIX"
    echo "  (empaquetado desde esta copia, no desde la release)"
fi

INSTALADO=0
if [ "$INSTALAR" -eq 1 ]; then
    if ! command -v code >/dev/null 2>&1; then
        echo "⛔ falta el comando code; el .vsix quedó en $VSIX" >&2
        exit 1
    fi
    # --force reemplaza la versión instalada: es el mismo número en cada corrida.
    code --install-extension "$VSIX" --force
    INSTALADO=1
    echo "✓ extensión instalada en VS Code"
fi

echo
echo "Listo para la pasada manual:"
if [ "$INSTALADO" -eq 1 ]; then
    echo "  1. extensión ya instalada: solo recargar la ventana"
elif [ -n "$VSIX" ]; then
    echo "  1. code --install-extension \"$VSIX\""
else
    echo "  1. instalar el .vsix de la release (no se empaquetó uno aquí)"
fi
echo "  2. code \"$DESTINO\""
echo "  3. recargar la ventana y seguir ide/PRUEBA-MANUAL.md"
