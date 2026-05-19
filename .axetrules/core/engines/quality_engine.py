import re
from typing import Tuple
from ..models.models import ProjectQuality
from .stack_engine import LANGUAGE_MAP

class QualityEngine:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def analyze_tests(self, manifest_text: str) -> Tuple[bool, float, str]:
        test_re = re.compile(r"(test|spec|__tests__|_test\.py|\.test\.|\.spec\.)", re.I)
        all_f = self.analyzer.all_files()
        test_files = [f for f in all_f if test_re.search(str(f))]
        code_files = [f for f in all_f if f.suffix in LANGUAGE_MAP]
        ratio = len(test_files) / max(len(code_files), 1)
        
        dep = manifest_text
        fw = ("Jest" if '"jest"' in dep else "Vitest" if '"vitest"' in dep
              else "Mocha" if '"mocha"' in dep else "Pytest" if "pytest" in dep
              else "JUnit" if "junit" in dep.lower() else "NUnit" if "nunit" in dep.lower()
              else "Desconocido")
        return len(test_files) > 0, round(ratio, 2), fw

    def get_quality(self) -> ProjectQuality:
        has_readme = any(f.name in ("README.md","README.rst") for f in self.analyzer.all_files())
        readme_score = self._readme_score(self.analyzer.manifest("README.md")) if has_readme else 0
        
        manifest_text = self.analyzer._all_manifest_text()
        has_tests, ratio, _ = self.analyze_tests(manifest_text)
        
        from .stack_engine import StackEngine
        stack = StackEngine(self.analyzer)
        infra = stack.detect_infrastructure()
        
        file_names = {f.name for f in self.analyzer.all_files()}
        has_ci = any(c in infra for c in ["GitHub Actions","GitLab CI","Azure Pipelines","Jenkins"])
        
        score = sum([
            15 if has_readme else 0,
            int(readme_score * 0.10),
            20 if has_tests else 0,
            min(int(ratio * 50), 15),
            10 if has_ci else 0,
            5 if "Docker" in infra else 0,
            5 if ".env.example" in file_names else 0,
            5 if ".gitignore" in file_names else 0,
            5 if "LICENSE" in file_names or "LICENSE.md" in file_names else 0,
            5 if any(l in infra for l in ["ESLint","Pylint"]) else 0,
        ])
        
        return ProjectQuality(
            has_readme=has_readme, readme_score=readme_score,
            has_tests=has_tests, test_ratio=ratio,
            has_linting=any(l in infra for l in ["ESLint","Pylint"]),
            has_ci_cd=has_ci, has_dockerfile="Docker" in infra,
            has_env_example=".env.example" in file_names,
            has_gitignore=".gitignore" in file_names,
            has_license="LICENSE" in file_names or "LICENSE.md" in file_names,
            has_changelog="CHANGELOG.md" in file_names or "CHANGELOG" in file_names,
            overall_score=min(100, score),
        )

    def _readme_score(self, content: str) -> int:
        s = 0
        if len(content) > 200:         s += 20
        if "## " in content:           s += 10
        if re.search(r"install|setup", content, re.I): s += 15
        if re.search(r"usage|example", content, re.I): s += 15
        if "```" in content:           s += 15
        if re.search(r"badge|!\[",     content, re.I): s += 10
        if "contributing" in content.lower(): s += 10
        if "license" in content.lower(): s += 5
        return min(100, s)
