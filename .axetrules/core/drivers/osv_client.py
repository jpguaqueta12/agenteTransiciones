"""
scripts/osv_client.py — RepoIntel Suite
Cliente OSV API para detección de CVEs en dependencias de cualquier ecosistema.
API pública, sin autenticación: https://api.osv.dev/v1/

pip install httpx
"""
from __future__ import annotations
import json, re, time
from dataclasses import dataclass, field
import httpx

OSV_BASE = "https://api.osv.dev/v1"


# ── Modelos ───────────────────────────────────────────────────────────────────

@dataclass
class Dependency:
    name: str
    version: str
    ecosystem: str    # npm | PyPI | Maven | NuGet | Go | Packagist | RubyGems | crates.io
    manifest_file: str = ""
    is_direct: bool = True
    scope: str = "runtime"


@dataclass
class CVEFinding:
    vuln_id: str
    package_name: str
    package_version: str
    ecosystem: str
    summary: str
    severity_level: str    # CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN
    severity_score: float  # CVSS 0.0–10.0
    fixed_versions: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    published: str = ""

    @property
    def has_fix(self) -> bool: return bool(self.fixed_versions)

    @property
    def fix_recommendation(self) -> str:
        return f"Actualizar a >= {self.fixed_versions[0]}" if self.fixed_versions \
               else "Sin fix disponible — evaluar alternativa"


@dataclass
class ScanSummary:
    total_scanned: int
    vulnerable_packages: int
    total_findings: int
    by_severity: dict[str, int]
    critical: list[CVEFinding]
    high: list[CVEFinding]
    medium: list[CVEFinding]
    low: list[CVEFinding]
    duration_seconds: float

    @property
    def score(self) -> int:
        s = 100
        s -= min(len(self.critical) * 25, 50)
        s -= min(len(self.high) * 10, 30)
        s -= min(len(self.medium) * 3, 15)
        s -= min(len(self.low), 5)
        return max(0, s)

    @property
    def grade(self) -> str:
        s = self.score
        return "A" if s>=90 else "B" if s>=80 else "C" if s>=60 else "D" if s>=40 else "F"


# ── Cliente ───────────────────────────────────────────────────────────────────

class OSVClient:
    def __init__(self, batch_size: int = 1000, delay: float = 0.5):
        self.batch_size = batch_size
        self.delay = delay
        self._http = httpx.Client(base_url=OSV_BASE, timeout=30.0,
                                  headers={"Content-Type": "application/json"})

    def scan_dependencies(self, deps: list[Dependency]) -> ScanSummary:
        t0 = time.time()
        print(f"🔍 Escaneando {len(deps)} dependencias via OSV API...")
        findings = self._batch_query(deps)

        # Deduplicar
        seen: set[str] = set()
        unique: list[CVEFinding] = []
        for f in findings:
            key = f"{f.vuln_id}:{f.package_name}:{f.package_version}"
            if key not in seen:
                seen.add(key)
                unique.append(f)

        buckets: dict[str, list[CVEFinding]] = {"CRITICAL":[], "HIGH":[], "MEDIUM":[], "LOW":[], "UNKNOWN":[]}
        for f in unique:
            buckets.setdefault(f.severity_level, []).append(f)
        for k in buckets:
            buckets[k].sort(key=lambda x: x.severity_score, reverse=True)

        return ScanSummary(
            total_scanned=len(deps),
            vulnerable_packages=len({f.package_name for f in unique}),
            total_findings=len(unique),
            by_severity={k: len(v) for k, v in buckets.items()},
            critical=buckets["CRITICAL"], high=buckets["HIGH"],
            medium=buckets["MEDIUM"], low=buckets["LOW"],
            duration_seconds=round(time.time() - t0, 2),
        )

    def _batch_query(self, deps: list[Dependency]) -> list[CVEFinding]:
        results: list[CVEFinding] = []
        for i in range(0, len(deps), self.batch_size):
            chunk = deps[i:i + self.batch_size]
            payload = {"queries": [
                {"version": d.version, "package": {"name": d.name, "ecosystem": d.ecosystem}}
                for d in chunk
            ]}
            try:
                resp = self._http.post("/querybatch", json=payload)
                resp.raise_for_status()
                data = resp.json()
                for dep, res in zip(chunk, data.get("results", [])):
                    for vuln in res.get("vulns", []):
                        results.append(self._parse(vuln, dep))
            except httpx.HTTPError:
                # Fallback individual
                for dep in chunk:
                    results.extend(self._single_query(dep))
            if i + self.batch_size < len(deps):
                time.sleep(self.delay)
        return results

    def _single_query(self, dep: Dependency) -> list[CVEFinding]:
        try:
            resp = self._http.post("/query", json={
                "version": dep.version,
                "package": {"name": dep.name, "ecosystem": dep.ecosystem}
            })
            resp.raise_for_status()
            return [self._parse(v, dep) for v in resp.json().get("vulns", [])]
        except httpx.HTTPError:
            return []

    def _parse(self, raw: dict, dep: Dependency) -> CVEFinding:
        score, level = self._severity(raw)
        aliases = raw.get("aliases", [])
        vuln_id = next((a for a in aliases if a.startswith("CVE-")), raw["id"])
        fixed = self._fixed_versions(raw, dep)
        refs = [r["url"] for r in raw.get("references", []) if r.get("url")][:5]
        return CVEFinding(
            vuln_id=vuln_id, package_name=dep.name, package_version=dep.version,
            ecosystem=dep.ecosystem, summary=raw.get("summary", "Sin descripción")[:200],
            severity_level=level, severity_score=score,
            fixed_versions=fixed, references=refs, published=raw.get("published",""),
        )

    def _severity(self, raw: dict) -> tuple[float, str]:
        for sev in raw.get("severity", []):
            if sev.get("type") in ("CVSS_V3", "CVSS_V4"):
                score = self._parse_score(sev.get("score",""))
                return score, self._level(score)
        db = raw.get("database_specific", {})
        if "cvss" in db:
            score = float(db["cvss"].get("score", 0))
            return score, db["cvss"].get("severity", self._level(score)).upper()
        return 0.0, "UNKNOWN"

    @staticmethod
    def _parse_score(s: str) -> float:
        try: return float(s)
        except ValueError: return 5.0  # MEDIUM como fallback

    @staticmethod
    def _level(score: float) -> str:
        if score >= 9.0: return "CRITICAL"
        if score >= 7.0: return "HIGH"
        if score >= 4.0: return "MEDIUM"
        if score > 0.0:  return "LOW"
        return "UNKNOWN"

    @staticmethod
    def _fixed_versions(raw: dict, dep: Dependency) -> list[str]:
        fixed: list[str] = []
        for affected in raw.get("affected", []):
            if affected.get("package", {}).get("ecosystem") != dep.ecosystem: continue
            for r in affected.get("ranges", []):
                for e in r.get("events", []):
                    if "fixed" in e: fixed.append(e["fixed"])
        return sorted(set(fixed))

    def __enter__(self): return self
    def __exit__(self, *_): self._http.close()


