import re
from typing import Dict, List, Optional
from ..models.models import (
    ArchPatternResult, DeploymentStyleResult, ServiceInfo, ArchitectureReport,
    ArchPatternResult
)

# Constants extracted from local_analyzer.py
ARCH_PATTERNS = {
    "Clean Architecture": ["domain/","application/","infrastructure/","presentation/"],
    "Hexagonal":          ["ports/","adapters/"],
    "MVC":                ["models/","views/","controllers/"],
    "Layered":            ["service/","repository/","controller/"],
    "Event-Driven":       ["events/","handlers/"],
    "CQRS":               ["commands/","queries/"],
}

_ARCH_DIR_SIGNALS = {
    "Clean Architecture":       ["domain", "application", "infrastructure", "presentation"],
    "Hexagonal":                ["ports", "adapters", "core"],
    "DDD":                      ["aggregates", "value-objects", "domain-events",
                                  "domain-services", "bounded-contexts"],
    "MVC":                      ["controllers", "models", "views", "middlewares"],
    "Layered":                  ["service", "repository", "controller", "entity"],
    "CQRS":                     ["commands", "queries", "command-handlers", "query-handlers"],
    "Event-Driven":             ["events", "handlers", "subscribers", "publishers",
                                  "consumers", "listeners"],
    "Microkernel":              ["plugins", "extensions", "core", "registry"],
}

_ARCH_CODE_SIGNALS = {
    "Clean Architecture": [
        r"(?i)class\s+\w+UseCase\b",
        r"(?i)interface\s+\w+Repository\b",
        r"(?i)class\s+\w+Entity\b",
    ],
    "Hexagonal": [
        r"(?i)interface\s+\w+Port\b",
        r"(?i)class\s+\w+Adapter\b",
        r"(?i)implements\s+\w+Port\b",
    ],
    "DDD": [
        r"(?i)class\s+\w+Aggregate\b",
        r"(?i)class\s+\w+(ValueObject|VO)\b",
        r"(?i)DomainEvent|DomainService",
        r"@AggregateRoot",
    ],
    "MVC": [
        r"@Controller|@RestController",
        r"class\s+\w+Controller\b",
    ],
    "Layered": [
        r"@Service|@Repository|@Component",
        r"class\s+\w+Service\b",
        r"class\s+\w+Repository\b",
    ],
    "CQRS": [
        r"(?i)class\s+\w+Command\b",
        r"(?i)class\s+\w+Query\b",
        r"(?i)CommandHandler|QueryHandler",
        r"(?i)ICommandBus|IQueryBus|CommandBus|QueryBus",
    ],
    "Event-Driven": [
        r"(?i)EventBus|MessageBus|EventEmitter",
        r"(?i)class\s+\w+Event\b",
        r"(?i)@OnEvent|@EventHandler|@Subscribe",
        r"(?i)kafka|rabbitmq|sqs|pubsub",
    ],
}

_DESIGN_PATTERN_SIGNALS = {
    "Factory":        [r"(?i)\bFactory\b", r"(?i)createInstance|getInstance"],
    "Builder":        [r"(?i)class\s+\w+Builder\b", r"(?i)\.build\(\)"],
    "Singleton":      [r"(?i)_instance\s*=\s*None", r"(?i)getInstance\(\)"],
    "Repository":     [r"(?i)interface\s+\w+Repository", r"(?i)class\s+\w+Repository"],
    "Adapter":        [r"(?i)class\s+\w+Adapter\b"],
    "Facade":         [r"(?i)class\s+\w+Facade\b"],
    "Observer":       [r"(?i)subscribe\b|EventEmitter|Observable"],
    "Strategy":       [r"(?i)interface\s+\w+Strategy", r"(?i)setStrategy"],
    "Command":        [r"(?i)class\s+\w+Command\b", r"(?i)\.execute\(\)"],
    "Mediator":       [r"(?i)Mediator|CommandBus|QueryBus"],
    "Middleware":     [r"(?i)middleware|next\(\)"],
    "Decorator":      [r"(?i)@\w+Decorator|class\s+\w+Decorator"],
}

_EXTERNAL_COMM_SIGNALS = {
    "HTTP/REST":      [r"axios|fetch\(|HttpClient|requests\.get|RestTemplate"],
    "gRPC":           [r"grpc|@GrpcClient|Channel\("],
    "GraphQL client": [r"ApolloClient|graphql-request|gql`"],
    "RabbitMQ":       [r"amqplib|RabbitMQ|BasicPublish"],
    "Kafka":          [r"KafkaProducer|KafkaConsumer|kafkajs"],
    "Redis Pub/Sub":  [r"redis.*\.publish\(|redis.*\.subscribe\("],
    "AWS SQS":        [r"SQSClient|sendMessage.*Queue"],
    "WebSocket":      [r"WebSocket\b|socket\.io|ws\.send"],
}

