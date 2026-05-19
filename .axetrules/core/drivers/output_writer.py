#!/usr/bin/env python3
"""
output_writer.py — Agencia de Transición
Sistema centralizado de escritura de outputs.

Cada fase del pipeline genera su carpeta dentro de:
  .axetrules/output/<proyecto>/<timestamp>/
    ├── 00_deteccion/
    │   └── platform_detection.md
    ├── 01_scout/
    │   └── projects_discovered.md
    ├── 02_analyst/
    │   ├── stack_profile.md
    │   └── quality_report.md
    ├── 03_architect/
    │   └── architecture_report.md
    ├── 04_auditor/
    │   ├── secrets_report.md
    │   └── cve_report.md
    ├── 05_strategist/
    │   └── TRANSITION_ROADMAP.md
    └── 00_summary/
        └── FULL_REPORT.md

Uso:
    from core.drivers.output_writer import OutputWriter
    writer = OutputWriter(project_name="mi-repo")
    writer.write("analyst", "stack_profile.md", contenido_markdown)
    path = writer.get_phase_dir("analyst")
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


# Orden y nombres de las fases
PHASES = {
    "deteccion":          "00_deteccion",
    "scout":              "01_scout",
    "analyst":            "02_analyst",
    "architect":          "03_architect",
    "auditor":            "04_auditor",
    "strategist":         "05_strategist",
    "access-readiness":   "06_access-readiness",
    "app-inventory":      "07_app-inventory",
    "dependency-mapping": "08_dependency-mapping",
    "api-integration":    "09_api-integration",
    "business-capability":"10_business-capability",
    "functional-flow":    "11_functional-flow",
    "knowledge-mgmt":     "12_knowledge-mgmt",
    "kt-capture":         "13_kt-capture",
    "exit-criteria":      "14_exit-criteria",
    "command-control":    "15_command-control",
    "summary":            "00_summary",
}


def _find_axetrules_root() -> Path:
    """Sube desde el CWD hasta encontrar la carpeta .axetrules."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".axetrules").exists():
            return parent / ".axetrules"
    # Fallback: relativo al script
    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir, *script_dir.parents]:
        if (parent / ".axetrules").exists():
            return parent / ".axetrules"
        if parent.name == ".axetrules":
            return parent
    raise FileNotFoundError(
        "No se encontró la carpeta .axetrules. "
        "Ejecuta desde el directorio raíz del workspace."
    )


