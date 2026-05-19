# Platform Adapters — Referencia técnica

Esta referencia describe cómo interactúa RepoIntel con cada plataforma Git soportada:
qué permisos necesita el token, qué endpoints usa, cuándo clonar el repo vs solo usar
la API, y cómo mapea los conceptos de cada plataforma al modelo interno de RepoIntel.

---

## Tabla de contenidos

1. [Modelo interno común](#1-modelo-interno-común)
2. [Estrategia híbrida: API vs clone](#2-estrategia-híbrida-api-vs-clone)
3. [GitLab](#3-gitlab)
4. [GitHub](#4-github)
5. [Azure DevOps](#5-azure-devops)
6. [Bitbucket](#6-bitbucket)
7. [Detección automática de plataforma](#7-detección-automática-de-plataforma)

---

## 1. Modelo interno común

Todos los adapters producen las mismas estructuras. Esto desacopla los módulos
de análisis de la plataforma subyacente.

```python
# Proyecto / Repositorio
{
  "id": str,
  "name": str,
  "full_path": str,             # org/grupo/repo
  "description": str | None,
  "url": str,                   # URL web del proyecto
  "clone_url_https": str,       # URL para clonar con token embebido
  "clone_url_ssh": str,
  "default_branch": str,
  "visibility": "public" | "private" | "internal",
  "last_activity": str,         # ISO 8601
  "platform": "gitlab" | "github" | "azdevops" | "bitbucket"
}

# Rama
{
  "name": str,
  "is_default": bool,
  "is_protected": bool,
  "last_commit_sha": str,
  "last_commit_message": str,
  "last_commit_author": str,
  "last_commit_date": str,
  "ahead_behind": { "ahead": int, "behind": int } | None
}

# Pull Request / Merge Request
{
  "id": str,
  "title": str,
  "state": "open" | "merged" | "closed",
  "source_branch": str,
  "target_branch": str,
  "author": str,
  "reviewers": list[str],
  "created_at": str,
  "updated_at": str,
  "merged_at": str | None
}
```

---

## 2. Estrategia híbrida: API vs clone

Usa la API para metadata; clona solo cuando necesitas leer contenido de archivos.

| Análisis           | API | Clone | Razón                                              |
|--------------------|-----|-------|----------------------------------------------------|
| Ramas              | ✅  | ❌    | La API devuelve todos los datos de ramas           |
| Actividad          | ✅  | ❌    | Commits, PRs e issues están en la API              |
| Contratos API      | ❌  | ✅    | Hay que leer archivos .yaml/.json/.wsdl del repo   |
| Stack tecnológico  | ⚠️  | ✅    | API da lenguajes; stack completo requiere archivos |
| Dependencias       | ⚠️  | ✅    | Hay que parsear package.json, pom.xml, etc.        |
| Seguridad (CVEs)   | ❌  | ✅    | Hay que leer manifiestos de dependencias           |
| Seguridad (secrets)| ❌  | ✅    | Hay que hacer grep en el código fuente             |
| Calidad            | ⚠️  | ✅    | CI config por API; complejidad requiere código     |

**Clonar siempre con:**
```bash
git clone --depth=1 https://oauth2:<TOKEN>@<host>/<path>.git /tmp/repo-intel/<name>/
```
Limpia el directorio temporal al terminar: `rm -rf /tmp/repo-intel/<name>/`

---

## 3. GitLab

### Permisos del token (PAT o Project Access Token)

Scope recomendado para análisis completo: **`read_api` + `read_repository`**

| Análisis               | Scope requerido      |
|------------------------|----------------------|
| Discovery de proyectos | `read_api`           |
| Ramas / commits / MRs  | `read_repository`    |
| Issues / Pipelines     | `read_api`           |
| Clonar repo            | `read_repository`    |

### Endpoints principales

```
Base URL: https://<host>/api/v4

GET /groups/:id/projects?per_page=100&include_subgroups=true   # discovery por grupo
GET /projects?search=<term>&per_page=100                       # búsqueda
GET /projects/:id/repository/branches?per_page=100             # ramas
GET /projects/:id/repository/commits?ref_name=<branch>         # commits
GET /projects/:id/merge_requests?state=all&per_page=100        # MRs
GET /projects/:id/issues?state=all&per_page=100                # issues
GET /projects/:id/pipelines?per_page=20                        # CI
GET /projects/:id/repository/tree?recursive=true               # árbol de archivos
GET /projects/:id/repository/files/:path/raw?ref=<branch>      # contenido de archivo
```

### Paginación

```python
headers = {"PRIVATE-TOKEN": token}
params = {"per_page": 100, "page": 1}
while True:
    r = requests.get(url, headers=headers, params=params)
    results.extend(r.json())
    if not r.headers.get("X-Next-Page"):
        break
    params["page"] = int(r.headers["X-Next-Page"])
```

### Mapeo de conceptos

| GitLab       | Modelo interno |
|--------------|----------------|
| Group        | group          |
| Project      | project        |
| Merge Request| pull_request   |
| Pipeline     | ci_run         |

---

## 4. GitHub

### Permisos del token

Fine-grained (recomendado): `Contents: Read`, `Metadata: Read`,
`Pull requests: Read`, `Issues: Read`, `Actions: Read`

PAT clásico: `repo` (read-only) + `read:org`

### Endpoints principales

```
Base URL: https://api.github.com

GET /orgs/:org/repos?type=all&per_page=100        # repos de una org
GET /users/:user/repos?per_page=100               # repos de un usuario
GET /repos/:owner/:repo/branches?per_page=100     # ramas
GET /repos/:owner/:repo/compare/:base...:head     # divergencia de ramas
GET /repos/:owner/:repo/commits?sha=<branch>      # commits
GET /repos/:owner/:repo/pulls?state=all           # PRs
GET /repos/:owner/:repo/issues?state=all          # issues
GET /repos/:owner/:repo/actions/runs?per_page=20  # CI
GET /repos/:owner/:repo/git/trees/:sha?recursive=1 # árbol de archivos
GET /repos/:owner/:repo/languages                 # lenguajes detectados
```

### Autenticación

```python
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
```

### Paginación (header Link)

```python
while url:
    r = requests.get(url, headers=headers)
    results.extend(r.json())
    links = r.headers.get("Link", "")
    url = next((p.split(";")[0].strip().strip("<>")
                for p in links.split(",") if 'rel="next"' in p), None)
```

### Rate limits

- 5000 req/hora autenticado. Si recibes 403 con `X-RateLimit-Remaining: 0`,
  espera hasta el timestamp en `X-RateLimit-Reset`.
- Clona con `--depth=1` para repos grandes.

### Mapeo de conceptos

| GitHub       | Modelo interno |
|--------------|----------------|
| Organization | group          |
| Repository   | project        |
| Pull Request | pull_request   |
| Actions Run  | ci_run         |

---

## 5. Azure DevOps

### Permisos del token (PAT)

| Análisis               | Scope requerido              |
|------------------------|------------------------------|
| Discovery de proyectos | `Project and Team (read)`    |
| Ramas / commits        | `Code (read)`                |
| Pull Requests          | `Code (read)`                |
| Work Items             | `Work Items (read)`          |
| Pipelines              | `Build (read)`               |
| Clonar repo            | `Code (read)`                |

### Estructura de URL

```
Cloud:       https://dev.azure.com/{org}/{project}/_git/{repo}
On-premise:  https://{server}/{collection}/{project}/_git/{repo}
```

> Azure DevOps tiene una capa adicional: cada **Organization** contiene **Projects** AzDO,
> y cada Project puede tener múltiples **Git Repositories**. Cuando el usuario da solo la org,
> lista primero los Projects y luego los repos de cada uno.

### Endpoints principales

```
Base URL: https://dev.azure.com/{org}

GET /{org}/_apis/projects?api-version=7.1                                    # proyectos
GET /{org}/{project}/_apis/git/repositories?api-version=7.1                  # repos
GET /{org}/{project}/_apis/git/repositories/{repoId}/refs?filter=heads/      # ramas
GET /{org}/{project}/_apis/git/repositories/{repoId}/commits                 # commits
GET /{org}/{project}/_apis/git/repositories/{repoId}/pullrequests?searchCriteria.status=all  # PRs
GET /{org}/{project}/_apis/git/repositories/{repoId}/items?recursionLevel=full  # árbol
GET /{org}/{project}/_apis/pipelines?api-version=7.1                         # pipelines
GET /{org}/{project}/_apis/build/builds?api-version=7.1                      # builds
```

### Autenticación (Basic con PAT)

```python
import base64, requests
credentials = base64.b64encode(f":{token}".encode()).decode()
headers = {"Authorization": f"Basic {credentials}", "Content-Type": "application/json"}
```

### Paginación (continuationToken)

```python
params = {"$top": 100}
while True:
    r = requests.get(url, headers=headers, params=params)
    data = r.json()
    results.extend(data.get("value", []))
    ct = r.headers.get("x-ms-continuationtoken")
    if not ct:
        break
    params["continuationToken"] = ct
```

### Clonar

```
https://anything:{token}@dev.azure.com/{org}/{project}/_git/{repo}
```

### Mapeo de conceptos

| Azure DevOps   | Modelo interno |
|----------------|----------------|
| Organization   | group          |
| Project (AzDO) | sub-group      |
| Repository     | project        |
| Pull Request   | pull_request   |
| Pipeline Run   | ci_run         |
| Work Item      | issue          |

---

## 6. Bitbucket

Bitbucket tiene dos variantes con APIs distintas. El adapter detecta cuál usar por la URL.

### Bitbucket Cloud (bitbucket.org) — API 2.0

**Permisos (App Password o Access Token):**
`Repositories: Read`, `Pull requests: Read`, `Issues: Read`, `Pipelines: Read`

```
Base URL: https://api.bitbucket.org/2.0

GET /repositories/{workspace}?pagelen=100                        # repos del workspace
GET /repositories/{workspace}/{repo}/refs/branches?pagelen=100   # ramas
GET /repositories/{workspace}/{repo}/commits/{branch}            # commits
GET /repositories/{workspace}/{repo}/pullrequests?state=ALL      # PRs
GET /repositories/{workspace}/{repo}/src/{commit}/{path}         # árbol de archivos
GET /repositories/{workspace}/{repo}/pipelines/?sort=-created_on # pipelines
```

**Autenticación Cloud:**
```python
# App Password: usuario:password
auth = (username, app_password)
r = requests.get(url, auth=auth)

# Access Token: Bearer
headers = {"Authorization": f"Bearer {access_token}"}
```

**Paginación Cloud (campo `next`):**
```python
while url:
    r = requests.get(url, auth=auth)
    data = r.json()
    results.extend(data.get("values", []))
    url = data.get("next")
```

### Bitbucket Server/Data Center (self-hosted) — REST API 1.0

```
Base URL: https://{host}/rest/api/1.0

GET /projects/{key}/repos?limit=100                           # repos del proyecto
GET /projects/{key}/repos/{slug}/branches?limit=100           # ramas
GET /projects/{key}/repos/{slug}/commits?limit=100            # commits
GET /projects/{key}/repos/{slug}/pull-requests?state=ALL      # PRs
GET /projects/{key}/repos/{slug}/browse?at={branch}           # árbol de archivos
```

**Autenticación Server:**
```python
headers = {"Authorization": f"Bearer {personal_access_token}"}
```

### Mapeo de conceptos

| Bitbucket Cloud | Bitbucket Server | Modelo interno |
|-----------------|------------------|----------------|
| Workspace       | Project          | group          |
| Repository      | Repository       | project        |
| Pull Request    | Pull Request     | pull_request   |
| Pipeline        | —                | ci_run         |

---

## 7. Detección automática de plataforma

```python
def detect_platform(url: str) -> str:
    u = url.lower()
    if "github.com" in u or "/api/v3" in u:
        return "github"
    if "gitlab" in u or "/api/v4" in u:
        return "gitlab"
    if "dev.azure.com" in u or "visualstudio.com" in u:
        return "azdevops"
    if "bitbucket.org" in u or "bitbucket." in u:
        return "bitbucket"
    return "unknown"
```

Si devuelve `"unknown"`, el skill maestro pregunta al usuario explícitamente.
Acepta: `"gitlab"`, `"github"`, `"azure"` / `"azdevops"`, `"bitbucket"` (case-insensitive).