_LAYER_FORBIDDEN = {
    "domain":      ["infrastructure", "presentation", "controllers", "adapters"],
    "entities":    ["services", "controllers"],
    "models":      ["controllers", "routes"],
}

SOURCE_EXTS = {".py", ".ts", ".js", ".java", ".kt", ".cs", ".go"}

class ArchEngine:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self._all_paths = [str(f.relative_to(self.analyzer.root))
                           for f in self.analyzer.all_files()]
        self._joined_paths = " ".join(self._all_paths)

    def detect_architecture_basic(self) -> str:
        joined = " ".join(str(f.relative_to(self.analyzer.root)) for f in self.analyzer.all_files())
        scores = {p: sum(1 for d in dirs if d in joined)
                  for p, dirs in ARCH_PATTERNS.items()}
        scored = {k: v for k, v in scores.items() if v > 0}
        return max(scored, key=lambda k: scored[k]) if scored else "Desconocido"

    def analyze(self) -> ArchitectureReport:
        deployment   = self._detect_deployment()
        arch_results = self._detect_arch_patterns()
        primary      = arch_results[0] if arch_results else ArchPatternResult("Desconocido","BAJA",[],0)
        secondary    = arch_results[1:3]
        design_pats  = self._detect_design_patterns()
        violations   = self._detect_layer_violations()
        ext_comms    = self._detect_external_comms()
        services     = self._detect_services() if "monorepo" in deployment.name.lower() else []
        diagram      = self._generate_mermaid(primary.name, deployment.name, services)

        return ArchitectureReport(
            deployment_style=deployment,
            primary_pattern=primary,
            secondary_patterns=secondary,
            design_patterns=design_pats,
            layer_violations=violations,
            external_comms=ext_comms,
            services=services,
            mermaid_diagram=diagram,
        )

    def _detect_deployment(self) -> DeploymentStyleResult:
        paths = self._joined_paths
        evidence: list[str] = []

        # Serverless
        serverless_signals = ["serverless.yml", "sam.yaml", "handler.py",
                               "functions/", "lambdas/"]
        srv_hits = [s for s in serverless_signals if s in paths]
        if len(srv_hits) >= 2:
            return DeploymentStyleResult("Serverless", "ALTA",
                                         [f"Detectado: {h}" for h in srv_hits])

        # Monorepo
        monorepo_signals = ["services/", "apps/", "packages/", "lerna.json",
                             "nx.json", "turbo.json", "pnpm-workspace.yaml"]
        mono_hits = [s for s in monorepo_signals if s in paths]
        if len(mono_hits) >= 2:
            evidence = [f"Detectado: {h}" for h in mono_hits]
            return DeploymentStyleResult("Monorepo multi-servicio", "ALTA", evidence)

        # Modular Monolith
        modular_signals = ["modules/", "features/", "bounded-contexts/"]
        mod_hits = [s for s in modular_signals if s in paths]
        if mod_hits:
            return DeploymentStyleResult("Monolito Modular", "MEDIA",
                                         [f"Detectado: {h}" for h in mod_hits])

        # Microservicio (heurística de tamaño)
        source_files = [f for f in self.analyzer.all_files() if f.suffix in SOURCE_EXTS]
        has_docker = "Dockerfile" in paths
        if has_docker and len(source_files) < 100:
            return DeploymentStyleResult("Microservicio", "MEDIA", [
                f"Dockerfile detectado",
                f"{len(source_files)} archivos fuente (repositorio acotado)",
            ])

        return DeploymentStyleResult("Monolito", "MEDIA", [
            "Sin señales de arquitectura distribuida",
            f"{len(source_files)} archivos fuente",
        ])

    def _detect_arch_patterns(self) -> list[ArchPatternResult]:
        results: list[ArchPatternResult] = []
        for pattern, dir_signals in _ARCH_DIR_SIGNALS.items():
            evidence: list[str] = []
            for sig in dir_signals:
                if f"/{sig}/" in self._joined_paths or self._joined_paths.startswith(sig + "/"):
                    evidence.append(f"Directorio '{sig}/' detectado")
            for code_sig in _ARCH_CODE_SIGNALS.get(pattern, []):
                matches = self._scan_code_pattern(code_sig, max_files=5)
                if matches:
                    evidence.append(f"Código: `{code_sig[:40]}` en {len(matches)} archivo(s)")
            if not evidence: continue
            total_signals = len(dir_signals) + len(_ARCH_CODE_SIGNALS.get(pattern, []))
            score = int(len(evidence) / max(total_signals, 1) * 100)
            confidence = "ALTA" if score >= 60 else "MEDIA" if score >= 30 else "BAJA"
            results.append(ArchPatternResult(pattern, confidence, evidence, score))
        return sorted(results, key=lambda r: r.score, reverse=True)

    def _scan_code_pattern(self, pattern: str, max_files: int = 10) -> list[str]:
        found: list[str] = []
        compiled = re.compile(pattern)
        for f in self.analyzer.all_files():
            if f.suffix not in SOURCE_EXTS: continue
            content = self.analyzer.read_safe(f, max_bytes=30_000)
            if compiled.search(content):
                found.append(str(f.relative_to(self.analyzer.root)))
                if len(found) >= max_files: break
        return found

    def _detect_design_patterns(self) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for pattern, signals in _DESIGN_PATTERN_SIGNALS.items():
            files: list[str] = []
            for sig in signals:
                files.extend(self._scan_code_pattern(sig, max_files=3))
            if files:
                found[pattern] = list(dict.fromkeys(files))[:5]
        return found

    def _detect_layer_violations(self) -> list[str]:
        violations: list[str] = []
        import_re = re.compile(
            r'(?:import|from|require)\s+["\']([^"\']+)["\']|'
            r'import\s+\S+\s+from\s+["\']([^"\']+)["\']'
        )
        for f in self.analyzer.all_files():
            if f.suffix not in SOURCE_EXTS: continue
            rel = str(f.relative_to(self.analyzer.root))
            src_layer = self._extract_layer(rel)
            if not src_layer: continue
            content = self.analyzer.read_safe(f, max_bytes=20_000)
            for m in import_re.finditer(content):
                imp = m.group(1) or m.group(2) or ""
                tgt_layer = self._extract_layer(imp)
                if tgt_layer and tgt_layer in _LAYER_FORBIDDEN.get(src_layer, []):
                    violations.append(
                        f"⚠️  {rel}\n"
                        f"     importa de '{imp}'\n"
                        f"     → '{src_layer}' NO debería depender de '{tgt_layer}'"
                    )
                    if len(violations) >= 10: return violations
        return violations

    @staticmethod
    def _extract_layer(path: str) -> Optional[str]:
        LAYER_KEYWORDS = ["domain", "application", "infrastructure", "presentation",
                          "controllers", "models", "entities", "services",
                          "repositories", "adapters", "ports"]
        for kw in LAYER_KEYWORDS:
            if f"/{kw}/" in path or path.startswith(kw + "/"):
                return kw
        return None

    def _detect_external_comms(self) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for protocol, signals in _EXTERNAL_COMM_SIGNALS.items():
            files: list[str] = []
            for sig in signals:
                files.extend(self._scan_code_pattern(sig, max_files=3))
            if files:
                found[protocol] = list(dict.fromkeys(files))[:3]
        return found

    def _detect_services(self) -> list[ServiceInfo]:
        services: list[ServiceInfo] = []
        from .stack_engine import StackEngine
        for root_dir in ["services", "apps", "packages", "microservices"]:
            root_path = self.analyzer.root / root_dir
            if not root_path.exists(): continue
            for sub in sorted(root_path.iterdir()):
                if not sub.is_dir(): continue
                try:
                    from ..local_analyzer_compat import LocalAnalyzerCompat
                    sub_analyzer = LocalAnalyzerCompat(str(sub))
                    stack = StackEngine(sub_analyzer)
                    sub_stack = stack.get_profile()
                    services.append(ServiceInfo(
                        name=sub.name,
                        path=str(sub.relative_to(self.analyzer.root)),
                        primary_language=sub_stack.primary_language,
                        frameworks=sub_stack.frameworks[:2],
                        has_dockerfile=(sub / "Dockerfile").exists(),
                        entry_points=sub_stack.entry_points[:1],
                    ))
                except Exception: pass
        return services

    def _generate_mermaid(self, pattern: str, deployment: str, services: list[ServiceInfo]) -> str:
        if "monorepo" in deployment.lower() and services:
            return self._mermaid_monorepo(services)
        templates = {
            "Clean Architecture": self._mermaid_clean,
            "Hexagonal":          self._mermaid_hexagonal,
            "MVC":                self._mermaid_mvc,
            "Layered":            self._mermaid_layered,
            "CQRS":               self._mermaid_cqrs,
            "Event-Driven":       self._mermaid_event_driven,
        }
        builder = templates.get(pattern, self._mermaid_generic)
        return builder()

    def _mermaid_monorepo(self, services: list[ServiceInfo]) -> str:
        lines = ["```mermaid", "graph TD"]
        for i, svc in enumerate(services):
            fw = svc.frameworks[0] if svc.frameworks else svc.primary_language
            lines.append(f'  S{i}["{svc.name}\\n{fw}"]')
        if any("gateway" in s.name.lower() or "api-gateway" in s.name.lower() for s in services):
            gw_idx = next(i for i, s in enumerate(services) if "gateway" in s.name.lower())
            for i, svc in enumerate(services):
                if i != gw_idx: lines.append(f"  S{gw_idx} --> S{i}")
        lines.append("```")
        return "\n".join(lines)

    def _mermaid_clean(self): return "```mermaid\ngraph TD\n  subgraph PR[\"🖥️ Presentation\"]\n    CTRL[Controllers / DTOs]\n  end\n  subgraph APP[\"⚙️ Application\"]\n    UC[Use Cases]\n  end\n  subgraph DOM[\"🏛️ Domain ← Core\"]\n    ENT[Entities / Aggregates]\n    RI[Repository Interfaces]\n    DS[Domain Services]\n  end\n  subgraph INF[\"🔧 Infrastructure\"]\n    REPO[Repository Impl]\n    DB[(Database)]\n    EXT[External APIs]\n  end\n  CTRL --> UC\n  UC --> ENT\n  UC --> RI\n  REPO -.->|implements| RI\n  REPO --> DB\n  style DOM fill:#4CAF50,color:#fff\n  style APP fill:#2196F3,color:#fff\n  style INF fill:#FF9800,color:#fff\n  style PR fill:#9C27B0,color:#fff\n```"
    def _mermaid_hexagonal(self): return "```mermaid\ngraph LR\n  subgraph EXT_L[\"Driving Adapters\"]\n    REST[REST Controller]\n    CLI[CLI / Jobs]\n  end\n  subgraph CORE[\"Core (Ports)\"]\n    PIN[Input Ports]\n    APP[Application / Domain]\n    POUT[Output Ports]\n  end\n  subgraph EXT_R[\"Driven Adapters\"]\n    DB[(Database)]\n    API[External API]\n  end\n  REST --> PIN\n  CLI --> PIN\n  PIN --> APP\n  APP --> POUT\n  POUT -.->|implements| DB\n  POUT -.->|implements| API\n  style CORE fill:#4CAF50,color:#fff\n```"
    def _mermaid_mvc(self): return "```mermaid\ngraph LR\n  Client([Cliente]) --> CTRL[Controllers]\n  CTRL --> SVC[Services]\n  SVC --> MODEL[Models / Entities]\n  MODEL --> DB[(Database)]\n  CTRL --> VIEW[Views / Responses]\n  style CTRL fill:#2196F3,color:#fff\n  style MODEL fill:#4CAF50,color:#fff\n  style VIEW fill:#9C27B0,color:#fff\n```"
    def _mermaid_layered(self): return "```mermaid\ngraph TD\n  Client([Cliente])\n  CTRL[\"🖥️ Controllers / REST Layer\"]\n  SVC[\"⚙️ Service Layer\"]\n  REPO[\"🗄️ Repository Layer\"]\n  DB[(\"💾 Database\")]\n  Client --> CTRL --> SVC --> REPO --> DB\n  style CTRL fill:#9C27B0,color:#fff\n  style SVC fill:#2196F3,color:#fff\n  style REPO fill:#FF9800,color:#fff\n```"
    def _mermaid_cqrs(self): return "```mermaid\ngraph TD\n  Client([Cliente])\n  subgraph WRITE[\"✏️ Write Side (Commands)\"]\n    CMD[Command Handler]\n    WDB[(Write DB)]\n  end\n  subgraph READ[\"👁️ Read Side (Queries)\"]\n    QRY[Query Handler]\n    RDB[(Read DB / Projection)]\n  end\n  Client -->|Command| CMD\n  Client -->|Query| QRY\n  CMD --> WDB\n  WDB -.->|Event / Sync| RDB\n  QRY --> RDB\n  style WRITE fill:#FF5722,color:#fff\n  style READ fill:#2196F3,color:#fff\n```"
    def _mermaid_event_driven(self): return "```mermaid\ngraph LR\n  PUB[\"📤 Event Publisher\"]\n  BUS[\"🚌 Event Bus / Message Broker\"]\n  S1[\"📥 Subscriber 1\"]\n  S2[\"📥 Subscriber 2\"]\n  S3[\"📥 Subscriber N\"]\n  PUB -->|publish event| BUS\n  BUS -->|consume| S1\n  BUS -->|consume| S2\n  BUS -->|consume| S3\n  style BUS fill:#FF9800,color:#fff\n  style PUB fill:#4CAF50,color:#fff\n```"
    def _mermaid_generic(self): return "```mermaid\ngraph TD\n  A[No se pudo generar diagrama automático]\n```"