class OutputWriter:
    """
    Gestiona la escritura de todos los outputs de la agencia.

    Crea la estructura:
      .axetrules/output/<proyecto>/<YYYY-MM-DD_HH-MM>/
    """

    def __init__(
        self,
        project_name: str,
        run_id: Optional[str] = None,
        axetrules_root: Optional[Path] = None,
    ):
        self.project_name = project_name
        self.safe_name = _safe(project_name)
        self.run_id = run_id or datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.axetrules = axetrules_root or _find_axetrules_root()
        self.run_dir = self.axetrules / "output" / self.safe_name / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._manifest: dict = {
            "project": project_name,
            "run_id": self.run_id,
            "started_at": datetime.now().isoformat(),
            "files": [],
        }

    # ── API pública ───────────────────────────────────────────────────────────

    def write(self, phase: str, filename: str, content: str) -> Path:
        """
        Escribe un archivo de output para una fase.

        Args:
            phase:    Nombre de la fase (deteccion | scout | analyst | architect | auditor | strategist | summary)
            filename: Nombre del archivo (ej: "stack_profile.md")
            content:  Contenido markdown o texto

        Returns:
            Path absoluto del archivo creado
        """
        phase_dir = self.get_phase_dir(phase)
        filepath = phase_dir / filename
        filepath.write_text(content, encoding="utf-8")
        self._manifest["files"].append({
            "phase": phase,
            "file": filename,
            "path": str(filepath.relative_to(self.axetrules)),
            "written_at": datetime.now().isoformat(),
        })
        self._save_manifest()
        return filepath

    def get_phase_dir(self, phase: str) -> Path:
        """Retorna (y crea) el directorio de una fase."""
        folder = PHASES.get(phase, phase)
        d = self.run_dir / folder
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_run_dir(self) -> Path:
        return self.run_dir

    def list_outputs(self) -> list[dict]:
        """Lista todos los archivos generados en esta ejecución."""
        return self._manifest.get("files", [])

    def finalize(self, state: Optional[dict] = None) -> Path:
        """
        Cierra la ejecución: actualiza el manifiesto y genera el índice.
        Llama esto al final del pipeline completo.
        """
        self._manifest["finished_at"] = datetime.now().isoformat()
        if state:
            self._manifest["agency_state"] = state
        self._save_manifest()
        index_path = self._generate_index()
        return index_path

    # ── Helpers de formato ────────────────────────────────────────────────────

    @staticmethod
    def header(title: str, phase: str, project: str, url: str = "") -> str:
        """Genera un encabezado estándar para todos los reportes."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        url_line = f"**URL:** {url}  \n" if url else ""
        return (
            f"# {title}\n\n"
            f"**Proyecto:** {project}  \n"
            f"**Fase:** {phase}  \n"
            f"**Fecha:** {ts}  \n"
            f"{url_line}"
            f"\n---\n\n"
        )

    @staticmethod
    def section(title: str, content: str, level: int = 2) -> str:
        prefix = "#" * level
        return f"{prefix} {title}\n\n{content}\n"

    @staticmethod
    def table(headers: list[str], rows: list[list]) -> str:
        sep = "|".join(["---"] * len(headers))
        head = "| " + " | ".join(headers) + " |"
        divider = f"|{sep}|"
        body = "\n".join("| " + " | ".join(str(c) for c in row) + " |" for row in rows)
        return f"{head}\n{divider}\n{body}\n"

    @staticmethod
    def footer() -> str:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"\n---\n\n*Generado por Agencia de Transición — {ts}*\n"

    # ── Internos ──────────────────────────────────────────────────────────────

    def _save_manifest(self) -> None:
        manifest_path = self.run_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(self._manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _generate_index(self) -> Path:
        """Genera INDEX.md escaneando el sistema de archivos del run completo.

        Detecta archivos escritos tanto por el pipeline Python como por el
        Director LLM, garantizando que el índice siempre esté completo.
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# 📁 Output — {self.project_name}",
            f"\n**Run ID:** `{self.run_id}`  ",
            f"**Generado:** {ts}  \n",
            "---\n",
        ]

        phase_labels = {
            "deteccion":          "🔎 Detección de Plataforma",
            "scout":              "🕵️ Scout — Descubrimiento",
            "analyst":            "📊 Analyst — Stack & Calidad",
            "architect":          "🏛️ Architect — Arquitectura",
            "auditor":            "🔐 Auditor — Seguridad",
            "strategist":         "🚀 Strategist — Roadmap",
            "access-readiness":   "🔑 Access Readiness — Accesos Día 1",
            "app-inventory":      "📋 App Inventory — Inventario de Aplicaciones",
            "dependency-mapping": "🕸️ Dependency Mapping — Dependencias",
            "api-integration":    "🔌 API Integration — Catálogo de APIs",
            "business-capability":"💼 Business Capability — Capacidades de Negocio",
            "functional-flow":    "🔄 Functional Flow — Flujos de Proceso",
            "knowledge-mgmt":     "🧠 Knowledge Mgmt — Base de Conocimiento",
            "kt-capture":         "🎙️ KT Capture — Sesiones de Traspaso",
            "exit-criteria":      "✅ Exit Criteria — Criterios de Salida",
            "command-control":    "🎯 Command & Control — RAID & Decisiones",
            "summary":            "📋 Resumen Completo",
        }

        skip_files = {"INDEX.md", "FULL_REPORT.md", "CONSOLIDATED_REPORT.md"}

        for phase_key, folder_name in PHASES.items():
            phase_dir = self.run_dir / folder_name
            if not phase_dir.exists():
                continue
            # Escanear filesystem — incluye archivos del Director LLM y del Python
            md_files = sorted(
                p for p in phase_dir.rglob("*.md")
                if p.name not in skip_files
            )
            if not md_files:
                continue
            label = phase_labels.get(phase_key, phase_key)
            lines.append(f"## {label}\n")
            for filepath in md_files:
                rel = filepath.relative_to(self.axetrules)
                lines.append(f"- [{filepath.name}]({rel})")
            lines.append("")

        lines.append(self.footer())
        content = "\n".join(lines)
        index_path = self.run_dir / "INDEX.md"
        index_path.write_text(content, encoding="utf-8")
        return index_path


