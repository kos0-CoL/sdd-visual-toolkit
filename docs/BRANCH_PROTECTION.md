# Rama protegida `main`

La protección vive en la configuración del repositorio en GitHub, no en el
código: este archivo la describe para que no dependa de la memoria de una
persona. **GitHub no lee este archivo**; si algo cambia acá, hay que
aplicarlo en el repositorio.

Desde el 2026-11-10 se usa un **ruleset de repositorio** (id `26952531`,
«main protegida») en lugar de la protección clásica de rama, que quedó
eliminada.

## Reglas activas

| Regla del ruleset | Efecto | Equivalente clásico |
|---|---|---|
| `pull_request` | Todo cambio entra por pull request | No existía: se cumplía por costumbre |
| `required_status_checks` | `tests (Python 3.11)` … `3.14` e `instalación editable` | Igual |
| `deletion` | No se puede borrar `main` | Igual |
| `non_fast_forward` | No se puede reescribir el historial | `allow_force_pushes: false` |

Parámetros del ruleset:

- `strict_required_status_checks_policy: false` — no se exige rama al día.
- `required_approving_review_count: 0` — sin revisiones obligatorias.
- `required_review_thread_resolution: true` — conversaciones resueltas.
- `require_extra_approval_for_unattributed_changes: false` — ver abajo.
- `bypass_actors: []` — nadie queda exento, ni el dueño.

## Qué cambia frente a la protección clásica

1. **Los administradores quedan cubiertos por defecto.** En la clásica hacía
   falta `enforce_admins: true`; en el ruleset la exención se pide
   explícitamente con `bypass_actors`, y acá está vacía.
2. **«Todo por pull request» pasó a estar forzado por el servidor.** Antes era
   una convención: la protección clásica no impedía un push directo. Ahora se
   verifica que un push directo a `main` se rechaza con
   `push declined due to repository rule violations` y
   `Changes must be made through a pull request`.
3. **El ruleset es un objeto con historial y estado.** Se puede consultar,
   versionar y desactivar (`enforcement: disabled`) sin perder la
   configuración; la clásica se sobrescribía a ciegas.
4. **Los refs se eligen por patrón.** Acá se usa `~DEFAULT_BRANCH`, así que si
   el repositorio cambia de rama por defecto, la regla la sigue.
5. **El endpoint clásico ya no existe.** `GET /branches/main/protection`
   responde `404 Branch not protected`; los scripts que lo consulten deben
   pasar al de rulesets.

## Dos detalles que muerden

- **`require_extra_approval_for_unattributed_changes` viene en `true` por
  defecto** al crear el ruleset, aunque no se envíe. Con una sola cuenta y
  cero aprobaciones requeridas, eso puede bloquear un PR sin que nadie pueda
  aprobarlo; se desactivó de forma explícita y conviene revisarlo si se
  recrea el ruleset.
- **Los nombres de los checks dependen del workflow.** `tests (Python …)` sale
  de la matriz de `.github/workflows/ci.yml` e `instalación editable` del job
  `install`. Si se renombra un job o se quita una versión de la matriz, el
  check esperado deja de reportarse y GitHub bloquea los merges con
  «Expected — Waiting for status to be reported». Falla de forma ruidosa, no
  silenciosa, pero hay que actualizar la regla en el mismo cambio.

## Riesgo asumido

- **Sin revisiones obligatorias**: con una sola cuenta, exigirlas bloquearía
  todos los PR. `.github/CODEOWNERS` sí solicita revisión en PR de terceros,
  porque GitHub nunca pide revisión a quien abre el PR.
- **`strict` desactivado**: la CI de un PR corre contra el resultado de
  fusionarlo con la base del momento; si la base avanza después, el merge
  puede no haber sido probado exactamente como quedará. Aceptable con una
  persona fusionando de a un PR; con varios PR en paralelo conviene activarlo.

## Replicar el ruleset

```bash
# `allowed_merge_methods` y `required_reviewers` los rellena GitHub; se
# incluyen para que este bloque coincida con lo que devuelve la API.
gh api -X POST repos/kos0-CoL/sdd-visual-toolkit/rulesets --input - <<'JSON'
{
  "name": "main protegida",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          {"context": "tests (Python 3.11)"},
          {"context": "tests (Python 3.12)"},
          {"context": "tests (Python 3.13)"},
          {"context": "tests (Python 3.14)"},
          {"context": "instalación editable"}
        ]
      }
    },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true,
        "require_extra_approval_for_unattributed_changes": false,
        "allowed_merge_methods": ["merge", "squash", "rebase"],
        "required_reviewers": []
      }
    }
  ],
  "bypass_actors": []
}
JSON
```

## Comprobar el estado actual

```bash
gh api repos/kos0-CoL/sdd-visual-toolkit/rulesets \
  --jq '.[] | {name, enforcement, target}'

gh api repos/kos0-CoL/sdd-visual-toolkit/rules/branches/main \
  --jq '.[] | {type, params: (.parameters // {})}'
```

Para desactivarlo sin borrarlo: `PATCH /rulesets/26952531` con
`{"enforcement": "disabled"}`.
