#!/usr/bin/env python3
"""
generate_report.py — Agencia de Transición
Consolida todos los outputs markdown de un run y los exporta a Word (.docx).

Uso:
    python .axetrules/core/drivers/generate_report.py
        → run más reciente → 00_summary/CONSOLIDATED_REPORT.md
                           → 00_summary/INFORME_TRANSICION.docx

    python .axetrules/core/drivers/generate_report.py --run-dir <ruta>
    python .axetrules/core/drivers/generate_report.py --md-only
    python .axetrules/core/drivers/generate_report.py --docx-only
"""
from __future__ import annotations

import re
import sys
import json
import os
import codecs
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ── Constantes ────────────────────────────────────────────────────────────────

PHASES: dict[str, dict[str, Any]] = {
    "00_deteccion": {
        "label": "Detección de Plataforma",
        "label_emoji": "🔎 Detección de Plataforma",
        "order": 0,
    },
    "01_scout": {
        "label": "Scout — Descubrimiento de Repositorios",
        "label_emoji": "🕵️ Scout — Descubrimiento",
        "order": 1,
    },
    "02_analyst": {
        "label": "Analyst — Stack y Calidad",
        "label_emoji": "📊 Analyst — Stack y Calidad",
        "order": 2,
    },
    "03_architect": {
        "label": "Architect — Arquitectura",
        "label_emoji": "🏛️ Architect — Arquitectura",
        "order": 3,
    },
    "04_auditor": {
        "label": "Auditor — Seguridad",
        "label_emoji": "🔐 Auditor — Seguridad",
        "order": 4,
    },
    "05_strategist": {
        "label": "Strategist — Roadmap de Transición",
        "label_emoji": "🚀 Strategist — Roadmap",
        "order": 5,
    },
    "06_access-readiness": {
        "label": "Access Readiness — Accesos Día 1",
        "label_emoji": "🔑 Access Readiness — Accesos Día 1",
        "order": 6,
    },
    "07_app-inventory": {
        "label": "App Inventory — Inventario de Aplicaciones",
        "label_emoji": "📋 App Inventory — Inventario de Aplicaciones",
        "order": 7,
    },
    "08_dependency-mapping": {
        "label": "Dependency Mapping — Dependencias",
        "label_emoji": "🕸️ Dependency Mapping — Dependencias",
        "order": 8,
    },
    "09_api-integration": {
        "label": "API Integration — Catálogo de APIs",
        "label_emoji": "🔌 API Integration — Catálogo de APIs",
        "order": 9,
    },
    "10_business-capability": {
        "label": "Business Capability — Capacidades de Negocio",
        "label_emoji": "💼 Business Capability — Capacidades de Negocio",
        "order": 10,
    },
    "11_functional-flow": {
        "label": "Functional Flow — Flujos de Proceso",
        "label_emoji": "🔄 Functional Flow — Flujos de Proceso",
        "order": 11,
    },
    "12_knowledge-mgmt": {
        "label": "Knowledge Management — Base de Conocimiento",
        "label_emoji": "🧠 Knowledge Mgmt — Base de Conocimiento",
        "order": 12,
    },
    "13_kt-capture": {
        "label": "KT Capture — Sesiones de Traspaso",
        "label_emoji": "🎙️ KT Capture — Sesiones de Traspaso",
        "order": 13,
    },
    "14_exit-criteria": {
        "label": "Exit Criteria — Criterios de Salida",
        "label_emoji": "✅ Exit Criteria — Criterios de Salida",
        "order": 14,
    },
    "15_command-control": {
        "label": "Command & Control — RAID y Decisiones Ejecutivas",
        "label_emoji": "🎯 Command & Control — RAID y Decisiones",
        "order": 15,
    },
    "16_database-analysis": {
        "label": "Database Analysis — Datos y Persistencia",
        "label_emoji": "🗄️ Database Analysis — Datos y Persistencia",
        "order": 11.1,
    },
    "17_performance-static": {
        "label": "Performance Static — Rendimiento Estático",
        "label_emoji": "⚡ Performance Static — Rendimiento Estático",
        "order": 11.2,
    },
    "18_observability-readiness": {
        "label": "Observability Readiness — Observabilidad",
        "label_emoji": "📡 Observability Readiness — Observabilidad",
        "order": 11.3,
    },
    "19_sox-audit": {
        "label": "SOX Audit — Controles y Auditoría",
        "label_emoji": "🧾 SOX Audit — Controles y Auditoría",
        "order": 11.4,
    },
    "20_appsec-deep": {
        "label": "AppSec Deep — Seguridad Aplicativa",
        "label_emoji": "🛡️ AppSec Deep — Seguridad Aplicativa",
        "order": 11.5,
    },
    "21_modularity-analysis": {
        "label": "Modularity Analysis — Modularidad y Acoplamiento",
        "label_emoji": "🧩 Modularity Analysis — Modularidad y Acoplamiento",
        "order": 11.6,
    },
    "22_devops-readiness": {
        "label": "DevOps Readiness — CI/CD y Entrega",
        "label_emoji": "🚀 DevOps Readiness — CI/CD y Entrega",
        "order": 11.7,
    },
    "23_testing-readiness": {
        "label": "Testing Readiness — Pruebas y Cobertura Evidenciada",
        "label_emoji": "🧪 Testing Readiness — Pruebas y Cobertura Evidenciada",
        "order": 11.8,
    },
    "00_summary": {
        "label": "Resumen Completo",
        "label_emoji": "📋 Resumen Completo",
        "order": 99,
        "is_summary": True,
    },
}