# ── Generadores de contenido por fase ────────────────────────────────────────

def build_detection_report(info, writer: OutputWriter) -> Path:
    """Genera el reporte de detección de plataforma."""
    _LABELS = {
        "gitlab": "GitLab", "github": "GitHub",
        "azure": "Azure DevOps", "bitbucket": "Bitbucket", "unknown": "Desconocida",
    }
    _ICONS = {"ALTA": "🟢", "MEDIA": "🟡", "BAJA": "🔴"}

    label = _LABELS.get(info.platform, info.platform)
    icon  = _ICONS.get(info.confidence, "⚪")

    content = writer.header("🔎 Detección de Plataforma", "Detección", writer.project_name)
    content += f"## Resultado\n\n"
    content += writer.table(
        ["Campo", "Valor"],
        [
            ["Plataforma",   f"{label} {icon}"],
            ["Confianza",    info.confidence],
            ["Base URL",     info.base_url],
            ["Project ID",   info.project_id],
            ["Nombre",       info.project_name],
            ["Grupo / Org",  info.group or "—"],
            ["Clone URL",    info.clone_url],
        ],
    )
    content += f"\n## Token Requerido\n\n"
    content += f"- **Scopes:** `{info.token_scopes}`\n"
    if info.token_url:
        content += f"- **Crear en:** {info.token_url}\n"
    if info.notes:
        content += f"\n> ⚠️ {info.notes}\n"
    content += writer.footer()
    return writer.write("deteccion", "platform_detection.md", content)


def build_scout_report(projects: list, writer: OutputWriter,
                        selected_name: str = "") -> Path:
    """Genera el reporte de discovery del Scout — todos los proyectos encontrados."""
    content = writer.header("🕵️ Scout — Proyectos Descubiertos", "Scout", writer.project_name)
    content += f"**Total encontrados:** {len(projects)}\n\n"
    if selected_name:
        content += f"**Repositorio seleccionado para análisis:** `{selected_name}`\n\n"
    if projects:
        rows = []
        for i, p in enumerate(projects, 1):
            marker = " ← analizado" if p.name == selected_name else ""
            rows.append([
                str(i),
                str(p.id),
                f"**{p.name}**{marker}" if p.name == selected_name else p.name,
                p.visibility,
                p.last_activity[:10] if p.last_activity else "—",
                p.default_branch,
            ])
        content += writer.table(
            ["#", "ID", "Nombre", "Visibilidad", "Última Actividad", "Rama Default"],
            rows,
        )
    else:
        content += "> No se encontraron proyectos (API no disponible o sin permisos).\n"
    content += writer.footer()
    return writer.write("scout", "projects_discovered.md", content)


