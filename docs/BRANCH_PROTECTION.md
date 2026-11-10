# Protección de `main` y de los tags de versión

La protección vive en la configuración del repositorio en GitHub, no en el
código: este archivo la describe para que no dependa de la memoria de una
persona. **GitHub no lee este archivo**; si algo cambia acá, hay que
aplicarlo en el repositorio.

Hay dos rulesets activos:

| Ruleset | Id | Alcance |
|---|---|---|
| «main protegida» | `26952531` | la rama por defecto |
| «tags de versión inmutables» | `26955481` | `refs/tags/v*` |

Desde el 2026-11-10 la rama usa un ruleset en lugar de la protección clásica,
que quedó eliminada.

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

## Cuando el CI tarda en arrancar

GitHub crea el run de `pull_request` con retraso variable: en diez PR
seguidos de este repositorio (2026-11-10) fue de **4 s a 447 s**, y ningún
evento se perdió — los runs aparecieron tarde, no dejaron de crearse. No es
configuración del repo: hay un solo workflow, sin filtros de rutas.

La tentación es cerrar y reabrir el PR. No lo haga: eso emite un segundo
evento, crea un run duplicado (el doble de jobs) y el PR queda `BLOCKED`
hasta que terminan los dos, porque el ruleset exige los checks y hay dos
juegos en curso.

Espere con un sondeo acotado, o arranque el workflow a mano sobre la rama:

```bash
gh workflow run CI --ref <rama>
gh pr checks <n> --watch --interval 10
```

El run manual reporta los mismos nombres de check sobre el mismo commit, así
que satisface el ruleset. Antes de fusionar, `mergeStateStatus` debe ser
`CLEAN`: los cinco checks verdes de un run no bastan si hay otro en curso.

## Riesgo asumido

- **Sin revisiones obligatorias**: con una sola cuenta, exigirlas bloquearía
  todos los PR. `.github/CODEOWNERS` sí solicita revisión en PR de terceros,
  porque GitHub nunca pide revisión a quien abre el PR.
- **`strict` desactivado**: la CI de un PR corre contra el resultado de
  fusionarlo con la base del momento; si la base avanza después, el merge
  puede no haber sido probado exactamente como quedará. Aceptable con una
  persona fusionando de a un PR; con varios PR en paralelo conviene activarlo.

## Tags de versión

Los tags `v*` son inmutables (`deletion`, `update`, `non_fast_forward`, sin
`bypass_actors`). Antes de aplicar la regla se comprobó que un tag se podía
mover sin dejar rastro; hoy eso falla. Comportamiento verificado el
2026-11-10:

| Acción | Resultado |
|---|---|
| Mover `v0.1.0` a otro commit | `push declined due to repository rule violations` |
| Borrar `v0.1.1` | `push declined due to repository rule violations` |
| Crear un tag nuevo `v0.0.1-prueba` | Permitido (y luego eliminado) |

Consecuencias prácticas:

- **Publicar una versión no cambia**: crear y empujar el tag sigue funcionando;
  sólo se bloquea moverlo o borrarlo después.
- **Un tag equivocado queda fijo.** Para corregirlo hay que desactivar el
  ruleset (`PUT` con `"enforcement": "disabled"`), borrar el tag y volver a
  activarlo. Es el precio de que un release no pueda cambiar bajo los pies.
- **El patrón es `refs/tags/v*`**: un tag con otro nombre (por ejemplo
  `prueba-tmp`) no está cubierto y se puede borrar normalmente.

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

## Replicar el ruleset de tags

```bash
gh api -X POST repos/kos0-CoL/sdd-visual-toolkit/rulesets --input - <<'JSON'
{
  "name": "tags de versión inmutables",
  "target": "tag",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "update"},
    {"type": "non_fast_forward"}
  ],
  "bypass_actors": []
}
JSON
```

## Comprobar el estado actual

```bash
gh api repos/kos0-CoL/sdd-visual-toolkit/rulesets \
  --jq '.[] | {name, target, enforcement}'

gh api repos/kos0-CoL/sdd-visual-toolkit/rulesets/26955481 \
  --jq '{name, target, enforcement, reglas: [.rules[].type]}'

gh api repos/kos0-CoL/sdd-visual-toolkit/rules/branches/main \
  --jq '.[] | {type, params: (.parameters // {})}'

git ls-remote --tags origin
```

Para desactivar un ruleset sin borrarlo, `PUT /rulesets/<id>` con el cuerpo
completo y `"enforcement": "disabled"`. `PATCH` sobre ese endpoint devuelve
`404` aunque el ruleset exista: es una limitación de la API, no un error de
permisos.