PHASE_ORDER = [
    folder
    for folder, conf in sorted(PHASES.items(), key=lambda item: item[1]["order"])
    if not conf.get("is_summary")
]

PHASE_LABELS = {folder: conf["label"] for folder, conf in PHASES.items()}
PHASE_LABELS_EMOJI = {folder: conf["label_emoji"] for folder, conf in PHASES.items()}

SKIP_FILES = {"INDEX.md", "FULL_REPORT.md", "CONSOLIDATED_REPORT.md"}

MONTHS_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


# ── Descubrir raíz ────────────────────────────────────────────────────────────

def _find_axetrules_root() -> Path:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".axetrules").exists():
            return parent / ".axetrules"
    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir, *script_dir.parents]:
        if (parent / ".axetrules").exists():
            return parent / ".axetrules"
        if parent.name == ".axetrules":
            return parent
    raise FileNotFoundError(
        "No se encontró .axetrules. Ejecuta desde el workspace raíz."
    )


def find_latest_run(axetrules: Optional[Path] = None) -> Path:
    """Retorna el directorio del run más reciente en output/."""
    root = axetrules or _find_axetrules_root()
    output_dir = root / "output"
    if not output_dir.exists():
        raise FileNotFoundError(f"No existe {output_dir}")
    candidates = [
        run_dir
        for proj_dir in sorted(output_dir.iterdir()) if proj_dir.is_dir()
        for run_dir in sorted(proj_dir.iterdir()) if run_dir.is_dir()
    ]
    if not candidates:
        raise FileNotFoundError("No hay runs en output/. Ejecuta el pipeline primero.")
    return candidates[-1]


def _resolve_phase_directories(run_dir: Path) -> tuple[list[Path], list[str]]:
    """
    Resuelve las carpetas de fase en orden único.

    Política para carpetas no catalogadas: se incluyen al final para evitar
    pérdida silenciosa de contenido y se reportan como uncatalogued_phases.
    """
    all_folders = sorted(d for d in run_dir.iterdir() if d.is_dir())
    known = [run_dir / phase for phase in PHASE_ORDER if (run_dir / phase).exists()]
    remaining = [d for d in all_folders if d not in known and d.name != "00_summary"]
    uncatalogued = [d.name for d in remaining]
    return known + remaining, uncatalogued