def build_branches_report(branches: list, selected_branch: str,
                           writer: OutputWriter) -> Path:
    """Genera el reporte de todas las ramas del repo — siempre se guarda completo."""
    content = writer.header(
        "🌿 Scout — Ramas Descubiertas", "Scout", writer.project_name
    )
    content += f"**Total de ramas:** {len(branches)}\n\n"
    content += f"**Rama seleccionada para análisis:** `{selected_branch}`\n\n"
    if branches:
        rows = []
        for b in branches:
            name     = b.name if hasattr(b, "name") else str(b)
            default  = "★" if (hasattr(b, "is_default") and b.is_default) else ""
            protected= "🔒" if (hasattr(b, "is_protected") and b.is_protected) else ""
            date     = ""
            if hasattr(b, "last_commit_date") and b.last_commit_date:
                date = b.last_commit_date[:10]
            author   = getattr(b, "last_commit_author", "") or ""
            msg      = getattr(b, "last_commit_message", "") or ""
            msg      = msg[:60] + "…" if len(msg) > 60 else msg
            marker   = " ← analizada" if name == selected_branch else ""
            rows.append([
                f"**{name}**{marker}" if name == selected_branch else name,
                default,
                protected,
                date,
                author[:25],
                msg,
            ])
        content += writer.table(
            ["Rama", "Default", "Protegida", "Último Commit", "Autor", "Mensaje"],
            rows,
        )
    else:
        content += "> No se pudo obtener la lista de ramas (API no disponible).\n"
        content += f"\n> Rama analizada (ingresada manualmente): `{selected_branch}`\n"
    content += writer.footer()
    return writer.write("scout", "branches_discovered.md", content)


def build_stack_report(stack, quality, writer: OutputWriter, url: str = "") -> Path:
    """Genera el reporte de stack y calidad del Analyst."""
    grade = (
        "A" if quality.overall_score >= 90 else
        "B" if quality.overall_score >= 80 else
        "C" if quality.overall_score >= 60 else
        "D" if quality.overall_score >= 40 else "F"
    )
    grade_icon = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⚫"}.get(grade, "")

    content = writer.header("📊 Analyst — Stack & Calidad", "Analyst", writer.project_name, url)

    # Stack
    content += "## Stack Tecnológico\n\n"
    content += writer.table(
        ["Campo", "Valor"],
        [
            ["Lenguaje Principal", stack.primary_language],
            ["Tipo de Proyecto",   stack.project_type],
            ["Frameworks",         ", ".join(stack.frameworks) or "—"],
            ["Bases de Datos",     ", ".join(stack.databases) or "—"],
            ["Infraestructura",    ", ".join(stack.infrastructure) or "—"],
            ["Framework de Tests", stack.test_framework],
        ],
    )

    # Lenguajes detallados
    if stack.languages:
        content += "\n### Distribución de Lenguajes\n\n"
        total = sum(stack.languages.values())
        rows = [
            [lang, str(count), f"{count/total*100:.1f}%"]
            for lang, count in stack.languages.items()
        ]
        content += writer.table(["Lenguaje", "Archivos", "% del Total"], rows)

    # Entry points
    if stack.entry_points:
        content += "\n### Entry Points\n\n"
        for ep in stack.entry_points:
            content += f"- `{ep}`\n"
        content += "\n"

    # Calidad
    content += f"\n## Score de Calidad: {quality.overall_score}/100 {grade_icon} ({grade})\n\n"
    content += writer.table(
        ["Elemento", "Estado", "Detalle"],
        [
            ["README",       "✅" if quality.has_readme    else "❌", f"Score: {quality.readme_score}/100" if quality.has_readme else "Ausente"],
            ["Tests",        "✅" if quality.has_tests     else "❌", f"Ratio: {quality.test_ratio*100:.0f}%" if quality.has_tests else "No detectados"],
            ["CI/CD",        "✅" if quality.has_ci_cd     else "❌", "Configurado" if quality.has_ci_cd else "No configurado"],
            ["Dockerfile",   "✅" if quality.has_dockerfile else "❌", ""],
            ["Linting",      "✅" if quality.has_linting   else "❌", ""],
            ["LICENSE",      "✅" if quality.has_license   else "❌", ""],
            ["CHANGELOG",    "✅" if quality.has_changelog else "❌", ""],
            [".gitignore",   "✅" if quality.has_gitignore else "❌", ""],
            [".env.example", "✅" if quality.has_env_example else "❌", ""],
        ],
    )
    content += writer.footer()
    return writer.write("analyst", "stack_quality_report.md", content)


