"""
scripts/volumetry_analyzer.py — RepoIntel Suite
Análisis de volumetría, complejidad y riesgo técnico del código fuente.

Módulos:
  - LOC / SLOC por lenguaje y por capa
  - Distribución de tamaño de archivos
  - Complejidad ciclomática estimada
  - Profundidad de anidamiento
  - Funciones/clases problemáticas
  - Ratio de documentación y TODOs
  - Duplicación de código (hashing de bloques)
  - Hotspots (complejidad × frecuencia de cambio Git)
  - Acoplamiento fan-in / fan-out

pip install gitpython  (solo para hotspots via git log)
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Importar utilidades base ──────────────────────────────────────────────────
# local_analyzer.py debe estar en el mismo directorio
try:
    from local_analyzer import LocalAnalyzer, LANGUAGE_MAP, IGNORE_DIRS, IGNORE_EXTS
except ImportError:
    # Fallback si se ejecuta standalone
    LANGUAGE_MAP = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".java": "Java", ".kt": "Kotlin", ".cs": "C#", ".go": "Go",
        ".rb": "Ruby", ".php": "PHP", ".rs": "Rust", ".cpp": "C++",
        ".c": "C", ".scala": "Scala", ".swift": "Swift", ".dart": "Dart",
        ".vue": "Vue", ".jsx": "JSX", ".tsx": "TSX",
    }
    IGNORE_DIRS = {
        "node_modules", ".git", "dist", "build", "__pycache__", ".next",
        "vendor", "target", "bin", "obj", ".terraform", "coverage",
        ".nyc_output", "venv", ".venv", "env", ".gradle", "out",
    }
    IGNORE_EXTS = {".min.js", ".min.css", ".map", ".lock", ".sum"}

SOURCE_EXTS = {".py", ".ts", ".js", ".java", ".kt", ".cs", ".go",
               ".rb", ".php", ".rs", ".cpp", ".c", ".scala", ".swift",
               ".dart", ".vue", ".jsx", ".tsx"}

# ── Patrones de complejidad ciclomática por lenguaje ─────────────────────────

COMPLEXITY_PATTERNS: dict[str, list[str]] = {
    ".py":   [r"\bif\b", r"\belif\b", r"\bfor\b", r"\bwhile\b",
              r"\bexcept\b", r"\bwith\b", r"\band\b", r"\bor\b",
              r"\bcase\b", r" if .+? else "],
    ".ts":   [r"\bif\b", r"\belse if\b", r"\bfor\b", r"\bwhile\b",
              r"\bcatch\b", r"\bcase\b", r"\?\?", r"\?\.",
              r" \? .+? : "],
    ".tsx":  [r"\bif\b", r"\belse if\b", r"\bfor\b", r"\bwhile\b",
              r"\bcatch\b", r"\bcase\b", r"\?\?", r"\?\.",
              r" \? .+? : "],
    ".js":   [r"\bif\b", r"\belse if\b", r"\bfor\b", r"\bwhile\b",
              r"\bcatch\b", r"\bcase\b", r"\?\?", r" \? .+? : "],
    ".jsx":  [r"\bif\b", r"\belse if\b", r"\bfor\b", r"\bwhile\b",
              r"\bcatch\b", r"\bcase\b", r"\?\?"],
    ".java": [r"\bif\b", r"\belse if\b", r"\bfor\b", r"\bwhile\b",
              r"\bcatch\b", r"\bcase\b", r"\&\&", r"\|\|",
              r" \? .+? : "],
    ".kt":   [r"\bif\b", r"\bwhen\b", r"\bfor\b", r"\bwhile\b",
              r"\bcatch\b", r"\?\?", r"\?\.", r" \? .+? : "],
    ".cs":   [r"\bif\b", r"\belse if\b", r"\bfor\b", r"\bforeach\b",
              r"\bwhile\b", r"\bcatch\b", r"\bcase\b", r"\?\?",
              r" \? .+? : "],
    ".go":   [r"\bif\b", r"\bfor\b", r"\bcase\b", r"\bselect\b",
              r"\bdefer\b"],
    ".rb":   [r"\bif\b", r"\belsif\b", r"\bunless\b", r"\bwhile\b",
              r"\buntil\b", r"\brescue\b", r"\bcase\b", r"\band\b",
              r"\bor\b"],
    ".php":  [r"\bif\b", r"\belseif\b", r"\bfor\b", r"\bforeach\b",
              r"\bwhile\b", r"\bcatch\b", r"\bcase\b", r"\?\?",
              r" \? .+? : "],
    ".rs":   [r"\bif\b", r"\belse if\b", r"\bfor\b", r"\bwhile\b",
              r"\bmatch\b", r"\bloop\b", r"\&\&", r"\|\|"],
    ".swift":[r"\bif\b", r"\bguard\b", r"\bfor\b", r"\bwhile\b",
              r"\bcatch\b", r"\bswitch\b", r"\?\?", r"\?\."],
}

# ── Patrones de imports por lenguaje (para acoplamiento) ─────────────────────

IMPORT_PATTERNS: dict[str, str] = {
    ".py":   r"^(?:from|import)\s+([\w\.]+)",
    ".ts":   r"(?:import|require)\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+['\"]([^'\"]+)['\"]",
    ".tsx":  r"(?:import|require)\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+['\"]([^'\"]+)['\"]",
    ".js":   r"(?:import|require)\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+['\"]([^'\"]+)['\"]",
    ".jsx":  r"(?:import|require)\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+['\"]([^'\"]+)['\"]",
    ".java": r"^import\s+([\w\.]+);",
    ".kt":   r"^import\s+([\w\.]+)",
    ".cs":   r"^using\s+([\w\.]+);",
    ".go":   r"\"([\w\.\/]+)\"",
    ".rb":   r"require\s+['\"]([^'\"]+)['\"]",
    ".php":  r"(?:use|require|include)\s+['\"]?([^\s;'\"]+)",
}

# ── Modelos de datos ──────────────────────────────────────────────────────────

@dataclass
class LOCStats:
    total_lines: int = 0
    code_lines: int = 0        # SLOC
    comment_lines: int = 0
    blank_lines: int = 0

    @property
    def comment_ratio(self) -> float:
        return round(self.comment_lines / max(self.code_lines, 1), 2)


@dataclass
class FileMetrics:
    path: str
    language: str
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    complexity_score: int = 0
    max_nesting: int = 0
    function_count: int = 0


@dataclass
class LOCReport:
    overall: LOCStats
    by_language: dict[str, LOCStats]
    by_layer: dict[str, LOCStats]
    top_files: list[FileMetrics]      # top 20 por líneas totales
    total_files: int = 0


@dataclass
class FileSizeDistribution:
    histogram: dict[str, int]         # rango → cantidad de archivos
    oversized: list[FileMetrics]       # >500 líneas
    avg_lines: float = 0.0
    p90_lines: int = 0                 # percentil 90


@dataclass
class ComplexityReport:
    by_file: dict[str, int]            # filepath → score total
    hotspots: list[tuple[str, int]]    # (filepath, score) top 20
    avg: float = 0.0
    distribution: dict[str, int] = field(default_factory=dict)
    # {"low": n, "medium": n, "high": n, "very_high": n}


@dataclass
class NestingReport:
    by_file: dict[str, int]            # filepath → max depth
    deep_files: list[tuple[str, int]]  # archivos con depth > 4
    avg_depth: float = 0.0


@dataclass
class ProblematicUnit:
    filepath: str
    name: str
    line: int
    metric: str    # "long_function" | "many_params" | "large_class" | "god_object"
    value: int     # líneas, parámetros, métodos, imports


@dataclass
class TodoItem:
    filepath: str
    line: int
    kind: str      # TODO | FIXME | HACK | XXX | NOSONAR
    text: str


@dataclass
class DocumentationReport:
    docstring_ratio: float
    undocumented_count: int
    todos: list[TodoItem]
    fixmes: list[TodoItem]
    hacks: list[TodoItem]

    @property
    def tech_debt_items(self) -> int:
        return len(self.todos) + len(self.fixmes) + len(self.hacks)


@dataclass
class DuplicateBlock:
    block_hash: str
    locations: list[tuple[str, int]]   # (filepath, start_line)
    sample_lines: list[str]             # primeras 3 líneas del bloque


@dataclass
class DuplicationReport:
    blocks: list[DuplicateBlock]
    duplication_ratio: float
    total_duplicate_lines: int


@dataclass
class Hotspot:
    filepath: str
    complexity_score: int
    change_count: int
    hotspot_score: float   # 0–100


@dataclass
class CouplingModule:
    path: str
    fan_in: int             # cuántos módulos importan a este
    fan_out: int            # cuántos módulos importa este

    @property
    def instability(self) -> float:
        total = self.fan_in + self.fan_out
        return round(self.fan_out / max(total, 1), 2)


@dataclass
class CouplingReport:
    modules: list[CouplingModule]
    hub_modules: list[CouplingModule]    # fan_in > 10
    unstable_modules: list[CouplingModule]  # instability > 0.7
    dead_files: list[str]                # fan_in = 0 y fan_out = 0


@dataclass
class CodeHealthScore:
    total: int
    grade: str
    hotspot_count: int
    top_risks: list[str]


@dataclass
class VolumetryReport:
    loc: LOCReport
    file_dist: FileSizeDistribution
    complexity: ComplexityReport
    nesting: NestingReport
    problematic_units: list[ProblematicUnit]
    docs: DocumentationReport
    duplication: DuplicationReport
    hotspots: list[Hotspot]
    coupling: CouplingReport
    health: CodeHealthScore


# ── Analizador principal ──────────────────────────────────────────────────────

class VolumetryAnalyzer:
    """
    Punto de entrada: VolumetryAnalyzer(clone_path).analyze()
    También puedes ejecutar módulos individuales.
    """

    def __init__(self, clone_path: str):
        self.root = Path(clone_path)
        if not self.root.exists():
            raise FileNotFoundError(f"Repo no encontrado: {clone_path}")
        self._files: list[Path] | None = None
        self._content_cache: dict[str, str] = {}

    # ── Utilidades ────────────────────────────────────────────────────────────

    def source_files(self) -> list[Path]:
        if self._files is not None:
            return self._files
        result = []
        for p in self.root.rglob("*"):
            if p.is_file() and p.suffix in SOURCE_EXTS:
                if not set(p.parts).intersection(IGNORE_DIRS):
                    if p.suffix not in IGNORE_EXTS:
                        result.append(p)
        self._files = result
        return result

    def read(self, path: Path, max_bytes: int = 200_000) -> str:
        key = str(path)
        if key not in self._content_cache:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    self._content_cache[key] = f.read(max_bytes)
            except OSError:
                self._content_cache[key] = ""
        return self._content_cache[key]

    def rel(self, path: Path) -> str:
        return str(path.relative_to(self.root))

    @staticmethod
    def _layer_of(rel_path: str) -> str:
        """Extrae la capa de primer nivel de una ruta relativa."""
        parts = rel_path.replace("\\", "/").split("/")
        # Buscar en src/ o directamente en raíz
        if len(parts) >= 2 and parts[0] in ("src", "lib", "app"):
            return parts[1] if len(parts) > 2 else parts[0]
        return parts[0]

    # ── Módulo 1: LOC ─────────────────────────────────────────────────────────

    def calculate_loc(self) -> LOCReport:
        by_language: dict[str, LOCStats] = defaultdict(LOCStats)
        by_layer: dict[str, LOCStats] = defaultdict(LOCStats)
        all_files_metrics: list[FileMetrics] = []
        overall = LOCStats()

        COMMENT_STARTS = ("//", "#", "/*", "*", "<!--", "'''", '"""')

        for f in self.source_files():
            content = self.read(f)
            lines = content.splitlines()
            lang = LANGUAGE_MAP.get(f.suffix.lower(), "Other")
            layer = self._layer_of(self.rel(f))

            fm = FileMetrics(
                path=self.rel(f), language=lang,
                total_lines=0, code_lines=0,
                comment_lines=0, blank_lines=0,
            )

            for line in lines:
                stripped = line.strip()
                fm.total_lines += 1
                if not stripped:
                    fm.blank_lines += 1
                elif any(stripped.startswith(c) for c in COMMENT_STARTS):
                    fm.comment_lines += 1
                else:
                    fm.code_lines += 1

            # Acumular en lenguaje
            s = by_language[lang]
            s.total_lines  += fm.total_lines
            s.code_lines   += fm.code_lines
            s.comment_lines += fm.comment_lines
            s.blank_lines  += fm.blank_lines

            # Acumular en capa
            l = by_layer[layer]
            l.total_lines  += fm.total_lines
            l.code_lines   += fm.code_lines
            l.comment_lines += fm.comment_lines
            l.blank_lines  += fm.blank_lines

            # Acumular en total
            overall.total_lines  += fm.total_lines
            overall.code_lines   += fm.code_lines
            overall.comment_lines += fm.comment_lines
            overall.blank_lines  += fm.blank_lines

            all_files_metrics.append(fm)

        top_files = sorted(all_files_metrics, key=lambda x: x.total_lines, reverse=True)[:20]

        return LOCReport(
            overall=overall,
            by_language=dict(sorted(by_language.items(),
                                    key=lambda x: x[1].total_lines, reverse=True)),
            by_layer=dict(sorted(by_layer.items(),
                                 key=lambda x: x[1].total_lines, reverse=True)),
            top_files=top_files,
            total_files=len(all_files_metrics),
        )

    # ── Módulo 2: Distribución de tamaño ─────────────────────────────────────

    def file_size_distribution(self) -> FileSizeDistribution:
        RANGES = [
            ("micro (<50)",       0,   49),
            ("pequeño (50-150)",  50,  150),
            ("mediano (151-300)", 151, 300),
            ("grande (301-500)",  301, 500),
            ("muy grande (>500)", 501, 999_999),
        ]
        histogram: dict[str, int] = {r[0]: 0 for r in RANGES}
        all_sizes: list[int] = []
        oversized: list[FileMetrics] = []

        for f in self.source_files():
            lines = self.read(f).count("\n") + 1
            all_sizes.append(lines)
            lang = LANGUAGE_MAP.get(f.suffix.lower(), "Other")
            fm = FileMetrics(self.rel(f), lang, lines, 0, 0, 0)

            for label, lo, hi in RANGES:
                if lo <= lines <= hi:
                    histogram[label] += 1
                    break
            if lines > 500:
                oversized.append(fm)

        all_sizes.sort()
        p90 = all_sizes[int(len(all_sizes) * 0.9)] if all_sizes else 0
        avg = sum(all_sizes) / max(len(all_sizes), 1)

        return FileSizeDistribution(
            histogram=histogram,
            oversized=sorted(oversized, key=lambda x: x.total_lines, reverse=True),
            avg_lines=round(avg, 1),
            p90_lines=p90,
        )

    # ── Módulo 3: Complejidad ciclomática ─────────────────────────────────────

    def estimate_cyclomatic_complexity(self) -> ComplexityReport:
        by_file: dict[str, int] = {}
        distribution = {"low(1-4)": 0, "medium(5-9)": 0,
                        "high(10-14)": 0, "very_high(15+)": 0}

        for f in self.source_files():
            patterns = COMPLEXITY_PATTERNS.get(f.suffix.lower(), [])
            if not patterns:
                continue
            content = self.read(f)
            score = 1  # base CC = 1
            for pattern in patterns:
                score += len(re.findall(pattern, content))
            by_file[self.rel(f)] = score

            if score <= 4:    distribution["low(1-4)"] += 1
            elif score <= 9:  distribution["medium(5-9)"] += 1
            elif score <= 14: distribution["high(10-14)"] += 1
            else:             distribution["very_high(15+)"] += 1

        hotspots = sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:20]
        avg = sum(by_file.values()) / max(len(by_file), 1)

        return ComplexityReport(
            by_file=by_file,
            hotspots=hotspots,
            avg=round(avg, 1),
            distribution=distribution,
        )

    # ── Módulo 4: Profundidad de anidamiento ──────────────────────────────────

    def analyze_nesting_depth(self) -> NestingReport:
        by_file: dict[str, int] = {}

        for f in self.source_files():
            content = self.read(f)
            max_depth = 0
            for line in content.splitlines():
                if not line.strip():
                    continue
                # Calcular profundidad por indentación
                spaces = len(line) - len(line.lstrip())
                indent_size = 4 if f.suffix in (".py",) else 2
                depth = spaces // max(indent_size, 1)
                max_depth = max(max_depth, depth)
            by_file[self.rel(f)] = min(max_depth, 20)  # cap para evitar outliers

        deep_files = [(p, d) for p, d in by_file.items() if d > 4]
        deep_files.sort(key=lambda x: x[1], reverse=True)
        avg = sum(by_file.values()) / max(len(by_file), 1)

        return NestingReport(
            by_file=by_file,
            deep_files=deep_files[:20],
            avg_depth=round(avg, 1),
        )

    # ── Módulo 5: Unidades problemáticas ─────────────────────────────────────

    def find_problematic_units(self) -> list[ProblematicUnit]:
        problems: list[ProblematicUnit] = []
        FN_PATTERNS = [
            re.compile(r"^\s*(?:def|function|func|fun|sub)\s+(\w+)\s*\(([^)]*)\)", re.M),
            re.compile(r"^\s*(?:public|private|protected|static|async)[\s\w]*\s+(\w+)\s*\(([^)]*)\)", re.M),
        ]

        for f in self.source_files():
            content = self.read(f)
            lines = content.splitlines()
            rel = self.rel(f)

            # Funciones largas (>50 líneas) y con muchos parámetros
            for pattern in FN_PATTERNS:
                for m in pattern.finditer(content):
                    fn_name = m.group(1)
                    params_str = m.group(2) if m.lastindex >= 2 else ""
                    fn_line = content[:m.start()].count("\n") + 1

                    # Contar parámetros (aproximado)
                    params = [p.strip() for p in params_str.split(",") if p.strip()] if params_str else []
                    if len(params) > 5:
                        problems.append(ProblematicUnit(
                            rel, fn_name, fn_line,
                            "many_params", len(params)
                        ))

                    # Estimar longitud de función: líneas hasta la siguiente def/class
                    fn_body_lines = 0
                    indent = len(lines[fn_line - 1]) - len(lines[fn_line - 1].lstrip())
                    for i in range(fn_line, min(fn_line + 200, len(lines))):
                        l = lines[i]
                        if l.strip() and (len(l) - len(l.lstrip())) <= indent and i > fn_line:
                            break
                        fn_body_lines += 1
                    if fn_body_lines > 50:
                        problems.append(ProblematicUnit(
                            rel, fn_name, fn_line,
                            "long_function", fn_body_lines
                        ))

            # Clases grandes
            class_pattern = re.compile(r"^\s*(?:class|interface|struct)\s+(\w+)", re.M)
            for m in class_pattern.finditer(content):
                class_line = content[:m.start()].count("\n") + 1
                # Contar líneas aproximadas de la clase
                class_lines = min(500, len(lines) - class_line)
                if class_lines > 300:
                    problems.append(ProblematicUnit(
                        rel, m.group(1), class_line,
                        "large_class", class_lines
                    ))

        return problems

    # ── Módulo 6: Documentación y TODOs ──────────────────────────────────────

    def analyze_documentation(self) -> DocumentationReport:
        TODO_RE  = re.compile(r"(?://|#|/\*)\s*TODO[:\s](.+)", re.I)
        FIXME_RE = re.compile(r"(?://|#|/\*)\s*FIXME[:\s](.+)", re.I)
        HACK_RE  = re.compile(r"(?://|#|/\*)\s*(?:HACK|XXX|NOSONAR)[:\s](.+)", re.I)
        DOC_RE   = re.compile(r'(?:"""|\'\'\'\s*\w|/\*\*|^\s*#\s*\w)', re.M)
        FN_RE    = re.compile(r"^\s*(?:def|function|func|fun|public|private|protected)\s+\w+", re.M)

        todos:  list[TodoItem] = []
        fixmes: list[TodoItem] = []
        hacks:  list[TodoItem] = []

        total_fns = 0
        documented_fns = 0

        for f in self.source_files():
            content = self.read(f)
            rel = self.rel(f)
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                if m := TODO_RE.search(line):
                    todos.append(TodoItem(rel, i, "TODO", m.group(1).strip()[:100]))
                if m := FIXME_RE.search(line):
                    fixmes.append(TodoItem(rel, i, "FIXME", m.group(1).strip()[:100]))
                if m := HACK_RE.search(line):
                    hacks.append(TodoItem(rel, i, "HACK", m.group(1).strip()[:100]))

            # Ratio de documentación (aproximado)
            fns = FN_RE.findall(content)
            docs = DOC_RE.findall(content)
            total_fns += len(fns)
            documented_fns += min(len(docs), len(fns))

        ratio = round(documented_fns / max(total_fns, 1), 2)

        return DocumentationReport(
            docstring_ratio=ratio,
            undocumented_count=max(0, total_fns - documented_fns),
            todos=todos[:100],
            fixmes=fixmes[:50],
            hacks=hacks[:50],
        )

    # ── Módulo 7: Duplicación ─────────────────────────────────────────────────

    def detect_duplication(self, block_size: int = 6) -> DuplicationReport:
        TRIVIAL = re.compile(r"^[{}\[\]();\s,]+$")

        def normalize(line: str) -> str:
            """Normalizar línea para comparación: quitar strings, números, espacios."""
            line = re.sub(r'"[^"]*"', '"STR"', line)
            line = re.sub(r"'[^']*'", "'STR'", line)
            line = re.sub(r"\b\d+\b", "NUM", line)
            line = re.sub(r"\s+", " ", line)
            return line.strip().lower()

        def is_trivial(block_lines: list[str]) -> bool:
            non_trivial = [l for l in block_lines if not TRIVIAL.match(l)]
            return len(non_trivial) < 2

        hashes: dict[str, list[tuple[str, int]]] = defaultdict(list)
        sample_lines_map: dict[str, list[str]] = {}

        for f in self.source_files():
            content = self.read(f)
            raw_lines = content.splitlines()
            norm_lines = [normalize(l) for l in raw_lines if l.strip()]
            rel = self.rel(f)

            for i in range(len(norm_lines) - block_size + 1):
                block = norm_lines[i:i + block_size]
                if is_trivial(block):
                    continue
                block_str = "\n".join(block)
                h = hashlib.md5(block_str.encode()).hexdigest()
                hashes[h].append((rel, i + 1))
                if h not in sample_lines_map:
                    sample_lines_map[h] = raw_lines[i:i + 3]

        duplicate_blocks: list[DuplicateBlock] = [
            DuplicateBlock(h, locs, sample_lines_map.get(h, []))
            for h, locs in hashes.items()
            if len(locs) > 1
        ]
        duplicate_blocks.sort(key=lambda b: len(b.locations), reverse=True)

        total_source_lines = sum(
            self.read(f).count("\n") + 1 for f in self.source_files()
        )
        dup_lines = sum(len(b.locations) * block_size for b in duplicate_blocks)
        ratio = round(min(dup_lines / max(total_source_lines, 1), 1.0), 3)

        return DuplicationReport(
            blocks=duplicate_blocks[:50],
            duplication_ratio=ratio,
            total_duplicate_lines=dup_lines,
        )

    # ── Módulo 8: Hotspots ────────────────────────────────────────────────────

    def calculate_hotspots(self, days: int = 90) -> list[Hotspot]:
        """
        Cruza complejidad ciclomática con frecuencia de cambio en Git.
        Requiere que el repo tenga historial Git (no solo --depth 1).
        Si Git no está disponible, retorna solo por complejidad.
        """
        complexity = self.estimate_cyclomatic_complexity()
        change_freq = self._git_change_frequency(days)

        if not complexity.by_file:
            return []

        # Normalizar a 0-100
        max_cc   = max(complexity.by_file.values(), default=1)
        max_freq = max(change_freq.values(), default=1) if change_freq else 1

        hotspots: list[Hotspot] = []
        for filepath, cc in complexity.by_file.items():
            freq = change_freq.get(filepath, 0)
            norm_cc   = cc / max_cc * 100
            norm_freq = freq / max_freq * 100
            score = norm_cc * 0.5 + norm_freq * 0.5

            if score > 10:  # Filtrar archivos triviales
                hotspots.append(Hotspot(
                    filepath=filepath,
                    complexity_score=cc,
                    change_count=freq,
                    hotspot_score=round(score, 1),
                ))

        return sorted(hotspots, key=lambda h: h.hotspot_score, reverse=True)[:30]

    def _git_change_frequency(self, days: int) -> dict[str, int]:
        """Cuenta cuántas veces cambió cada archivo en los últimos N días."""
        freq: dict[str, int] = defaultdict(int)
        try:
            result = subprocess.run(
                ["git", "-C", str(self.root), "log",
                 f"--since={days} days ago",
                 "--name-only", "--format="],
                capture_output=True, text=True, timeout=30
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and not line.startswith("commit"):
                    freq[line] += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Git no disponible o historial muy shallow
        return dict(freq)

    # ── Módulo 9: Acoplamiento ────────────────────────────────────────────────

    def analyze_coupling(self) -> CouplingReport:
        """
        Calcula fan-in y fan-out para cada módulo analizando imports.
        Solo considera imports relativos (./  ../) para evitar contar librerías externas.
        """
        # Mapa: módulo → set de módulos que importa
        imports_map: dict[str, set[str]] = defaultdict(set)
        all_rel_paths = {self.rel(f) for f in self.source_files()}

        for f in self.source_files():
            content = self.read(f)
            pattern_str = IMPORT_PATTERNS.get(f.suffix.lower(), "")
            if not pattern_str:
                continue
            rel = self.rel(f)
            try:
                compiled = re.compile(pattern_str, re.M)
            except re.error:
                continue

            for m in compiled.finditer(content):
                imp = m.group(1).strip()
                # Solo imports relativos
                if imp.startswith(".") or "/" in imp:
                    # Normalizar a ruta relativa
                    normalized = imp.lstrip("./").replace("/", os.sep if False else "/")
                    # Buscar el archivo que corresponde
                    for candidate in all_rel_paths:
                        if normalized in candidate:
                            imports_map[rel].add(candidate)
                            break

        # Calcular fan-in (quién importa a este módulo)
        fan_in: dict[str, int] = defaultdict(int)
        for _src, targets in imports_map.items():
            for target in targets:
                fan_in[target] += 1

        modules: list[CouplingModule] = []
        for rel_path in all_rel_paths:
            fo = len(imports_map.get(rel_path, set()))
            fi = fan_in.get(rel_path, 0)
            modules.append(CouplingModule(rel_path, fi, fo))

        hub_modules     = sorted([m for m in modules if m.fan_in > 10],
                                  key=lambda m: m.fan_in, reverse=True)
        unstable        = sorted([m for m in modules if m.instability > 0.7 and m.fan_out > 3],
                                  key=lambda m: m.instability, reverse=True)
        dead_files      = [m.path for m in modules if m.fan_in == 0 and m.fan_out == 0]

        return CouplingReport(
            modules=sorted(modules, key=lambda m: m.fan_in, reverse=True)[:50],
            hub_modules=hub_modules[:10],
            unstable_modules=unstable[:10],
            dead_files=dead_files[:20],
        )

    # ── Análisis completo ─────────────────────────────────────────────────────

    def analyze(self, include_hotspots: bool = True,
                include_duplication: bool = True) -> VolumetryReport:
        print("📊 Calculando LOC y distribución de archivos...")
        loc  = self.calculate_loc()
        dist = self.file_size_distribution()

        print("🔍 Analizando complejidad ciclomática...")
        complexity = self.estimate_cyclomatic_complexity()

        print("📐 Analizando profundidad de anidamiento...")
        nesting = self.analyze_nesting_depth()

        print("⚠️  Detectando unidades problemáticas...")
        problems = self.find_problematic_units()

        print("📝 Analizando documentación y TODOs...")
        docs = self.analyze_documentation()

        print("🔗 Analizando acoplamiento entre módulos...")
        coupling = self.analyze_coupling()

        duplication = DuplicationReport([], 0.0, 0)
        if include_duplication:
            print("🔁 Detectando código duplicado...")
            duplication = self.detect_duplication()

        hotspots: list[Hotspot] = []
        if include_hotspots:
            print("🔥 Calculando hotspots (complejidad × cambios Git)...")
            hotspots = self.calculate_hotspots()

        health = self._calculate_health(complexity, dist, duplication, docs, hotspots)

        return VolumetryReport(
            loc=loc, file_dist=dist, complexity=complexity,
            nesting=nesting, problematic_units=problems,
            docs=docs, duplication=duplication,
            hotspots=hotspots, coupling=coupling, health=health,
        )

    # ── Score de salud del código ─────────────────────────────────────────────

    @staticmethod
    def _calculate_health(complexity: ComplexityReport,
                           dist: FileSizeDistribution,
                           duplication: DuplicationReport,
                           docs: DocumentationReport,
                           hotspots: list[Hotspot]) -> CodeHealthScore:
        score = 100
        d = complexity.distribution

        # Penalizar por complejidad alta
        score -= min(d.get("very_high(15+)", 0) * 3, 20)
        score -= min(d.get("high(10-14)", 0) * 1, 10)

        # Penalizar por archivos muy grandes
        score -= min(len(dist.oversized) * 2, 15)

        # Penalizar por duplicación
        r = duplication.duplication_ratio
        if r > 0.20:   score -= 15
        elif r > 0.10: score -= 8
        elif r > 0.05: score -= 3

        # Penalizar por poca documentación
        dr = docs.docstring_ratio
        if dr < 0.20:   score -= 10
        elif dr < 0.40: score -= 5

        # Penalizar por deuda técnica acumulada
        score -= min(docs.tech_debt_items // 10, 10)

        score = max(0, score)
        grade = ("A" if score >= 90 else "B" if score >= 80
                 else "C" if score >= 60 else "D" if score >= 40 else "F")

        return CodeHealthScore(
            total=score, grade=grade,
            hotspot_count=len(hotspots),
            top_risks=[h.filepath for h in hotspots[:3]],
        )


# ── Formateo de reporte ───────────────────────────────────────────────────────

def format_volumetry_report(r: VolumetryReport) -> str:
    lines: list[str] = [
        "",
        "📊 REPORTE DE VOLUMETRÍA",
        "━" * 60,
        f"  Archivos fuente:          {r.loc.total_files}",
        f"  LOC total:                {r.loc.overall.total_lines:,}",
        f"  SLOC (código real):       {r.loc.overall.code_lines:,}  "
        f"({int(r.loc.overall.code_lines/max(r.loc.overall.total_lines,1)*100)}%)",
        f"  Comentarios:              {r.loc.overall.comment_lines:,}  "
        f"({int(r.loc.overall.comment_ratio*100)}%)",
        f"  Promedio líneas/archivo:  {r.file_dist.avg_lines}",
        f"  Archivo más grande:       {r.loc.top_files[0].total_lines} líneas "
        f"— {r.loc.top_files[0].path}" if r.loc.top_files else "",
        "",
        f"  SCORE DE SALUD:  {r.health.total}/100  [{r.health.grade}]",
        f"  Hotspots críticos:  {r.health.hotspot_count}",
        "",
        "  COMPLEJIDAD CICLOMÁTICA",
        f"  Promedio:  {r.complexity.avg}",
    ]

    dist = r.complexity.distribution
    for label, key in [("🟢 Baja    (1–4):", "low(1-4)"),
                        ("🟡 Media   (5–9):", "medium(5-9)"),
                        ("🟠 Alta  (10-14):", "high(10-14)"),
                        ("🔴 Crítica (15+):", "very_high(15+)")]:
        n = dist.get(key, 0)
        lines.append(f"  {label}  {n} funciones")

    if r.hotspots:
        lines += ["", "  🔥 TOP HOTSPOTS (complejidad × cambios Git)",
                  f"  {'ARCHIVO':<50} {'CC':>5}  {'COMMITS':>7}  {'RIESGO':>6}",
                  "  " + "─" * 72]
        for h in r.hotspots[:8]:
            name = h.filepath[-48:].ljust(50)
            lines.append(f"  {name}  {h.complexity_score:>5}  "
                         f"{h.change_count:>7}  {h.hotspot_score:>6.1f}")

    if r.docs.todos or r.docs.fixmes or r.docs.hacks:
        lines += ["", "  📝 DEUDA TÉCNICA EN CÓDIGO",
                  f"  TODOs:   {len(r.docs.todos)}",
                  f"  FIXMEs:  {len(r.docs.fixmes)}",
                  f"  HACKs:   {len(r.docs.hacks)}",
                  f"  Ratio documentación: {int(r.docs.docstring_ratio*100)}%"]

    if r.duplication.duplication_ratio > 0:
        lines += ["", "  🔁 DUPLICACIÓN",
                  f"  Ratio:   {int(r.duplication.duplication_ratio*100)}%",
                  f"  Bloques: {len(r.duplication.blocks)}"]

    if r.coupling.dead_files:
        lines += ["", f"  ⚠️  Posible código muerto: {len(r.coupling.dead_files)} archivos"]

    return "\n".join(lines)