def _decode_markdown_bytes(data: bytes) -> tuple[str, Optional[str], bool]:
    """
    Intenta decodificar markdown en codificaciones comunes.

    Retorna (texto, warning, degraded):
    - warning: mensaje legible cuando hubo degradacion.
    - degraded: True si se usaron reemplazos y debe reportarse como parcial.
    """
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        try:
            return data.decode("utf-16"), None, False
        except UnicodeDecodeError:
            pass

    if len(data) >= 4 and len(data) % 2 == 0:
        odd_nulls = sum(1 for i in range(1, len(data), 2) if data[i] == 0)
        even_nulls = sum(1 for i in range(0, len(data), 2) if data[i] == 0)
        half = len(data) // 2

        if odd_nulls >= max(1, half // 3):
            try:
                return data.decode("utf-16-le"), None, False
            except UnicodeDecodeError:
                pass

        if even_nulls >= max(1, half // 3):
            try:
                return data.decode("utf-16-be"), None, False
            except UnicodeDecodeError:
                pass

    try:
        return data.decode("utf-8"), None, False
    except UnicodeDecodeError:
        pass

    return data.decode("utf-8", errors="replace"), "decodificacion degradada (utf-8 con reemplazo)", True


# ── Consolidación markdown ────────────────────────────────────────────────────

def consolidate(
    run_dir: Path,
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[str, list[str]]:
    """
    Lee todos los archivos markdown del run en orden de fase
    y los une en un solo documento markdown estructurado.
    """
    project_name = run_dir.parent.name
    run_id = run_dir.name
    now = datetime.now()
    ts = f"{now.day} de {MONTHS_ES[now.month]} de {now.year}"

    lines: list[str] = [
        f"# Informe de Transición de Software",
        "",
        f"**Proyecto:** {project_name.replace('-', ' ').title()}  ",
        f"**Run ID:** `{run_id}`  ",
        f"**Fecha:** {ts}  ",
        f"**Generado por:** Agencia de Transición  ",
        "",
        "---",
        "",
    ]

    sections: list[str] = []
    skipped_files: list[str] = []

    phase_dirs, uncatalogued = _resolve_phase_directories(run_dir)

    for phase_dir in phase_dirs:
        phase_folder = phase_dir.name

        md_files = sorted(
            p for p in phase_dir.rglob("*.md")
            if p.name not in SKIP_FILES
        )
        if not md_files:
            continue

        if phase_folder in PHASES:
            label = PHASE_LABELS[phase_folder]
        else:
            label = phase_folder.replace("-", " ").replace("_", " ").title()

        lines += ["", f"# {label}", ""]
        sections.append(label)

        for md_file in md_files:
            rel_path = str(md_file.relative_to(run_dir))
            raw = ""
            read_issue: Optional[str] = None
            degraded = False

            try:
                payload = md_file.read_bytes()
                raw, decode_warning, degraded = _decode_markdown_bytes(payload)
                if decode_warning:
                    read_issue = decode_warning
            except OSError as exc:
                read_issue = f"OSError: {exc}"
                skipped_files.append(rel_path)
                raw = ""

            if degraded:
                skipped_files.append(rel_path)

            raw = raw.strip()

            if read_issue:
                lines.append(f"> ⚠️ Archivo no procesable: {rel_path} ({read_issue})")
                lines.append("")

            if not raw:
                continue

            file_lines = raw.split("\n")

            # Eliminar el H1 propio del archivo (ya está como encabezado de sección)
            start = 0
            if file_lines and file_lines[0].startswith("# "):
                start = 1
                while start < len(file_lines) and file_lines[start].strip() in ("", "---"):
                    start += 1

            # Degradar headings internos: H2..H6 -> min(n+1, 4)
            adjusted: list[str] = []
            for ln in file_lines[start:]:
                heading_match = re.match(r"^(#{2,6})\s+(.*)$", ln)
                if heading_match:
                    src_level = len(heading_match.group(1))
                    target_level = min(src_level + 1, 4)
                    adjusted.append("#" * target_level + " " + heading_match.group(2))
                    continue
                adjusted.append(ln)

            content = "\n".join(adjusted).strip()
            if content:
                lines.append(content)
                lines.append("")

    if not sections:
        lines.append("> No se encontraron outputs en este run. Ejecuta el pipeline primero.\n")

    if metadata is not None:
        metadata["skipped_files"] = sorted(set(skipped_files))
        metadata["uncatalogued_phases"] = uncatalogued

    return "\n".join(lines), sections


# ── Formateo inline ───────────────────────────────────────────────────────────

_INLINE_RE = re.compile(
    r"\*\*\*(.+?)\*\*\*"           # ***bold+italic***
    r"|\*\*(.+?)\*\*"               # **bold**
    r"|__(.+?)__"                   # __bold__
    r"|\*([^*\n]+?)\*"              # *italic*
    r"|_([^_\n]+?)_"                # _italic_
    r"|~~(.+?)~~"                   # ~~strikethrough~~
    r"|`([^`\n]+?)`"                # `inline code`
    r"|\[([^\]]+)\]\([^)]+\)"       # [text](url) — renderiza solo el texto
)

_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0000FE00-\U0000FEFF]+"
)

_TABLE_SEP_RE = re.compile(r"^\|[\s|:=-]+\|$")


def _strip_heading(text: str) -> str:
    """Limpia emojis y marcado residual para headings Word."""
    text = _EMOJI_RE.sub("", text).strip()
    text = re.sub(r"\*+", "", text).strip()
    return text


def _apply_inline(para, text: str) -> None:
    """Aplica formato inline a un párrafo Word."""
    from docx.shared import Pt

    # Defensa en profundidad: evita costo regex elevado en líneas extremas.
    if len(text) > 5000:
        para.add_run(text)
        return

    last = 0
    for m in _INLINE_RE.finditer(text):
        s, e = m.span()
        if s > last:
            para.add_run(text[last:s])
        g = m.groups()
        if g[0]:
            r = para.add_run(g[0]); r.bold = r.italic = True
        elif g[1]:
            para.add_run(g[1]).bold = True
        elif g[2]:
            para.add_run(g[2]).bold = True
        elif g[3]:
            para.add_run(g[3]).italic = True
        elif g[4]:
            para.add_run(g[4]).italic = True
        elif g[5]:
            r = para.add_run(g[5]); r.font.strike = True
        elif g[6]:
            r = para.add_run(g[6])
            r.font.name = "Courier New"
            r.font.size = Pt(9)
        elif g[7]:
            para.add_run(g[7])  # link text only
        last = e

    if last < len(text):
        para.add_run(text[last:])


# ── Helpers Word ──────────────────────────────────────────────────────────────

def _add_code_block(doc, code: str) -> None:
    """Bloque de código: monoespaciado con fondo gris."""
    from docx.shared import Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    for line in code.split("\n"):
        p = doc.add_paragraph()
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "F2F2F2")
        pPr.append(shd)
        r = p.add_run(line if line else " ")
        r.font.name = "Courier New"
        r.font.size = Pt(9)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = None