def build_architecture_report(report, writer: OutputWriter, url: str = "") -> Path:
    """Genera el reporte de arquitectura del Architect."""
    content = writer.header("🏛️ Architect — Arquitectura", "Architect", writer.project_name, url)

    content += "## Resumen\n\n"
    content += writer.table(
        ["Campo", "Valor"],
        [
            ["Estilo de Despliegue",  f"{report.deployment_style.name} ({report.deployment_style.confidence})"],
            ["Patrón Principal",      f"{report.primary_pattern.name} — Score: {report.primary_pattern.score}/100"],
            ["Confianza",             report.primary_pattern.confidence],
            ["Violaciones",           str(len(report.layer_violations))],
            ["Servicios (monorepo)",  str(len(report.services))],
        ],
    )

    # Evidencia del patrón principal
    if report.primary_pattern.evidence:
        content += "\n### Evidencia Detectada\n\n"
        for ev in report.primary_pattern.evidence:
            content += f"- {ev}\n"
        content += "\n"

    # Patrones secundarios
    if report.secondary_patterns:
        content += "## Patrones Secundarios\n\n"
        rows = [[p.name, str(p.score), p.confidence] for p in report.secondary_patterns]
        content += writer.table(["Patrón", "Score", "Confianza"], rows)
        content += "\n"

    # Patrones de diseño GoF
    if report.design_patterns:
        content += "## Patrones de Diseño (GoF)\n\n"
        rows = [[p, str(len(files)), ", ".join(files[:2])] for p, files in report.design_patterns.items()]
        content += writer.table(["Patrón", "Implementaciones", "Archivos (muestra)"], rows)
        content += "\n"

    # Comunicación externa
    if report.external_comms:
        content += "## Comunicación Externa\n\n"
        rows = [[proto, str(len(files))] for proto, files in report.external_comms.items()]
        content += writer.table(["Protocolo", "Archivos"], rows)
        content += "\n"

    # Violaciones de capas
    if report.layer_violations:
        content += f"## ⚠️ Violaciones de Arquitectura ({len(report.layer_violations)})\n\n"
        for i, v in enumerate(report.layer_violations, 1):
            content += f"{i}. {v}\n"
        content += "\n"

    # Servicios (monorepo)
    if report.services:
        content += f"## Servicios Detectados ({len(report.services)})\n\n"
        rows = [
            [s.name, s.primary_language, ", ".join(s.frameworks[:2]) or "—",
             "✅" if s.has_dockerfile else "❌"]
            for s in report.services
        ]
        content += writer.table(["Servicio", "Lenguaje", "Frameworks", "Dockerfile"], rows)
        content += "\n"

    # Diagrama Mermaid
    content += "## Diagrama de Arquitectura\n\n"
    content += report.mermaid_diagram + "\n"
    content += writer.footer()
    return writer.write("architect", "architecture_report.md", content)


