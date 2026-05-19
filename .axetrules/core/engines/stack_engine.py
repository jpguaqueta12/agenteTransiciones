import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
from ..models.models import StackProfile

LANGUAGE_MAP = {
    ".py":"Python", ".js":"JavaScript", ".ts":"TypeScript", ".java":"Java",
    ".kt":"Kotlin", ".cs":"C#", ".go":"Go", ".rb":"Ruby", ".php":"PHP",
    ".rs":"Rust", ".cpp":"C++", ".c":"C", ".scala":"Scala", ".swift":"Swift",
    ".dart":"Dart", ".vue":"Vue", ".jsx":"JSX", ".tsx":"TSX",
    ".sh":"Shell", ".ps1":"PowerShell", ".tf":"Terraform",
    ".sql":"SQL", ".html":"HTML", ".css":"CSS", ".scss":"SCSS",
}

FRAMEWORK_SIGNALS = {
    "Spring Boot":     [("dep","spring-boot-starter"), ("file","src/main/java")],
    "FastAPI":         [("dep","fastapi")],
    "Django":          [("dep","django"), ("file","manage.py")],
    "Flask":           [("dep","flask")],
    "Express":         [("dep",'"express"')],
    "NestJS":          [("dep",'"@nestjs/core"'), ("file","nest-cli.json")],
    ".NET Web API":    [("file",".csproj"), ("dep","Microsoft.AspNetCore")],
    "Laravel":         [("dep",'"laravel/framework"'), ("file","artisan")],
    "Rails":           [("dep","rails"), ("file","config/routes.rb")],
    "React":           [("dep",'"react"'), ("dep",'"react-dom"')],
    "Next.js":         [("dep",'"next"'), ("file","next.config.js")],
    "Angular":         [("dep",'"@angular/core"'), ("file","angular.json")],
    "Vue":             [("dep",'"vue"'), ("file","vue.config.js")],
    "Vite":            [("dep",'"vite"'), ("file","vite.config.ts")],
    "React Native":    [("dep",'"react-native"')],
    "Flutter":         [("file","pubspec.yaml"), ("dep","flutter:")],
    "LangChain":       [("dep","langchain")],
    "LangGraph":       [("dep","langgraph")],
}

DB_SIGNALS = {
    "PostgreSQL":    ["psycopg2","pg","postgresql","TypeORM","Sequelize"],
    "MySQL":         ["mysql","mysql2","mysql-connector"],
    "MongoDB":       ["mongoose","pymongo","mongodb"],
    "Redis":         ["redis","ioredis","redis-py"],
    "SQLite":        ["sqlite","better-sqlite3"],
    "Elasticsearch": ["elasticsearch","opensearch"],
    "SQL Server":    ["mssql","pyodbc"],
    "Oracle":        ["cx_Oracle","oracledb"],
    "DynamoDB":      ["dynamodb","boto3"],
    "Neo4j":         ["neo4j","py2neo"],
    "Supabase":      ["supabase","@supabase/supabase-js"],
    "Prisma":        ['"@prisma/client"','prisma'],
    "SQLAlchemy":    ["sqlalchemy"],
    "TypeORM":       ['"typeorm"'],
    "Hibernate":     ["hibernate"],
}

INFRA_MAP = {
    "Dockerfile":"Docker", "docker-compose.yml":"Docker Compose",
    "docker-compose.yaml":"Docker Compose",
    ".github/workflows":"GitHub Actions", ".gitlab-ci.yml":"GitLab CI",
    "azure-pipelines.yml":"Azure Pipelines", "Jenkinsfile":"Jenkins",
    "sonar-project.properties":"SonarQube", ".sonarcloud.properties":"SonarCloud",
    "k8s":"Kubernetes", "kubernetes":"Kubernetes", "helm":"Helm",
    "main.tf":"Terraform", ".eslintrc":"ESLint", ".eslintrc.js":"ESLint",
    ".eslintrc.json":"ESLint", ".pylintrc":"Pylint",
}

class StackEngine:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def detect_languages(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for f in self.analyzer.all_files():
            lang = LANGUAGE_MAP.get(f.suffix.lower())
            if lang: counts[lang] += 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def detect_frameworks(self, manifest_text: str) -> List[str]:
        all_paths = [str(f.relative_to(self.analyzer.root)) for f in self.analyzer.all_files()]
        found: List[str] = []
        for fw, signals in FRAMEWORK_SIGNALS.items():
            for typ, val in signals:
                if typ == "dep" and val in manifest_text:
                    found.append(fw); break
                if typ == "file" and any(val.lstrip("*.") in p for p in all_paths):
                    found.append(fw); break
        return list(dict.fromkeys(found))

    def detect_databases(self, manifest_text: str) -> List[str]:
        return [db for db, sigs in DB_SIGNALS.items() if any(s in manifest_text for s in sigs)]

    def detect_infrastructure(self) -> List[str]:
        found: List[str] = []
        all_str = [str(f.relative_to(self.analyzer.root)) for f in self.analyzer.all_files()]
        all_str += [str(d.relative_to(self.analyzer.root)) for d in self.analyzer.root.rglob("*") if d.is_dir()]
        for pattern, label in INFRA_MAP.items():
            if label not in found and any(pattern in p for p in all_str):
                found.append(label)
        return list(dict.fromkeys(found))

    def get_profile(self) -> StackProfile:
        langs = self.detect_languages()
        manifest_text = self.analyzer._all_manifest_text()
        from .quality_engine import QualityEngine
        quality = QualityEngine(self.analyzer)
        has_tests, ratio, fw = quality.analyze_tests(manifest_text)
        
        from .arch_engine import ArchEngine
        arch = ArchEngine(self.analyzer)
        
        return StackProfile(
            languages=langs, 
            primary_language=next(iter(langs), "Desconocido"),
            frameworks=self.detect_frameworks(manifest_text), 
            databases=self.detect_databases(manifest_text),
            infrastructure=self.detect_infrastructure(),
            architecture_pattern=arch.detect_architecture_basic(),
            project_type=self._project_type(langs),
            entry_points=self._entry_points(),
            test_framework=fw, 
            has_tests=has_tests, 
            test_ratio=ratio,
        )

    def _project_type(self, langs: Dict[str, int]) -> str:
        fe = any(l in langs for l in ["TypeScript","JavaScript","Vue","JSX","TSX"])
        be = any(l in langs for l in ["Python","Java","Kotlin","C#","Go","PHP","Ruby"])
        mobile = "Dart" in langs or "Swift" in langs
        if mobile: return "Aplicación Mobile"
        if fe and be: return "Fullstack"
        if "HTML" in langs and fe: return "Frontend Web"
        if be: return "Backend / API"
        if fe: return "Frontend / SPA"
        return "Librería / Utilidad"

    def _entry_points(self) -> List[str]:
        NAMES = {"main.py","app.py","server.py","index.js","app.js","server.js",
                 "index.ts","main.ts","Main.java","Application.java",
                 "Program.cs","Startup.cs","main.go","main.rb"}
        return [str(f.relative_to(self.analyzer.root)) for f in self.analyzer.all_files()
                if f.name in NAMES][:5]