def _add_table(doc, rows: list[str]) -> None:
    """Convierte filas markdown en tabla Word.

    Solo marca cabecera cuando existe fila separadora estilo markdown.
    """
    from docx.shared import Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    has_separator = any(_TABLE_SEP_RE.match(row.strip()) for row in rows[:2])

    parsed: list[list[str]] = []
    for row in rows:
        if _TABLE_SEP_RE.match(row.strip()):
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if any(c for c in cells):
            parsed.append(cells)

    if not parsed:
        return

    max_cols = max(len(r) for r in parsed)
    parsed = [r + [""] * (max_cols - len(r)) for r in parsed]

    tbl = doc.add_table(rows=len(parsed), cols=max_cols)
    tbl.style = "Table Grid"

    for i, row in enumerate(parsed):
        for j, cell_text in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = ""
            para = cell.paragraphs[0]
            _apply_inline(para, cell_text)
            for run in para.runs:
                run.font.size = Pt(10)
                if has_separator and i == 0:
                    run.bold = True

            if has_separator and i == 0:
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "D6E4F0")
                tcPr.append(shd)

    doc.add_paragraph()


def _add_hr(doc) -> None:
    """Línea horizontal decorativa."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "2E74B5")
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.paragraph_format.space_after = Pt(6)


def _is_table_block(rows: list[str]) -> bool:
    """Valida que el bloque sea tabla markdown (requiere fila separadora)."""
    if len(rows) < 2:
        return False
    return any(_TABLE_SEP_RE.match(row.strip()) for row in rows[:2])


# ── Conversión a Word ─────────────────────────────────────────────────────────

def md_to_docx(md_content: str, output_path: Path, project_name: str) -> None:
    """Convierte el markdown consolidado a un documento Word estructurado."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        print("  ✗  python-docx no está instalado.")
        print("     pip install python-docx --break-system-packages")
        raise

    doc = Document()

    # Márgenes
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3.0)
        section.right_margin  = Cm(2.5)

    # Fuente base
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    # Estilos de encabezado
    _H_COLORS = {
        1: RGBColor(0x1F, 0x49, 0x7D),  # azul oscuro
        2: RGBColor(0x2E, 0x74, 0xB5),  # azul medio
        3: RGBColor(0x1F, 0x49, 0x7D),  # azul oscuro
        4: RGBColor(0x2E, 0x74, 0xB5),
    }
    _H_SIZES = {1: Pt(18), 2: Pt(14), 3: Pt(12), 4: Pt(11)}

    for lvl in (1, 2, 3, 4):
        try:
            style = doc.styles[f"Heading {lvl}"]
            style.font.name = "Calibri"
            style.font.bold = True
            style.font.size = _H_SIZES[lvl]
            style.font.color.rgb = _H_COLORS[lvl]
            if lvl == 4:
                style.font.italic = True
        except Exception:
            pass

    # ── Portada ───────────────────────────────────────────────────────────────
    now = datetime.now()
    date_str = f"{now.day} de {MONTHS_ES[now.month]} de {now.year}"
    display_name = project_name.replace("-", " ").title()

    for _ in range(4):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("INFORME DE TRANSICIÓN DE SOFTWARE")
    r.font.size = Pt(22); r.font.bold = True
    r.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(display_name)
    r.font.size = Pt(16)
    r.font.color.rgb = RGBColor(0x2E, 0x74, 0xB5)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(date_str)
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor(0x70, 0x70, 0x70)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Generado por Agencia de Transición de Software")
    r.font.size = Pt(10); r.font.italic = True
    r.font.color.rgb = RGBColor(0xA0, 0xA0, 0xA0)

    doc.add_page_break()

    # ── Parsear contenido markdown ────────────────────────────────────────────
    lines = md_content.split("\n")
    i = 0
    in_code = False
    code_lang = ""
    code_lines: list[str] = []
    first_h1 = True   # el primer H1 es el título del doc (ya está en portada)
    first_hr = True    # el primer --- separa la cabecera del contenido

    while i < len(lines):
        line = lines[i]

        # ── Bloque de código ──────────────────────────────────────────────────
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line[3:].strip()
                code_lines = []
            else:
                in_code = False
                label = f"[{code_lang}]" if code_lang else ""
                if label:
                    p = doc.add_paragraph()
                    r = p.add_run(label)
                    r.font.size = Pt(8)
                    r.font.italic = True
                    r.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
                    p.paragraph_format.space_after = Pt(0)
                _add_code_block(doc, "\n".join(code_lines))
                doc.add_paragraph()
                code_lang = ""
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # ── Tabla ─────────────────────────────────────────────────────────────
        if line.startswith("|") and "|" in line[1:]:
            tbl_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                tbl_lines.append(lines[i])
                i += 1

            if _is_table_block(tbl_lines):
                _add_table(doc, tbl_lines)
            else:
                for row in tbl_lines:
                    p = doc.add_paragraph()
                    _apply_inline(p, row)
            continue

        # ── Encabezados ───────────────────────────────────────────────────────
        if line.startswith("#### "):
            doc.add_paragraph(_strip_heading(line[5:]), style="Heading 4")

        elif line.startswith("### "):
            doc.add_paragraph(_strip_heading(line[4:]), style="Heading 3")

        elif line.startswith("## "):
            doc.add_paragraph(_strip_heading(line[3:]), style="Heading 2")

        elif line.startswith("# "):
            heading = _strip_heading(line[2:])
            if first_h1:
                # Título del documento: no repetir en portada, hacer intro
                first_h1 = False
                p = doc.add_paragraph()
                r = p.add_run(heading)
                r.font.size = Pt(14)
                r.font.bold = True
                r.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
            else:
                doc.add_page_break()
                doc.add_paragraph(heading, style="Heading 1")

        # ── Separador horizontal ──────────────────────────────────────────────
        elif line.strip() in ("---", "***", "___"):
            if first_hr:
                first_hr = False
                doc.add_paragraph()  # espacio después del bloque de cabecera
            else:
                _add_hr(doc)

        # ── Cita / blockquote ─────────────────────────────────────────────────
        elif line.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.4)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            _apply_inline(p, line[2:])
            for r in p.runs:
                r.italic = True
                r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

        # ── Checkbox ──────────────────────────────────────────────────────────
        elif line.startswith("- [ ] ") or line.startswith("- [x] "):
            checked = line.startswith("- [x] ")
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.left_indent = Inches(0.25)
            _apply_inline(p, ("☑ " if checked else "☐ ") + line[6:])

        # ── Lista con viñetas ─────────────────────────────────────────────────
        elif re.match(r"^[-*+] ", line):
            p = doc.add_paragraph(style="List Bullet")
            _apply_inline(p, line[2:])

        # ── Lista numerada ────────────────────────────────────────────────────
        elif re.match(r"^\d+\. ", line):
            p = doc.add_paragraph(style="List Number")
            _apply_inline(p, re.sub(r"^\d+\. ", "", line))

        # ── Línea vacía ───────────────────────────────────────────────────────
        elif not line.strip():
            pass

        # ── Párrafo normal ────────────────────────────────────────────────────
        else:
            p = doc.add_paragraph()
            _apply_inline(p, line)

        i += 1

    doc.save(str(output_path))