def build_security_report(secrets: list, cve_summary, writer: OutputWriter, url: str = "") -> Path:
    """Genera el reporte de seguridad del Auditor."""
    verdict = "✅ APTO PARA TRANSICIÓN" if not secrets and (not cve_summary or cve_summary.critical == 0) \
              else "⚠️ RIESGO DETECTADO"

    content = writer.header("🔐 Auditor — Seguridad", "Auditor", writer.project_name, url)
    content += f"## Veredicto: {verdict}\n\n"

    # Secretos
    content += f"## Secretos Expuestos ({len(secrets)})\n\n"
    if secrets:
        rows = [
            [s.secret_type, f"`{s.file_path}`", str(s.line_number), s.severity, s.redacted_snippet[:30]]
            for s in secrets
        ]
        content += writer.table(["Tipo", "Archivo", "Línea", "Severidad", "Fragmento"], rows)
        content += "\n### Recomendaciones\n\n"
        seen = set()
        for s in secrets:
            if s.recommendation and s.recommendation not in seen:
                content += f"- **{s.secret_type}:** {s.recommendation}\n"
                seen.add(s.recommendation)
    else:
        content += "> ✅ No se encontraron secretos expuestos.\n"
    content += "\n"

    # CVEs
    content += "## Vulnerabilidades de Dependencias\n\n"
    if cve_summary:
        content += writer.table(
            ["Severidad", "Cantidad"],
            [
                ["🔴 Crítico",  str(getattr(cve_summary, "critical", 0))],
                ["🟠 Alto",     str(getattr(cve_summary, "high", 0))],
                ["🟡 Medio",    str(getattr(cve_summary, "medium", 0))],
                ["🟢 Bajo",     str(getattr(cve_summary, "low", 0))],
            ],
        )
        if hasattr(cve_summary, "vulnerabilities") and cve_summary.vulnerabilities:
            content += "\n### Detalle de CVEs\n\n"
            rows = []
            for v in cve_summary.vulnerabilities[:20]:
                rows.append([
                    getattr(v, "id", "—"),
                    getattr(v, "package", "—"),
                    getattr(v, "severity", "—"),
                    str(getattr(v, "cvss", "—")),
                ])
            content += writer.table(["CVE ID", "Paquete", "Severidad", "CVSS"], rows)
    else:
        content += "> No se ejecutó análisis de CVEs o no se encontraron manifiestos.\n"

    content += writer.footer()
    return writer.write("auditor", "security_report.md", content)


def build_roadmap_report(
    stack, quality, arch_report, secrets: list,
    writer: OutputWriter, url: str = ""
) -> Path:
    """Genera el TRANSITION_ROADMAP.md del Strategist."""

    # Calcular índice de deuda
    violations = len(arch_report.layer_violations) if arch_report else 0
    debt = (
        (100 - quality.overall_score) * 0.4
        + violations * 5
        + len(secrets) * 10
    )

    strategy = (
        "Rehost / Replatform" if debt < 20 else
        "Refactor"            if debt < 50 else
        "Rearchitect"         if debt < 80 else
        "Rebuild"
    )

    content = writer.header("🚀 Strategist — Roadmap de Transición", "Strategist", writer.project_name, url)

    content += f"## Estrategia Seleccionada: **{strategy}**\n\n"
    content += writer.table(
        ["Métrica", "Valor"],
        [
            ["Índice de Deuda Técnica", f"{debt:.0f}/100"],
            ["Score de Calidad",        f"{quality.overall_score}/100"],
            ["Violaciones Arquitectura",str(violations)],
            ["Secretos Expuestos",      str(len(secrets))],
            ["Lenguaje Principal",      stack.primary_language],
            ["Patrón Actual",           arch_report.primary_pattern.name if arch_report else "—"],
        ],
    )

    content += "\n## Fase 1: Estabilización (Semanas 1-2) — Quick Wins\n\n"
    phase1 = []
    if secrets:
        phase1.append(f"- [ ] Rotar {len(secrets)} secreto(s) expuesto(s) en el código")
    if not quality.has_gitignore:
        phase1.append("- [ ] Agregar `.gitignore` apropiado")
    if not quality.has_env_example:
        phase1.append("- [ ] Crear `.env.example` con variables documentadas")
    if not quality.has_license:
        phase1.append("- [ ] Agregar archivo `LICENSE`")
    phase1.append("- [ ] Actualizar dependencias con CVEs críticos")
    content += "\n".join(phase1) + "\n"

    content += "\n## Fase 2: Refactorización (Semanas 3-6)\n\n"
    phase2 = []
    if violations > 0:
        phase2.append(f"- [ ] Corregir {violations} violación(es) de capas arquitectónicas")
    if not quality.has_tests:
        phase2.append("- [ ] Implementar suite de tests automatizados")
    elif quality.test_ratio < 0.3:
        phase2.append(f"- [ ] Aumentar cobertura de tests (actual: {quality.test_ratio*100:.0f}% → meta: 60%)")
    if not quality.has_linting:
        phase2.append("- [ ] Configurar herramienta de linting y formateo")
    if not quality.has_readme or quality.readme_score < 70:
        phase2.append("- [ ] Mejorar documentación (README, comentarios, docstrings)")
    phase2.append("- [ ] Refactorizar módulos con alta complejidad ciclomática")
    content += "\n".join(phase2) + "\n"

    content += "\n## Fase 3: Modernización (Semanas 7-12)\n\n"
    phase3 = []
    if not quality.has_dockerfile:
        phase3.append("- [ ] Contenerizar la aplicación con Docker")
    if not quality.has_ci_cd:
        phase3.append("- [ ] Implementar pipeline CI/CD completo")
    phase3.append("- [ ] Migrar a infraestructura cloud / actualizar stack")
    phase3.append("- [ ] Implementar health checks y readiness probes")
    content += "\n".join(phase3) + "\n"

    content += "\n## Fase 4: Optimización (Semanas 13+)\n\n"
    content += "- [ ] Agregar observabilidad (logs estructurados, métricas, trazas)\n"
    content += "- [ ] Implementar quality gates en el pipeline CI/CD\n"
    content += "- [ ] Documentación técnica completa (ADRs, diagramas actualizados)\n"
    content += "- [ ] Revisión de performance y optimización de queries\n"

    content += "\n## Estimación de Esfuerzo\n\n"
    content += writer.table(
        ["Fase", "Duración", "Riesgo", "Impacto"],
        [
            ["Estabilización", "2 semanas",  "🟢 Bajo",  "🔴 Alto"],
            ["Refactorización", "4 semanas", "🟡 Medio", "🟠 Alto"],
            ["Modernización",  "6 semanas",  "🟠 Medio", "🟡 Medio"],
            ["Optimización",   "Continuo",   "🟢 Bajo",  "🟢 Bajo"],
        ],
    )
    content += writer.footer()
    return writer.write("strategist", "TRANSITION_ROADMAP.md", content)


