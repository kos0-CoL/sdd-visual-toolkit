# Proceso de release

## Versionado

SemVer `MAYOR.MENOR.PARCHE`:

- **MAYOR**: cambios incompatibles en la CLI, en el formato de `.specify/`
  o en el protocolo MCP.
- **MENOR**: capacidad nueva compatible.
- **PARCHE**: correcciones y documentación.

`pyproject.toml` es la fuente de la versión; `CHANGELOG.md` la fuente de
las notas.

## Checklist antes de etiquetar

1. `python3 -m pytest tests/ -q` en verde.
2. CI en verde en todas las versiones soportadas.
3. `CHANGELOG.md` con la versión y su fecha (sin dejar `No publicado`).
4. `version` de `pyproject.toml` actualizada.
5. Smoke test de la CLI:

   ```bash
   python3 cli/main.py --help
   ```

6. Revisar que no se versionen secretos ni el `.specify/` de un proyecto real.

## Publicar

El tag debe apuntar al commit que ya contiene el CHANGELOG y la versión de
`pyproject.toml`; nunca a un árbol con cambios sin confirmar.

```bash
git tag -a v0.1.0 -m "v0.1.0 — primera versión funcional"
git push origin v0.1.0
```

Luego cree la release en GitHub con las notas del CHANGELOG (borrador en
`docs/release-notes-vX.Y.Z.md`). Una release solo se anuncia cuando CI está
verde y los artefactos corresponden al tag.

## Verificar tras publicar

Crear el tag no termina la release. Compruebe que es el tag anotado que
apunta al commit con la versión y que la release quedó pública:

```bash
git describe --tags                       # vX.Y.Z
git ls-remote --tags origin | grep vX.Y.Z  # el tag existe en el remoto
gh release view vX.Y.Z --json tagName,isDraft,isPrerelease
```

`isDraft` e `isPrerelease` deben ser `false`. Si la release quedó como
borrador, publíquela con `gh release edit vX.Y.Z --draft=false`.

Compruebe también que los enlaces de las notas apuntan a la ref del tag y
no a `main`, que sigue avanzando:

```bash
for f in CHANGELOG.md CONTRIBUTING.md SECURITY.md docs/release-notes-vX.Y.Z.md; do
  gh api "repos/kos0-CoL/sdd-visual-toolkit/contents/$f?ref=vX.Y.Z" --jq .path
done
```

Un `404` es un enlace roto: corrija las notas y actualícelas con
`gh release edit vX.Y.Z --notes-file docs/release-notes-vX.Y.Z.md`. El tag
no se toca, porque los tags `v*` son inmutables.

## Comunidad

- **Issues**: incluya versión de Python, sistema operativo y el comando
  exacto que falló.
- **Pull requests**: ver `CONTRIBUTING.md`.
- No hay canal de soporte con SLA; el proyecto se mantiene de forma
  voluntaria.