# ── Orquestador principal ─────────────────────────────────────────────────────

def _copy_to_downloads(src: Path, project_name: str) -> dict[str, Any]:
    """Copia un archivo a Downloads y retorna estado detallado de la operación."""
    import shutil

    override_dir = (
        Path(os.environ["AGENCIA_DOWNLOADS_DIR"])
        if "AGENCIA_DOWNLOADS_DIR" in os.environ
        else None
    )
    downloads = override_dir or (Path.home() / "Downloads")
    if not downloads.exists():
        return {
            "status": "skipped",
            "path": None,
            "reason": f"{downloads} no existe",
            "directory": str(downloads),
        }

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    safe_project = project_name.upper().replace(" ", "_")
    dest = downloads / f"INFORME_{safe_project}_{ts}{src.suffix}"

    try:
        shutil.copy2(src, dest)
    except OSError as exc:
        return {
            "status": "skipped",
            "path": None,
            "reason": f"Error copiando a descargas: {exc}",
            "directory": str(downloads),
        }

    return {
        "status": "ok",
        "path": str(dest),
        "reason": None,
        "directory": str(downloads),
    }


def _find_newer_sources_than(run_dir: Path, reference_file: Path) -> list[Path]:
    """Retorna fuentes markdown más nuevas que un consolidado existente."""
    if not reference_file.exists():
        return []

    ref_mtime = reference_file.stat().st_mtime
    phase_dirs, _ = _resolve_phase_directories(run_dir)
    newer: list[Path] = []
    for phase_dir in phase_dirs:
        for md_file in phase_dir.rglob("*.md"):
            if md_file.name in SKIP_FILES:
                continue
            if md_file.stat().st_mtime > ref_mtime:
                newer.append(md_file)
    return sorted(newer)


