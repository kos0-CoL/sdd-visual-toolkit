# Rama protegida `main`

La protección vive en la configuración del repositorio en GitHub, no en el
código: este archivo la describe para que no dependa de la memoria de una
persona. **GitHub no lee este archivo**; si algo cambia acá, hay que
aplicarlo en el repositorio.

Estado verificado el 2026-11-10 sobre `main`:

| Regla | Valor | Por qué |
|---|---|---|
| Checks obligatorios | `tests (Python 3.11)`, `tests (Python 3.12)`, `tests (Python 3.13)`, `tests (Python 3.14)`, `instalación editable` | La suite por versión y el empaquetado no pueden quedar en rojo |
| Rama al día antes de fusionar (`strict`) | Desactivado | Con un solo mantenedor, exigir rebase en cada PR agrega fricción; ver el riesgo abajo |
| Revisiones obligatorias | Ninguna | Quien abre el PR no puede aprobarlo; con una sola cuenta bloquearía todo |
| Aplicar a administradores (`enforce_admins`) | Activado | El dueño tampoco fusiona por atajo: todo entra por PR |
| Push forzado | Bloqueado | No se reescribe el historial de `main` |
| Borrar la rama | Bloqueado | `main` existe siempre |
| Resolver conversaciones | Obligatorio | Un comentario abierto impide fusionar |
| Restricciones de push | Ninguna | Quien tiene escritura puede crear ramas |
| Historial lineal | Desactivado | El squash merge ya deja un commit por PR |
| Commits firmados | Desactivado | No hay infraestructura de firma en el proyecto |

## Los checks obligatorios dependen del workflow

Los nombres de los checks son los nombres **resueltos** de los jobs de
`.github/workflows/ci.yml`:

- `tests (Python ${{ matrix.python-version }})` produce `tests (Python 3.11)` … `3.14`.
- `instalación editable` es el job que instala el paquete y ejecuta `toolkit`
  fuera del árbol.

Si se renombra un job o se quita una versión de la matriz, el check esperado
**deja de reportarse** y GitHub bloquea los merges con «Expected — Waiting
for status to be reported». Falla de forma ruidosa, no silenciosa, pero hay
que acordarse de actualizar la protección en el mismo cambio.

## Riesgo asumido con `strict` desactivado

La CI de un PR corre contra el resultado de fusionar el PR con la base del
momento. Si la base avanza después de esa ejecución, el merge puede no haber
sido probado exactamente como quedará. Es aceptable mientras haya una sola
persona fusionando de a un PR; si entran varios PR en paralelo, conviene
activar `strict` para forzar la rama al día.

## Revisión automática

`.github/CODEOWNERS` asigna todas las rutas a `@kos0-CoL`, así que un PR de
otra persona solicita revisión sin configuración extra. GitHub **no** pide
revisión a quien abre el PR: con una sola cuenta el efecto no se ve.

## Replicar la configuración

```bash
gh api -X PUT repos/kos0-CoL/sdd-visual-toolkit/branches/main/protection --input - <<'JSON'
{
  "required_status_checks": {
    "strict": false,
    "contexts": [
      "tests (Python 3.11)",
      "tests (Python 3.12)",
      "tests (Python 3.13)",
      "tests (Python 3.14)",
      "instalación editable"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
```

## Comprobar el estado actual

```bash
gh api repos/kos0-CoL/sdd-visual-toolkit/branches/main/protection \
  --jq '{checks: .required_status_checks.contexts,
         strict: .required_status_checks.strict,
         admins: .enforce_admins.enabled,
         force: .allow_force_pushes.enabled,
         borrar: .allow_deletions.enabled,
         conversaciones: .required_conversation_resolution.enabled}'
```
