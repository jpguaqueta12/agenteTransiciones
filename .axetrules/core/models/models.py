from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class SecretFinding:
    secret_type: str
    file_path: str
    line_number: int
    redacted_snippet: str
    severity: str = "CRITICAL"
    recommendation: str = ""

@dataclass
class StackProfile:
    languages: Dict[str, int]
    primary_language: str
    frameworks: List[str]
    databases: List[str]
    infrastructure: List[str]
    architecture_pattern: str
    project_type: str
    entry_points: List[str]
    test_framework: str
    has_tests: bool
    test_ratio: float

@dataclass
class ProjectQuality:
    has_readme: bool
    readme_score: int
    has_tests: bool
    test_ratio: float
    has_linting: bool
    has_ci_cd: bool
    has_dockerfile: bool
    has_env_example: bool
    has_gitignore: bool
    has_license: bool
    has_changelog: bool
    overall_score: int

@dataclass
class ArchPatternResult:
    name: str
    confidence: str          # ALTA | MEDIA | BAJA
    evidence: List[str]      # Lista de señales concretas encontradas
    score: int               # Señales encontradas / señales totales * 100

@dataclass
class DeploymentStyleResult:
    name: str                # Microservicio | Monolito | Monorepo | Serverless | ...
    confidence: str
    evidence: List[str]

@dataclass
class ServiceInfo:
    name: str
    path: str
    primary_language: str
    frameworks: List[str]
    has_dockerfile: bool
    entry_points: List[str]

@dataclass
class ArchitectureReport:
    deployment_style: DeploymentStyleResult
    primary_pattern: ArchPatternResult
    secondary_patterns: List[ArchPatternResult]
    design_patterns: Dict[str, List[str]]
    layer_violations: List[str]
    external_comms: Dict[str, List[str]]
    services: List[ServiceInfo]
    mermaid_diagram: str
