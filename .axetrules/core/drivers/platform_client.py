"""
scripts/platform_client.py — RepoIntel Suite
Cliente HTTP normalizado para GitLab, GitHub, Azure DevOps y Bitbucket.

pip install httpx pydantic
"""
from __future__ import annotations
import base64, re, time
from dataclasses import dataclass, field
from typing import Any, Generator, Optional
from urllib.parse import quote_plus
import httpx


# ── Modelos ──────────────────────────────────────────────────────────────────

@dataclass
class RepoContext:
    platform: str        # gitlab | github | azure | bitbucket
    base_url: str
    token: str
    project_id: str      # ID numérico o "namespace/project"
    project_name: str
    project_url: str     # URL HTTP del repo (para git clone)
    default_branch: str = "main"
    clone_path: str = ""

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")
        if not self.clone_path:
            self.clone_path = f"/tmp/repo-intel/{self.project_name}"


@dataclass
class BranchInfo:
    name: str
    last_commit_sha: str
    last_commit_date: str
    last_commit_author: str
    last_commit_message: str
    is_default: bool = False
    is_protected: bool = False
    ahead: int = 0
    behind: int = 0


@dataclass
class PullRequestInfo:
    id: str
    title: str
    author: str
    source_branch: str
    target_branch: str
    created_at: str
    updated_at: str
    state: str
    is_draft: bool = False
    reviewers: list[str] = field(default_factory=list)
    comment_count: int = 0
    url: str = ""


@dataclass
class CommitInfo:
    sha: str
    message: str
    author_name: str
    author_email: str
    authored_at: str
    url: str = ""


@dataclass
class ProjectInfo:
    id: str
    name: str
    description: str
    default_branch: str
    clone_url_https: str
    web_url: str
    last_activity: str
    visibility: str
    stars: int = 0
    forks: int = 0


# ── Cliente ───────────────────────────────────────────────────────────────────

