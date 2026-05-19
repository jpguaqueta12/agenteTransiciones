# Analysis Components — RepoIntel

Mapeo entre opciones del menú, skills especializados y scripts Python a ejecutar.
Leído por el orquestador en la Fase 4 (ejecución del análisis).

---

## Tabla de componentes

| Opción | Skill SKILL.md                              | Script principal            | Requiere clon | Tiempo aprox. |
|--------|---------------------------------------------|-----------------------------|---------------|---------------|
| 1      | `../../skills/branch-analyzer/SKILL.md`           | Solo API (no script)        | No            | 5-15s         |
| 2      | `../../skills/api-contract-scanner/SKILL.md`      | `local_analyzer.py`         | Sí (depth=1)  | 20-60s        |
| 3      | `../../skills/dependency-graph/SKILL.md`          | `local_analyzer.py` + `osv_client.py` | Sí (depth=1) | 30-90s |
| 4      | `../../skills/stack-profiler/SKILL.md`            | `local_analyzer.py`         | Sí (depth=1)  | 15-40s        |
| 5      | `../../skills/security-scanner/SKILL.md`          | `local_analyzer.py` + `osv_client.py` | Sí (depth=1) | 30-120s|
| 6      | `../../skills/activity-reporter/SKILL.md`         | Solo API (no script)        | Opcional      | 15-45s        |
| 7      | *(calidad — parte de stack-profiler)*       | `local_analyzer.py`         | Sí (depth=1)  | 10-30s        |
| 8      | `../../skills/architecture-analyzer/SKILL.md`     | `local_analyzer.py` → `ArchitectureAnalyzer` | Sí (depth=1) | 30-90s |
| 9      | `../../skills/volumetry-analyzer/SKILL.md`        | `volumetry_analyzer.py`     | Sí (depth=1 + git log para hotspots) | 60-180s |
| 10     | Análisis completo                           | Todos los anteriores        | Sí (depth=1)  | 5-12 min      |

---

## Secuencia recomendada para el análisis completo (opción 7)

Ejecutar en este orden para reutilizar el clon y minimizar llamadas a API:

```
1. stack-profiler       → Detecta el stack (útil para los siguientes módulos)
2. dependency-graph     → Usa el clon ya disponible
3. security-scanner     → Reutiliza manifiestos del paso anterior
4. api-contract-scanner → Reutiliza el clon
5. branch-analyzer      → Solo API, siempre rápido
6. activity-reporter    → Solo API
```

---

## Preparación del entorno (ejecutar una sola vez)

```bash
pip install httpx pydantic gitpython pyyaml rich --break-system-packages
git --version
mkdir -p /tmp/repo-intel
```

---

## Scripts disponibles

### `../../scripts/platform_client.py`
- `PlatformClient(context)` — constructor
- `.get_branches()` → `list[BranchInfo]`
- `.get_pull_requests(state)` → `list[PullRequestInfo]`
- `.get_commits(branch, since)` → `list[CommitInfo]`
- `.get_file_content(path)` → `str`
- `.get_file_tree()` → `list[str]`
- `.list_projects_in_group(group)` → `list[ProjectInfo]`
- `PlatformClient.detect_platform(url)` → `str` (método de clase)

### `../../scripts/local_analyzer.py`
- `LocalAnalyzer(clone_path)` — constructor
- `.detect_stack()` → `StackProfile`
- `.analyze_quality()` → `ProjectQuality`
- `.scan_secrets()` → `list[SecretFinding]`
- `.find_manifest_files()` → `list[tuple[str, str]]`

### `../../scripts/osv_client.py`
- `OSVClient().scan_dependencies(deps)` → `ScanSummary`
- `detect_and_parse_manifest(filename, content)` → `list[Dependency]`
- `format_summary_report(summary)` → `str`

---

## Integración típica entre scripts

```python
from scripts.platform_client import PlatformClient, RepoContext
from scripts.local_analyzer import LocalAnalyzer
from scripts.osv_client import OSVClient, detect_and_parse_manifest
import subprocess

context = RepoContext(
    platform=PlatformClient.detect_platform(base_url),
    base_url=base_url, token=token,
    project_id=project_id, project_name=project_name,
    project_url=project_url,
)

subprocess.run(["git", "clone", "--depth", "1",
    f"https://oauth2:{token}@{project_url.replace('https://', '')}",
    context.clone_path], check=True)

analyzer = LocalAnalyzer(context.clone_path)
stack    = analyzer.detect_stack()
secrets  = analyzer.scan_secrets()
manifests = analyzer.find_manifest_files()

all_deps = []
for filename, content in manifests:
    all_deps.extend(detect_and_parse_manifest(filename, content))

with OSVClient() as osv:
    cve_summary = osv.scan_dependencies(all_deps)

with PlatformClient(context) as client:
    branches = client.get_branches()
    prs      = client.get_pull_requests("open")
```