def regenerate_index(run_dir: Path) -> Path:
    """Regenera INDEX.md escaneando el filesystem del run completo.

    Incluye outputs del pipeline Python Y de los agentes LLM extendidos.
    """
    from datetime import datetime as _dt

    project_name = run_dir.parent.name
    run_id = run_dir.name
    axetrules = run_dir.parent.parent.parent  # output/<proj>/<run> → .axetrules/
    ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# 📁 Output — {project_name}",
        f"\n**Run ID:** `{run_id}`  ",
        f"**Generado:** {ts}  \n",
        "---\n",
    ]

    ordered_dirs, _ = _resolve_phase_directories(run_dir)
    for phase_dir in ordered_dirs:
        if phase_dir.name == "00_summary":
            continue  # resumen al final
        md_files = sorted(
            p for p in phase_dir.rglob("*.md") if p.name not in SKIP_FILES
        )
        if not md_files:
            continue
        if phase_dir.name in PHASE_LABELS_EMOJI:
            label = PHASE_LABELS_EMOJI[phase_dir.name]
        else:
            derived = phase_dir.name.replace("-", " ").replace("_", " ").title()
            label = f"📁 {derived}"
        lines.append(f"## {label}\n")
        for filepath in md_files:
            rel = filepath.relative_to(axetrules)
            lines.append(f"- [{filepath.name}]({rel})")
        lines.append("")

    # Summary al final
    summary_dir = run_dir / "00_summary"
    if summary_dir.exists():
        summary_files = sorted(
            p for p in summary_dir.rglob("*.md") if p.name not in SKIP_FILES
        )
        if summary_files:
            lines.append(f"## {PHASE_LABELS_EMOJI['00_summary']}\n")
            for filepath in summary_files:
                rel = filepath.relative_to(axetrules)
                lines.append(f"- [{filepath.name}]({rel})")
            lines.append("")

    lines.append(f"\n---\n\n*Generado por Agencia de Transición — {ts}*\n")
    content = "\n".join(lines)
    index_path = run_dir / "INDEX.md"
    index_path.write_text(content, encoding="utf-8")
    return index_path


