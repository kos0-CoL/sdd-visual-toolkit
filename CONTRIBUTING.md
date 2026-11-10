# Contribuir a SDD Visual Toolkit

Gracias por querer contribuir. El proyecto es pequeño a propósito:
biblioteca estándar de Python, cero dependencias en tiempo de ejecución y
una suite que se ejecuta en segundos.

## Requisitos

- Python >= 3.11
- `pytest` para la suite y `pytest-xdist` para ejecutarla en paralelo
  (únicas dependencias de desarrollo, declaradas en `requirements-dev.txt`)

## Preparar el entorno

```bash
git clone https://github.com/kos0-CoL/sdd-visual-toolkit.git
cd sdd-visual-toolkit
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

## Ejecutar las pruebas

```bash
python3 -m pytest tests/ -q
```

La suite completa debe quedar en verde. Si agrega capacidad, agregue al
menos un test que la verifique. La CI la ejecuta en paralelo con `-n 2`:
si una prueba comparte estado con otra, se verá ahí.

## Reglas de diseño

- **Solo biblioteca estándar** en `core/`, `cli/`, `state/` y `mcp/`.
  No agregue dependencias sin discutirlo antes en un issue.
- **El motor no inventa resultados**: lo que no se puede verificar se
  declara (`NOT_VERIFIED`, `sin_pruebas`, `—`), nunca se asume verde.
- **El humano implementa, el motor verifica**: no automatice la escritura
  de código dentro del ciclo.
- **Mensajes de dominio en español**; identificadores y API pública en
  inglés cuando corresponda.
- **Cambios pequeños y trazables**: un RF o una corrección por pull request.

## Flujo de trabajo

1. Abra un issue describiendo el problema o la propuesta.
2. Cree una rama (`fix/...`, `feat/...`, `docs/...`).
3. Haga el cambio con sus tests.
4. Ejecute `python3 -m pytest tests/ -q`.
5. Abra un pull request; la integración continua debe quedar verde y no se
   fusiona con conversaciones abiertas (ver `docs/BRANCH_PROTECTION.md`).

GitHub puede tardar varios minutos en crear el run del pull request. No
cierre y reabra el PR: eso emite un segundo evento, duplica los jobs y deja
el merge bloqueado hasta que terminan ambos runs. Compruebe si el run ya
existe y solo si no hay ninguno arránquelo a mano:

```bash
gh run list --commit "$(git rev-parse HEAD)" --limit 1
gh workflow run CI --ref <rama>
gh pr checks <n> --watch --interval 10
```

El run manual reporta los mismos checks sobre el mismo commit. Espere a que
`mergeStateStatus` sea `CLEAN` antes de fusionar.

## Estilo de commits

Mensajes en imperativo y enfocados en el porqué. Ejemplo:

```text
Evitar que el cierre marque completada una tarea sin pruebas
```

## Licencia

Al contribuir acepta que su aporte se publique bajo la licencia MIT de
este repositorio (ver `LICENSE`).

## Referencias

- Producto: `docs/SPEC-v0.1.md`
- Remediación: `docs/REMEDIACION.md`
- Cambios: `CHANGELOG.md`
- Releases: `docs/RELEASES.md`
- Rama protegida: `docs/BRANCH_PROTECTION.md`
- Seguridad: `SECURITY.md`
- Conducta: `CODE_OF_CONDUCT.md`
