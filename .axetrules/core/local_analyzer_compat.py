import os
from pathlib import Path
from .models.models import StackProfile, ProjectQuality, SecretFinding, ArchitectureReport

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", ".next",
    "vendor", "target", "bin", "obj", ".terraform", "coverage",
    ".nyc_output", "venv", ".venv", "env", ".gradle", "out",
}
IGNORE_EXTS = {
    ".min.js", ".min.css", ".map", ".lock", ".sum",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".woff", ".woff2", ".ttf",
}
MANIFEST_NAMES = {
    "package.json","requirements.txt","pom.xml","build.gradle","go.mod",
    "composer.json","Gemfile","Cargo.toml","pyproject.toml","setup.py",
}

class LocalAnalyzerCompat:
    def __init__(self, repo_path: str):
        self.root = Path(repo_path)
        if not self.root.exists():
            raise FileNotFoundError(f"Repo no encontrado: {repo_path}")
        self._files = None
        self._manifest_cache = {}

    def all_files(self):
        if self._files is not None: return self._files
        result = []
        for p in self.root.rglob("*"):
            if p.is_file():
                if not set(p.parts).intersection(IGNORE_DIRS):
                    if p.suffix.lower() not in IGNORE_EXTS:
                        result.append(p)
        self._files = result
        return result

    def read_safe(self, path: Path, max_bytes: int = 100_000) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_bytes)
        except OSError:
            return ""

    def manifest(self, name: str) -> str:
        if name in self._manifest_cache: return self._manifest_cache[name]
        for f in self.all_files():
            if f.name == name:
                c = self.read_safe(f)
                self._manifest_cache[name] = c
                return c
        return ""

    def _all_manifest_text(self) -> str:
        return " ".join(self.manifest(n) for n in MANIFEST_NAMES)

    # Delegation to Engines
    def detect_stack(self) -> StackProfile:
        from .engines.stack_engine import StackEngine
        return StackEngine(self).get_profile()

    def analyze_quality(self) -> ProjectQuality:
        from .engines.quality_engine import QualityEngine
        return QualityEngine(self).get_quality()

    def scan_secrets(self) -> list[SecretFinding]:
        from .engines.security_engine import SecurityEngine
        return SecurityEngine(self).scan_secrets()

    def analyze_architecture(self) -> ArchitectureReport:
        from .engines.arch_engine import ArchEngine
        return ArchEngine(self).analyze()
