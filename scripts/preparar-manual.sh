#!/usr/bin/env bash
# Prepara la pasada manual del IDE (§29) en un solo paso: empaqueta el .vsix,
# copia el fixture de 0.1.0, deja los ajustes del workspace, restaura el código
# que `validate` compara y genera los comandos del agente.
#
# Uso:
#   scripts/preparar-manual.sh [--destino DIR] [--vsix-dir DIR] [--sin-vsix]
#                              [--instalar] [--force]
#
#   --destino   proyecto de prueba (defecto /tmp/sdd-manual)
#   --vsix-dir  dónde dejar el .vsix (defecto /tmp/sdd-manual-vsix)
#   --sin-vsix  no empaquetar la extensión
#   --instalar  instalar el .vsix en VS Code al terminar (exige empaquetarlo)
#   --force     borrar y rehacer el destino si ya existe
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINO="${SDD_MANUAL_DIR:-/tmp/sdd-manual}"
VSIX_DIR="${SDD_MANUAL_VSIX:-/tmp/sdd-manual-vsix}"
CON_VSIX=1
INSTALAR=0
FORZAR=0
PYTHON="${PYTHON:-python3}"

uso() {
    sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --destino) DESTINO="${2:?falta la ruta}"; shift 2 ;;
        --vsix-dir) VSIX_DIR="${2:?falta la ruta}"; shift 2 ;;
        --sin-vsix) CON_VSIX=0; shift ;;
        --instalar) INSTALAR=1; shift ;;
        --force) FORZAR=1; shift ;;
        -h|--help) uso; exit 0 ;;
        *) echo "⛔ opción desconocida: $1" >&2; uso >&2; exit 2 ;;
    esac
done

if [ "$INSTALAR" -eq 1 ] && [ "$CON_VSIX" -eq 0 ]; then
    echo "⛔ --instalar necesita empaquetar el .vsix; quite --sin-vsix" >&2
    exit 2
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
    ( cd "$RAIZ/ide/vscode" && npx --yes @vscode/vsce package \
        --out "$VSIX" --allow-missing-repository >/dev/null )
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
