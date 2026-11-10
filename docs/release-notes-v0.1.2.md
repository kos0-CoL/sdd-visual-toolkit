# SDD Visual Toolkit v0.1.2

Versión de mantenimiento y herramientas. Sin cambios en el motor ni en el
formato de `.specify/`: es compatible con proyectos creados con 0.1.0 y 0.1.1.

## Añadido

- **`toolkit --version`** imprime la versión y sale con código 0:

  ```console
  $ toolkit --version
  toolkit 0.1.2
  ```

  La versión sale de `pyproject.toml` cuando se ejecuta desde el árbol de
  fuentes y de los metadatos de la distribución en una instalación normal.

- **`docs/BRANCH_PROTECTION.md`**: las reglas de `main` (checks obligatorios,
  administradores, push forzado, borrado de rama, conversaciones), el motivo
  de cada una, el acoplamiento con los nombres de los jobs de CI y los
  comandos para replicar y comprobar la configuración.
- **CI**: caché de dependencias de pip por versión de Python y hash de
  `pyproject.toml`.
- **Pruebas de consistencia**: la versión de `pyproject.toml` debe coincidir
  con la primera entrada del CHANGELOG, y el badge de tests del README con lo
  que recolecta pytest.

## Cambiado

- **CI más rápida donde se podía medir.** La suite corre en paralelo con
  `pytest-xdist -n 2`: 16,1 s → 10,0 s por job (medido en tres ejecuciones) y
  −15 % de cómputo por run. El reloj total del run no baja, porque el límite
  pasó a ser el aprovisionamiento del runner.
- **Protección de `main` con ruleset** en lugar de la protección clásica:
  todo cambio entra por pull request, sin exención para administradores,
  y la configuración queda versionada y consultable.

## Corregido

- El servidor MCP informaba `0.1.0` después de publicar la 0.1.1: CLI y MCP
  comparten ahora una sola fuente de versión, así que no pueden desfasarse.
- El badge de tests del README anunciaba 259 pruebas frente a una suite
  mayor.
- **Las instrucciones del README no funcionaban en un entorno limpio**: el
  paso de verificación ejecutaba `pytest` sin instalarlo. Ahora hay un paso
  explícito de dependencias de desarrollo.
- El ejemplo de sesión mostraba un formato de salida que ya no existe y el
  rango de RF omitía las primeras; ambos quedaron corregidos y verificados.

## Instalación

Requisitos: **Python ≥ 3.11** y Git. Cero dependencias en tiempo de
ejecución.

```bash
git clone https://github.com/kos0-CoL/sdd-visual-toolkit.git
cd sdd-visual-toolkit
python3 cli/main.py --help
```

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.2/CHANGELOG.md)
- Rama protegida: [`docs/BRANCH_PROTECTION.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.2/docs/BRANCH_PROTECTION.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.2/CONTRIBUTING.md)
- Seguridad: [`SECURITY.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.2/SECURITY.md)

**Full Changelog**: https://github.com/kos0-CoL/sdd-visual-toolkit/compare/v0.1.1...v0.1.2

Licencia: MIT.
