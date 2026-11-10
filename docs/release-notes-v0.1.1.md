# SDD Visual Toolkit v0.1.1

Versión de mantenimiento: arregla la instalación editable y completa los
archivos de comunidad. No cambia el comportamiento del motor ni el formato
de `.specify/`, así que es compatible con proyectos creados con 0.1.0.

## Corregido

- **`pip install -e .` funcionaba mal.** setuptools abortaba con
  `Multiple top-level packages discovered in a flat-layout` porque el
  proyecto usa paquetes de espacio de nombres y no declaraba backend ni
  paquetes. Ahora el comando `toolkit` queda disponible tras instalar:

  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  python3 -m pip install -e .
  toolkit --help
  ```

- `.gitignore` cubre los artefactos de empaquetado (`*.egg-info/`, `build/`,
  `dist/`).

## Añadido

- **Código de conducta** (Contributor Covenant 2.1, español), con el canal
  privado de reporte y enlaces desde el README y la guía de contribución.
- **Plantillas de issues** para errores y propuestas, con selector que enlaza
  la guía de contribución y la SPEC.
- **Plantilla de pull request** con tipo, alcance, checklist y evidencia.
- **`SECURITY.md`** con versiones soportadas, alcance y expectativas; el
  reporte privado de vulnerabilidades quedó habilitado en el repositorio.
- **`CODEOWNERS`** para solicitar revisión automática al dueño en PR de
  terceros.

## Instalación

Requisitos: **Python ≥ 3.11** y Git. Cero dependencias en tiempo de
ejecución.

```bash
git clone https://github.com/kos0-CoL/sdd-visual-toolkit.git
cd sdd-visual-toolkit
python3 cli/main.py --help
```

## Enlaces

- Changelog completo: [`CHANGELOG.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.1/CHANGELOG.md)
- Contribución: [`CONTRIBUTING.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.1/CONTRIBUTING.md)
- Código de conducta: [`CODE_OF_CONDUCT.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.1/CODE_OF_CONDUCT.md)
- Seguridad: [`SECURITY.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.1/SECURITY.md)
- Proceso de release: [`docs/RELEASES.md`](https://github.com/kos0-CoL/sdd-visual-toolkit/blob/v0.1.1/docs/RELEASES.md)

**Full Changelog**: https://github.com/kos0-CoL/sdd-visual-toolkit/compare/v0.1.0...v0.1.1

Licencia: MIT.