def build_full_summary(writer: OutputWriter, state: dict) -> Path:
    """Genera el reporte consolidado INDEX con links a todos los outputs."""
    content = writer.header(
        f"📋 Reporte Completo — {writer.project_name}",
        "Summary", writer.project_name
    )
    content += "## Archivos Generados\n\n"
    for f in writer.list_outputs():
        content += f"- **[{f['file']}]({f['path']})** — Fase: `{f['phase']}`\n"
    content += "\n## Estado del Pipeline\n\n"
    phases_done = state.get("phases_completed", [])
    all_phases = ["deteccion", "scout", "diagnose", "architect", "audit", "strategy"]
    for p in all_phases:
        icon = "✅" if p in phases_done else "⏳"
        content += f"- {icon} `{p}`\n"
    content += writer.footer()
    return writer.write("summary", "FULL_REPORT.md", content)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(name: str) -> str:
    """Convierte un nombre en un string seguro para usar como carpeta."""
    return (
        name.replace(" ", "-")
            .replace("/", "-")
            .replace("\\", "-")
            .replace(":", "")
            .lower()
    )


# ── CLI de diagnóstico ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    project = sys.argv[1] if len(sys.argv) > 1 else "test-project"
    writer = OutputWriter(project_name=project)
    test_content = (
        writer.header("Test Output", "Test", project)
        + "## Prueba\n\nEste es un archivo de prueba.\n"
        + writer.footer()
    )
    path = writer.write("analyst", "test.md", test_content)
    print(f"✅ Archivo de prueba creado: {path}")
    index = writer.finalize()
    print(f"✅ Índice generado: {index}")
    print(f"\n📁 Output en: {writer.get_run_dir()}")
