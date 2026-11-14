# Contributing to Tekki-Pass

Thanks for helping! This guide is short on purpose: follow it and your PR will be quick to review.

## Workflow

1. Create an issue (or pick one) describing the change.
2. Branch from `main` using **`type/short-description`**, for example:
   - `feat/attestation-link`
   - `fix/invoice-expiry`
   - `docs/readme-architecture`
   - `chore/bump-next`

   Allowed types are the same as for commits (see below).
3. Commit using **Conventional Commits**.
4. Open a **small PR** (aim for under ~400 changed lines, one concern per PR) using the PR template.
5. Get **one approving review** and a green CI.
6. Merge with **Rebase and merge**, which keeps `main` linear. Delete the branch afterwards.

## Commit messages

Format: `type(scope): summary` in the imperative, lower case, no final period. CI enforces it with commitlint.

| Type       | When                                      |
| ---------- | ----------------------------------------- |
| `feat`     | A new feature                             |
| `fix`      | A bug fix                                 |
| `docs`     | Documentation only                        |
| `test`     | Adding or fixing tests                    |
| `refactor` | Code change that neither fixes nor adds   |
| `perf`     | Performance improvement                   |
| `build`    | Docker, dependencies, build tooling       |
| `ci`       | GitHub Actions                            |
| `chore`    | Anything else (repo maintenance)          |

Scopes (optional): `api`, `web`, `docs`, `adr`, `ci`, `docker`, `deps`, `github`.

Examples:

```
feat(api): add attestation request endpoint
fix(web): show a clear message when the payment is not received
docs(adr): record the chosen Lightning SDK
```

Breaking changes: add `!` after the type (`feat(api)!: ...`) and explain in the body.

## Local development

### API (`apps/api`): Python 3.12 + [uv](https://docs.astral.sh/uv/)

```bash
cd apps/api
uv sync
uv run uvicorn app.main:app --reload
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

### Web (`apps/web`): Node.js 24

```bash
cd apps/web
npm ci
npm run dev
npm run lint && npm run format:check && npm run typecheck && npm test
```

### Everything together

```bash
docker compose up --build
```

## Definition of Done

A change is done when:

- [ ] It does what the linked issue describes, and nothing more.
- [ ] Code is typed (mypy strict / TypeScript strict) and commented where the intent is not obvious.
- [ ] Tests cover the new behaviour and pass locally and in CI.
- [ ] Linters and formatters pass (ruff, ESLint, Prettier).
- [ ] No secret, personal data or real key appears in code, tests, logs or fixtures.
- [ ] User-facing text uses plain words (French first) and works on a small screen.
- [ ] Docs are updated (README, ADR, `.env.example`) if behaviour or configuration changed.
- [ ] One reviewer approved the PR.