class PlatformClient:
    PLATFORM_DETECTORS = {
        "gitlab":    [r"gitlab\.com", r"gitlab\.", r"umane\.emeal\.nttdata\.com"],
        "github":    [r"github\.com", r"api\.github\.com"],
        "azure":     [r"dev\.azure\.com", r"visualstudio\.com"],
        "bitbucket": [r"bitbucket\.org", r"bitbucket\."],
    }

    def __init__(self, context: RepoContext):
        self.ctx = context
        self.platform = context.platform
        self._client = self._build_client()

    @classmethod
    def detect_platform(cls, url: str) -> str:
        for platform, patterns in cls.PLATFORM_DETECTORS.items():
            if any(re.search(p, url.lower()) for p in patterns):
                return platform
        raise ValueError(f"Plataforma no reconocida en URL: {url}")

    def _build_client(self) -> httpx.Client:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.platform == "gitlab":
            headers["PRIVATE-TOKEN"] = self.ctx.token
        elif self.platform == "github":
            headers["Authorization"] = f"Bearer {self.ctx.token}"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        elif self.platform == "azure":
            enc = base64.b64encode(f":{self.ctx.token}".encode()).decode()
            headers["Authorization"] = f"Basic {enc}"
        elif self.platform == "bitbucket":
            headers["Authorization"] = f"Bearer {self.ctx.token}"
        return httpx.Client(headers=headers, timeout=30.0, follow_redirects=True)

    def _get(self, url: str, params: dict | None = None) -> Any:
        for attempt in range(3):
            try:
                resp = self._client.get(url, params=params)
                if resp.status_code == 429:
                    time.sleep(int(resp.headers.get("Retry-After", "60")))
                    continue
                resp.raise_for_status()
                
                # Check if response has content before parsing JSON
                if not resp.content:
                    raise ValueError(f"Respuesta vacía del servidor: {url}")
                
                # Check content type
                content_type = resp.headers.get("content-type", "")
                if "application/json" not in content_type:
                    # Log first 500 chars of response for debugging
                    preview = resp.text[:500] if resp.text else "(vacío)"
                    raise ValueError(f"Respuesta no-JSON recibida. Content-Type: {content_type}\nPreview: {preview}")
                
                return resp.json()
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                body_preview = e.response.text[:200] if e.response.text else "(vacío)"
                if code == 401: raise PermissionError(f"Token inválido o expirado. Response: {body_preview}")
                if code == 403: raise PermissionError(f"Token sin permisos suficientes (necesita read_api + read_repository). Response: {body_preview}")
                if code == 404: raise FileNotFoundError(f"No encontrado: {url}. Response: {body_preview}")
                raise RuntimeError(f"HTTP {code}: {body_preview}")
            except ValueError as e:
                # JSON decode or empty response errors
                raise RuntimeError(f"Error parseando respuesta de {url}: {str(e)}")
        raise RuntimeError(f"Fallo tras 3 intentos: {url}")

    def _paginate(self, url: str, params: dict | None = None) -> Generator[dict, None, None]:
        params = dict(params or {})
        page = 1
        while True:
            if self.platform in ("gitlab", "github"):
                params.update({"page": page, "per_page": 100})
                data = self._get(url, params)
                if not data: break
                yield from data
                page += 1
            elif self.platform == "azure":
                params.update({"$skip": (page - 1) * 100, "$top": 100})
                data = self._get(url, params)
                items = data.get("value", [])
                if not items: break
                yield from items
                if len(items) < 100: break
                page += 1
            elif self.platform == "bitbucket":
                data = self._get(url, params)
                yield from data.get("values", [])
                next_url = data.get("next")
                if not next_url: break
                url, params = next_url, {}

    # ── API pública ───────────────────────────────────────────────────────────

    def get_project_info(self) -> ProjectInfo:
        return self._normalize_project(self._get(self._project_url()))

    def list_projects_in_group(self, group: str) -> list[ProjectInfo]:
        if self.platform == "github":
            # GitHub distingue usuarios de organizaciones — probar ambos endpoints.
            projects: list[ProjectInfo] = []
            seen: set = set()
            for url in [
                f"https://api.github.com/users/{group}/repos",
                f"https://api.github.com/orgs/{group}/repos",
            ]:
                try:
                    for r in self._paginate(url, {"sort": "pushed", "type": "all"}):
                        p = self._normalize_project(r)
                        if p.id not in seen:
                            seen.add(p.id)
                            projects.append(p)
                except Exception:
                    pass
            return sorted(projects, key=lambda p: p.last_activity or "", reverse=True)
        url = self._list_projects_url(group)
        return [self._normalize_project(p) for p in self._paginate(url)]

    def get_branches(self) -> list[BranchInfo]:
        return [self._normalize_branch(b) for b in self._paginate(self._branches_url())]

    def get_pull_requests(self, state: str = "open") -> list[PullRequestInfo]:
        return [self._normalize_pr(p) for p in self._paginate(self._prs_url(state))]

    def get_commits(self, branch: str | None = None, since: str | None = None,
                    limit: int = 200) -> list[CommitInfo]:
        url = self._commits_url(branch or self.ctx.default_branch)
        params = {"since": since} if since else {}
        raw: list[dict] = []
        for c in self._paginate(url, params):
            raw.append(c)
            if len(raw) >= limit: break
        return [self._normalize_commit(c) for c in raw]

    def get_file_content(self, file_path: str, branch: str | None = None) -> str:
        raw = self._get(self._file_url(file_path, branch or self.ctx.default_branch))
        return self._decode_file(raw)

    def get_file_tree(self) -> list[str]:
        items = list(self._paginate(self._tree_url()))
        return [i.get("path") or i.get("name") or "" for i in items
                if i.get("type") in ("blob", "file", None)]

    def get_releases(self) -> list[dict]:
        return list(self._paginate(self._releases_url()))

    def get_members(self) -> list[dict]:
        return list(self._paginate(self._members_url()))

    # ── URL builders ──────────────────────────────────────────────────────────

    def _enc(self, s: str) -> str: return quote_plus(s)

    def _azure_parts(self) -> tuple[str, str, str]:
        parts = self.ctx.project_id.split("/")
        if len(parts) != 3:
            raise ValueError("Azure project_id debe ser 'org/project/repo'")
        return parts[0], parts[1], parts[2]

    def _project_url(self) -> str:
        pid = self._enc(self.ctx.project_id)
        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/projects/{pid}"
        if self.platform == "github":
            return f"https://api.github.com/repos/{self.ctx.project_id}"
        if self.platform == "azure":
            o, p, r = self._azure_parts()
            return f"https://dev.azure.com/{o}/{p}/_apis/git/repositories/{r}?api-version=7.0"
        if self.platform == "bitbucket":
            ws, sl = self.ctx.project_id.split("/")
            return f"https://api.bitbucket.org/2.0/repositories/{ws}/{sl}"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _branches_url(self) -> str:
        pid = self._enc(self.ctx.project_id)
        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/projects/{pid}/repository/branches"
        if self.platform == "github":
            return f"https://api.github.com/repos/{self.ctx.project_id}/branches"
        if self.platform == "azure":
            o, p, r = self._azure_parts()
            return f"https://dev.azure.com/{o}/{p}/_apis/git/repositories/{r}/refs?filter=heads&api-version=7.0"
        if self.platform == "bitbucket":
            ws, sl = self.ctx.project_id.split("/")
            return f"https://api.bitbucket.org/2.0/repositories/{ws}/{sl}/refs/branches"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _commits_url(self, branch: str) -> str:
        pid = self._enc(self.ctx.project_id)
        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/projects/{pid}/repository/commits?ref_name={branch}"
        if self.platform == "github":
            return f"https://api.github.com/repos/{self.ctx.project_id}/commits?sha={branch}"
        if self.platform == "azure":
            o, p, r = self._azure_parts()
            return (
                f"https://dev.azure.com/{o}/{p}/_apis/git/repositories/{r}/commits"
                f"?searchCriteria.itemVersion.version={branch}&api-version=7.0"
            )
        if self.platform == "bitbucket":
            ws, sl = self.ctx.project_id.split("/")
            return f"https://api.bitbucket.org/2.0/repositories/{ws}/{sl}/commits/{branch}"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _prs_url(self, state: str) -> str:
        state_map = {
            "gitlab": {"open": "opened", "merged": "merged", "closed": "closed"},
            "github": {"open": "open", "merged": "closed", "closed": "closed"},
            "azure": {"open": "active", "merged": "completed", "closed": "abandoned"},
            "bitbucket": {"open": "OPEN", "merged": "MERGED", "closed": "DECLINED"},
        }
        s = state_map[self.platform][state]
        pid = self._enc(self.ctx.project_id)

        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/projects/{pid}/merge_requests?state={s}"
        if self.platform == "github":
            return f"https://api.github.com/repos/{self.ctx.project_id}/pulls?state={s}"
        if self.platform == "azure":
            o, p, r = self._azure_parts()
            return (
                f"https://dev.azure.com/{o}/{p}/_apis/git/repositories/{r}"
                f"/pullrequests?searchCriteria.status={s}&api-version=7.0"
            )
        if self.platform == "bitbucket":
            ws, sl = self.ctx.project_id.split("/")
            return f"https://api.bitbucket.org/2.0/repositories/{ws}/{sl}/pullrequests?state={s}"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _file_url(self, path: str, branch: str) -> str:
        pid = self._enc(self.ctx.project_id)
        enc_path = self._enc(path)

        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/projects/{pid}/repository/files/{enc_path}?ref={branch}"
        if self.platform == "github":
            return f"https://api.github.com/repos/{self.ctx.project_id}/contents/{path}?ref={branch}"
        if self.platform == "azure":
            o, p, r = self._azure_parts()
            return (
                f"https://dev.azure.com/{o}/{p}/_apis/git/repositories/{r}/items"
                f"?path={path}&versionDescriptor.version={branch}&api-version=7.0"
            )
        if self.platform == "bitbucket":
            ws, sl = self.ctx.project_id.split("/")
            return f"https://api.bitbucket.org/2.0/repositories/{ws}/{sl}/src/{branch}/{path}"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _tree_url(self) -> str:
        pid = self._enc(self.ctx.project_id)

        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/projects/{pid}/repository/tree?recursive=true"
        if self.platform == "github":
            return f"https://api.github.com/repos/{self.ctx.project_id}/git/trees/{self.ctx.default_branch}?recursive=1"
        if self.platform == "azure":
            o, p, r = self._azure_parts()
            return (
                f"https://dev.azure.com/{o}/{p}/_apis/git/repositories/{r}/trees/{self.ctx.default_branch}"
                f"?recursive=true&api-version=7.0"
            )
        if self.platform == "bitbucket":
            ws, sl = self.ctx.project_id.split("/")
            return f"https://api.bitbucket.org/2.0/repositories/{ws}/{sl}/src/{self.ctx.default_branch}/"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _releases_url(self) -> str:
        pid = self._enc(self.ctx.project_id)

        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/projects/{pid}/releases"
        if self.platform == "github":
            return f"https://api.github.com/repos/{self.ctx.project_id}/releases"
        if self.platform == "azure":
            o, p, _ = self._azure_parts()
            return f"https://dev.azure.com/{o}/{p}/_apis/pipelines?api-version=7.0"
        if self.platform == "bitbucket":
            ws, sl = self.ctx.project_id.split("/")
            return f"https://api.bitbucket.org/2.0/repositories/{ws}/{sl}/refs/tags"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _members_url(self) -> str:
        pid = self._enc(self.ctx.project_id)

        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/projects/{pid}/members"
        if self.platform == "github":
            return f"https://api.github.com/repos/{self.ctx.project_id}/collaborators"
        if self.platform == "azure":
            o, p, _ = self._azure_parts()
            return f"https://dev.azure.com/{o}/_apis/projects/{p}/teams?api-version=7.0"
        if self.platform == "bitbucket":
            ws, sl = self.ctx.project_id.split("/")
            return f"https://api.bitbucket.org/2.0/repositories/{ws}/{sl}/permissions-config/users"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _list_projects_url(self, group: str) -> str:
        if self.platform == "gitlab":
            return f"{self.ctx.base_url}/api/v4/groups/{self._enc(group)}/projects?include_subgroups=true"
        if self.platform == "github":
            return f"https://api.github.com/orgs/{group}/repos?type=all"
        if self.platform == "azure":
            return f"https://dev.azure.com/{group}/_apis/projects?api-version=7.0"
        if self.platform == "bitbucket":
            return f"https://api.bitbucket.org/2.0/repositories/{group}"
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    # ── Normalizadores ────────────────────────────────────────────────────────

    def _normalize_project(self, r: dict) -> ProjectInfo:
        if self.platform == "gitlab":
            return ProjectInfo(
                str(r["id"]),
                r["name"],
                r.get("description") or "",
                r.get("default_branch", "main"),
                r["http_url_to_repo"],
                r["web_url"],
                r.get("last_activity_at", ""),
                r.get("visibility", "private"),
                r.get("star_count", 0),
                r.get("forks_count", 0),
            )
        if self.platform == "github":
            return ProjectInfo(
                str(r["id"]),
                r["name"],
                r.get("description") or "",
                r.get("default_branch", "main"),
                r["clone_url"],
                r["html_url"],
                r.get("pushed_at", ""),
                "public" if not r.get("private") else "private",
                r.get("stargazers_count", 0),
                r.get("forks_count", 0),
            )
        if self.platform == "azure":
            return ProjectInfo(
                r["id"],
                r["name"],
                r.get("description") or "",
                r.get("defaultBranch", "refs/heads/main").replace("refs/heads/", ""),
                r.get("remoteUrl", ""),
                r.get("webUrl", ""),
                "",
                "private",
            )
        if self.platform == "bitbucket":
            clone_url = next(
                (
                    c["href"]
                    for c in r.get("links", {}).get("clone", [])
                    if c.get("name") == "https"
                ),
                "",
            )
            return ProjectInfo(
                r["slug"],
                r["name"],
                r.get("description") or "",
                r.get("mainbranch", {}).get("name", "main"),
                clone_url,
                r.get("links", {}).get("html", {}).get("href", ""),
                r.get("updated_on", ""),
                "public" if r.get("is_private") is False else "private",
            )
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _normalize_branch(self, r: dict) -> BranchInfo:
        if self.platform == "gitlab":
            c = r.get("commit", {})
            return BranchInfo(
                r["name"],
                c.get("id", ""),
                c.get("committed_date", ""),
                c.get("author_name", ""),
                (c.get("message") or "")[:100],
                r.get("default", False),
                r.get("protected", False),
            )
        if self.platform == "github":
            c = r.get("commit", {}).get("commit", {})
            a = c.get("author", {})
            return BranchInfo(
                r["name"],
                r["commit"]["sha"],
                a.get("date", ""),
                a.get("name", ""),
                (c.get("message") or "")[:100],
                False,
                r.get("protected", False),
            )
        if self.platform == "azure":
            return BranchInfo(
                r["name"].replace("refs/heads/", ""),
                r.get("objectId", ""),
                "",
                r.get("creator", {}).get("displayName", ""),
                "",
            )
        if self.platform == "bitbucket":
            t = r.get("target", {})
            return BranchInfo(
                r["name"],
                t.get("hash", ""),
                t.get("date", ""),
                t.get("author", {}).get("raw", ""),
                (t.get("message") or "")[:100],
            )
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _normalize_pr(self, r: dict) -> PullRequestInfo:
        if self.platform == "gitlab":
            return PullRequestInfo(
                str(r["iid"]),
                r["title"],
                r.get("author", {}).get("name", ""),
                r["source_branch"],
                r["target_branch"],
                r["created_at"],
                r["updated_at"],
                r["state"],
                r.get("draft", False) or r["title"].startswith("Draft:"),
                [x["name"] for x in r.get("reviewers", [])],
                r.get("user_notes_count", 0),
                r.get("web_url", ""),
            )
        if self.platform == "github":
            return PullRequestInfo(
                str(r["number"]),
                r["title"],
                r.get("user", {}).get("login", ""),
                r["head"]["ref"],
                r["base"]["ref"],
                r["created_at"],
                r["updated_at"],
                r["state"],
                r.get("draft", False),
                [x["login"] for x in r.get("requested_reviewers", [])],
                r.get("comments", 0),
                r.get("html_url", ""),
            )
        if self.platform == "azure":
            return PullRequestInfo(
                str(r["pullRequestId"]),
                r["title"],
                r.get("createdBy", {}).get("displayName", ""),
                r["sourceRefName"].replace("refs/heads/", ""),
                r["targetRefName"].replace("refs/heads/", ""),
                r["creationDate"],
                r.get("closedDate", r["creationDate"]),
                r["status"],
                r.get("isDraft", False),
                [x["displayName"] for x in r.get("reviewers", [])],
            )
        if self.platform == "bitbucket":
            return PullRequestInfo(
                str(r["id"]),
                r["title"],
                r.get("author", {}).get("display_name", ""),
                r["source"]["branch"]["name"],
                r["destination"]["branch"]["name"],
                r["created_on"],
                r["updated_on"],
                r["state"],
                reviewers=[x["user"]["display_name"] for x in r.get("reviewers", [])],
                comment_count=r.get("comment_count", 0),
                url=r.get("links", {}).get("html", {}).get("href", ""),
            )
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _normalize_commit(self, r: dict) -> CommitInfo:
        if self.platform == "gitlab":
            return CommitInfo(
                r["id"],
                (r.get("message") or "")[:120],
                r.get("author_name", ""),
                r.get("author_email", ""),
                r.get("authored_date", ""),
                r.get("web_url", ""),
            )
        if self.platform == "github":
            c = r.get("commit", {})
            a = c.get("author", {})
            return CommitInfo(
                r["sha"],
                (c.get("message") or "")[:120],
                a.get("name", ""),
                a.get("email", ""),
                a.get("date", ""),
                r.get("html_url", ""),
            )
        if self.platform == "azure":
            a = r.get("author", {})
            return CommitInfo(
                r["commitId"],
                (r.get("comment") or "")[:120],
                a.get("name", ""),
                a.get("email", ""),
                a.get("date", ""),
            )
        if self.platform == "bitbucket":
            return CommitInfo(
                r["hash"],
                (r.get("message") or "")[:120],
                r.get("author", {}).get("raw", ""),
                "",
                r.get("date", ""),
            )
        raise ValueError(f"Plataforma no soportada: {self.platform}")

    def _decode_file(self, raw: dict) -> str:
        if self.platform in ("gitlab", "github"):
            content = raw.get("content","")
            if raw.get("encoding") == "base64":
                return base64.b64decode(content.replace("\n","")).decode("utf-8","replace")
            return content
        return raw if isinstance(raw, str) else raw.get("content", str(raw))

    def __enter__(self): return self
    def __exit__(self, *_): self._client.close()