# ── Parsers de manifiestos ────────────────────────────────────────────────────

def parse_package_json(content: str) -> list[Dependency]:
    data = json.loads(content)
    deps: list[Dependency] = []
    def clean(v: str) -> str: return v.lstrip("^~>=<").split(" ")[0].split("-")[0].split("+")[0]
    for name, ver in data.get("dependencies", {}).items():
        deps.append(Dependency(name, clean(ver), "npm", "package.json", True, "runtime"))
    for name, ver in data.get("devDependencies", {}).items():
        deps.append(Dependency(name, clean(ver), "npm", "package.json", True, "dev"))
    return deps


def parse_requirements_txt(content: str) -> list[Dependency]:
    deps: list[Dependency] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-r", "-c", "--")): continue
        m = re.match(r'^([A-Za-z0-9_\-\.]+)(?:\[.*?\])?[><=~!]+([0-9][^\s;,]*)', line)
        if m:
            deps.append(Dependency(m.group(1).lower(), m.group(2).split(",")[0].strip(),
                                   "PyPI", "requirements.txt", True))
    return deps


def parse_pom_xml(content: str) -> list[Dependency]:
    import xml.etree.ElementTree as ET
    deps: list[Dependency] = []
    try:
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}
        root = ET.fromstring(content)
        for d in root.findall(".//m:dependency", ns):
            g = d.findtext("m:groupId", namespaces=ns) or ""
            a = d.findtext("m:artifactId", namespaces=ns) or ""
            v = d.findtext("m:version", namespaces=ns) or ""
            scope = d.findtext("m:scope", namespaces=ns) or "compile"
            if g and a and v and not v.startswith("${"):
                deps.append(Dependency(f"{g}:{a}", v, "Maven", "pom.xml", True,
                                       "dev" if scope == "test" else "runtime"))
    except ET.ParseError: pass
    return deps


def parse_go_mod(content: str) -> list[Dependency]:
    deps: list[Dependency] = []
    in_req = False
    for line in content.splitlines():
        line = line.strip()
        if "require (" in line: in_req = True; continue
        if in_req and line == ")": in_req = False; continue
        target = line.replace("require ", "").strip() if line.startswith("require ") else (line if in_req else "")
        if target and not target.startswith("//"):
            parts = target.split()
            if len(parts) >= 2:
                deps.append(Dependency(parts[0], parts[1].lstrip("v"), "Go", "go.mod", True))
    return deps


def detect_and_parse_manifest(filename: str, content: str) -> list[Dependency]:
    """Router: detecta el tipo de manifiesto y parsea las dependencias."""
    import os
    basename = os.path.basename(filename).lower()
    parsers = {
        "package.json":     parse_package_json,
        "requirements.txt": parse_requirements_txt,
        "pom.xml":          parse_pom_xml,
        "go.mod":           parse_go_mod,
    }
    parser = parsers.get(basename)
    if parser:
        try: return parser(content)
        except Exception as e:
            print(f"⚠️  Error parseando {filename}: {e}")
    return []


# ── Formateo de reporte ───────────────────────────────────────────────────────

def format_summary_report(s: ScanSummary) -> str:
    lines = [
        "", "🔒 REPORTE DE VULNERABILIDADES — OSV API", "━" * 50,
        f"  Paquetes escaneados:   {s.total_scanned}",
        f"  Paquetes vulnerables:  {s.vulnerable_packages}",
        f"  Total hallazgos:       {s.total_findings}",
        f"  Score de seguridad:    {s.score}/100  [{s.grade}]",
        f"  Tiempo de escaneo:     {s.duration_seconds}s",
        "",
        f"  🔴 CRÍTICO: {s.by_severity.get('CRITICAL',0)}  "
        f"🟠 ALTO: {s.by_severity.get('HIGH',0)}  "
        f"🟡 MEDIO: {s.by_severity.get('MEDIUM',0)}  "
        f"🔵 BAJO: {s.by_severity.get('LOW',0)}",
        "",
    ]
    for f in (s.critical + s.high)[:10]:
        icon = "🔴" if f.severity_level == "CRITICAL" else "🟠"
        lines += [
            f"  {icon} {f.vuln_id}  —  {f.package_name} {f.package_version}  (CVSS {f.severity_score})",
            f"     {f.summary[:80]}",
            f"     {f.fix_recommendation}", "",
        ]
    return "\n".join(lines)