def generate(
    run_dir: Optional[Path] = None,
    md_only: bool = False,
    docx_only: bool = False,
) -> dict[str, Any]:
    """
    Consolida y exporta el informe.
    Retorna un dict con las claves 'markdown' y/o 'docx' apuntando a los archivos,
    y 'docx_downloads' / 'markdown_downloads' con las copias en ~/Downloads.
    """
    if run_dir is None:
        run_dir = find_latest_run()

    project_name = run_dir.parent.name
    summary_dir = run_dir / "00_summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    md_path   = summary_dir / "CONSOLIDATED_REPORT.md"
    docx_path = summary_dir / f"INFORME_TRANSICION_{project_name.upper()}.docx"

    result: dict[str, Any] = {
        "status": "SUCCESS",
        "sections_included": 0,
        "sections": [],
        "skipped_files": [],
        "uncatalogued_phases": [],
        "downloads": {
            "status": "skipped",
            "reason": "No se intentaron copias todavía",
            "directory": str(Path.home() / "Downloads"),
            "markdown": None,
            "docx": None,
        },
    }

    # Regenerar INDEX.md con todos los outputs (CORE + extendidos)
    print(f"  🗂️   Actualizando INDEX.md…")
    index_path = regenerate_index(run_dir)
    result["index"] = index_path
    result["index_path"] = str(index_path)
    print(f"      → {index_path}")

    if not docx_only:
        print(f"  📄  Consolidando markdown…")
        consolidation_meta: dict[str, Any] = {}
        md_content, sections = consolidate(run_dir, metadata=consolidation_meta)
        md_path.write_text(md_content, encoding="utf-8", errors="replace")
        result["markdown"] = md_path
        result["markdown_path"] = str(md_path)
        result["sections"] = sections
        result["sections_included"] = len(sections)
        result["skipped_files"] = consolidation_meta.get("skipped_files", [])
        result["uncatalogued_phases"] = consolidation_meta.get("uncatalogued_phases", [])
        print(f"      → {md_path}")

        dl_md = _copy_to_downloads(md_path, project_name)
        if dl_md["status"] == "ok":
            result["markdown_downloads"] = Path(dl_md["path"])
            result["downloads"]["markdown"] = dl_md["path"]
            result["downloads"]["directory"] = dl_md["directory"]
        else:
            result["downloads"]["reason"] = dl_md["reason"]
            print(f"  ⚠️  No se copió markdown a descargas: {dl_md['reason']}", file=sys.stderr)
    else:
        if not md_path.exists():
            raise FileNotFoundError(
                f"No se encontró {md_path}. Ejecuta sin --docx-only primero."
            )

        newer_sources = _find_newer_sources_than(run_dir, md_path)
        if newer_sources:
            print(
                (
                    "  ⚠️  CONSOLIDATED_REPORT.md es más antiguo que "
                    f"{len(newer_sources)} archivo(s) fuente. "
                    "Considera regenerar sin --docx-only."
                ),
                file=sys.stderr,
            )

        md_content = md_path.read_text(encoding="utf-8")
        result["markdown_path"] = str(md_path)

    if not md_only:
        print(f"  📝  Generando Word…")
        md_to_docx(md_content, docx_path, project_name)
        result["docx"] = docx_path
        result["docx_path"] = str(docx_path)
        print(f"      → {docx_path}")

        dl_docx = _copy_to_downloads(docx_path, project_name)
        if dl_docx["status"] == "ok":
            result["docx_downloads"] = Path(dl_docx["path"])
            result["downloads"]["docx"] = dl_docx["path"]
            result["downloads"]["directory"] = dl_docx["directory"]
        else:
            result["downloads"]["reason"] = dl_docx["reason"]
            print(f"  ⚠️  No se copió Word a descargas: {dl_docx['reason']}", file=sys.stderr)

    if result.get("skipped_files"):
        result["status"] = "PARTIAL"

    downloads = result["downloads"]
    if downloads.get("markdown") or downloads.get("docx"):
        downloads["status"] = "ok"
        downloads["reason"] = None
    else:
        downloads["status"] = "skipped"

    return result


def _result_to_json(result: dict[str, Any]) -> str:
    """Serializa el contrato de salida para consumo del Director."""

    def _default(obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Tipo no serializable: {type(obj).__name__}")

    return json.dumps(result, ensure_ascii=False, default=_default, indent=2)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Genera informe consolidado Word")
    parser.add_argument(
        "--run-dir", metavar="RUTA",
        help="Directorio del run (ej: .axetrules/output/mi-repo/2025-01-15_10-30). "
             "Por defecto: el más reciente.",
    )
    parser.add_argument(
        "--md-only", action="store_true",
        help="Solo genera el markdown consolidado, sin Word.",
    )
    parser.add_argument(
        "--docx-only", action="store_true",
        help="Solo genera el Word (requiere CONSOLIDATED_REPORT.md existente).",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir) if args.run_dir else None

    print("\n🗂️  Agencia de Transición — Generador de Informes")
    print("━" * 50)

    try:
        result = generate(
            run_dir=run_dir,
            md_only=args.md_only,
            docx_only=args.docx_only,
        )
        print("\n✅  REPORT GENERATOR")
        print("━" * 50)
        print(f"Secciones consolidadas : {result.get('sections_included', 0)}")
        for section in result.get("sections", []):
            print(f"  ✅ {section}")

        print("\nArchivos generados:")
        if "markdown" in result:
            print(f"    📄 Markdown  : {result['markdown']}")
        if "docx" in result:
            print(f"    📝 Word      : {result['docx']}")

        downloads = result.get("downloads", {})
        if downloads.get("status") == "ok":
            if downloads.get("markdown"):
                print(f"    📄 Descargas : {downloads['markdown']}")
            if downloads.get("docx"):
                print(f"    📝 Descargas : {downloads['docx']}")
        else:
            print(f"    ⚠️ Descargas : {downloads.get('reason')}")

        print("━" * 50)
        print("---JSON---")
        print(_result_to_json(result))
        print("---JSON---")
    except FileNotFoundError as e:
        print(f"\n✗  {e}", file=sys.stderr)
        failed = {
            "status": "FAILED",
            "error": str(e),
            "sections_included": 0,
            "sections": [],
        }
        print("---JSON---")
        print(_result_to_json(failed))
        print("---JSON---")
        sys.exit(1)
    except ImportError as e:
        print(f"\n✗  Dependencia faltante: {e}", file=sys.stderr)
        print("   Ejecuta: pip install python-docx --break-system-packages", file=sys.stderr)
        failed = {
            "status": "FAILED",
            "error": f"ImportError: {e}",
            "sections_included": 0,
            "sections": [],
        }
        print("---JSON---")
        print(_result_to_json(failed))
        print("---JSON---")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗  Error inesperado: {e}", file=sys.stderr)
        raise
