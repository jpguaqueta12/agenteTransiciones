from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "generate_report.py"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
GOLDEN_DOCX = GOLDEN_DIR / "generate_report_fixture_golden.docx"


def load_report_module():
    spec = importlib.util.spec_from_file_location("generate_report", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar generate_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def report_module():
    return load_report_module()


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    axetrules = tmp_path / ".axetrules"
    run = axetrules / "output" / "proyecto-demo" / "2026-05-19_10-00"

    scout = run / "01_scout"
    analyst = run / "02_analyst"
    auditor = run / "04_auditor"

    scout.mkdir(parents=True, exist_ok=True)
    analyst.mkdir(parents=True, exist_ok=True)
    auditor.mkdir(parents=True, exist_ok=True)

    (scout / "scout.md").write_text(
        "\n".join(
            [
                "# Scout Report",
                "",
                "## A",
                "### B",
                "#### C",
                "##### D",
                "",
                "> cita de validacion",
                "- [ ] pendiente",
                "- [x] completado",
            ]
        ),
        encoding="utf-8",
    )

    (analyst / "analyst.md").write_text(
        "\n".join(
            [
                "# Analyst Report",
                "",
                "| Col A | Col B |",
                "| --- | --- |",
                "| v1 | v2 |",
                "",
                "| ascii | diag |",
                "| sin | separador |",
                "| en | bloque |",
            ]
        ),
        encoding="utf-8",
    )

    (auditor / "auditor.md").write_text(
        "\n".join(
            [
                "# Auditor Report",
                "",
                "```python",
                "print('hola')",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    return run


def test_find_latest_run_returns_latest_folder(report_module, tmp_path: Path):
    axetrules = tmp_path / ".axetrules"
    (axetrules / "output" / "a" / "2026-05-18_09-00").mkdir(parents=True)
    (axetrules / "output" / "a" / "2026-05-19_08-00").mkdir(parents=True)
    (axetrules / "output" / "b" / "2026-05-17_10-00").mkdir(parents=True)

    latest = report_module.find_latest_run(axetrules)

    assert latest.name == "2026-05-17_10-00"
    assert latest.parent.name == "b"


def test_regenerate_index_lists_non_excluded_markdown(report_module, run_dir: Path):
    summary = run_dir / "00_summary"
    summary.mkdir(parents=True, exist_ok=True)
    (summary / "CONSOLIDATED_REPORT.md").write_text("x", encoding="utf-8")
    (summary / "README.md").write_text("ok", encoding="utf-8")

    index = report_module.regenerate_index(run_dir)
    content = index.read_text(encoding="utf-8")

    assert "scout.md" in content
    assert "analyst.md" in content
    assert "auditor.md" in content
    assert "README.md" in content
    assert "CONSOLIDATED_REPORT.md" not in content


def test_consolidate_produces_expected_sections(report_module, run_dir: Path):
    metadata = {}
    markdown, sections = report_module.consolidate(run_dir, metadata=metadata)

    assert len(sections) == 3
    assert "# Scout — Descubrimiento de Repositorios" in markdown
    assert "# Analyst — Stack y Calidad" in markdown
    assert "# Auditor — Seguridad" in markdown
    assert metadata["skipped_files"] == []


def test_heading_depth_is_clamped_to_level_four(report_module, run_dir: Path):
    markdown, _ = report_module.consolidate(run_dir)

    assert "### A" in markdown
    assert "#### B" in markdown
    assert "#### C" in markdown
    assert "#### D" in markdown
    assert "#####" not in markdown


def test_md_to_docx_generates_readable_document(report_module, run_dir: Path, tmp_path: Path):
    docx = pytest.importorskip("docx")

    markdown, _ = report_module.consolidate(run_dir)
    output = tmp_path / "report.docx"

    report_module.md_to_docx(markdown, output, "proyecto-demo")

    parsed = docx.Document(str(output))
    assert len(parsed.paragraphs) > 0
    assert len(parsed.tables) == 1


def test_md_to_docx_writes_golden_fixture(report_module, run_dir: Path):
    pytest.importorskip("docx")

    markdown, _ = report_module.consolidate(run_dir)
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    report_module.md_to_docx(markdown, GOLDEN_DOCX, "proyecto-demo")

    assert GOLDEN_DOCX.exists()


def test_generate_returns_extended_contract(report_module, run_dir: Path, tmp_path: Path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setenv("AGENCIA_DOWNLOADS_DIR", str(downloads))

    result = report_module.generate(run_dir=run_dir)

    expected_keys = {
        "status",
        "sections_included",
        "sections",
        "markdown",
        "docx",
        "index",
        "markdown_path",
        "docx_path",
        "index_path",
        "downloads",
        "skipped_files",
        "uncatalogued_phases",
    }
    assert expected_keys.issubset(result.keys())
    assert result["status"] == "SUCCESS"
    assert result["sections_included"] == 3
    assert result["downloads"]["status"] == "ok"
    assert Path(result["markdown_path"]).name == "CONSOLIDATED_REPORT.md"
    assert Path(result["docx_path"]).name == "INFORME_TRANSICION_PROYECTO-DEMO.docx"


def test_invalid_utf8_file_marks_partial_without_abort(report_module, run_dir: Path, tmp_path: Path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setenv("AGENCIA_DOWNLOADS_DIR", str(downloads))

    bad_file = run_dir / "02_analyst" / "broken.md"
    bad_file.write_bytes(b"\x80\x81")

    result = report_module.generate(run_dir=run_dir)

    assert result["status"] == "PARTIAL"
    assert any("02_analyst" in p for p in result["skipped_files"])
    assert Path(result["docx_path"]).exists()

    consolidated = Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "Archivo no procesable" in consolidated


def test_uncatalogued_phase_is_included_in_markdown_and_index(report_module, run_dir: Path, tmp_path: Path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setenv("AGENCIA_DOWNLOADS_DIR", str(downloads))

    extra = run_dir / "99_nuevo-agente"
    extra.mkdir(parents=True, exist_ok=True)
    (extra / "output.md").write_text("# Extra\n\ncontenido", encoding="utf-8")

    result = report_module.generate(run_dir=run_dir)

    consolidated = Path(result["markdown_path"]).read_text(encoding="utf-8")
    index = Path(result["index_path"]).read_text(encoding="utf-8")

    assert "99 Nuevo Agente" in consolidated
    assert "99_nuevo-agente" in index
    assert "99_nuevo-agente" in result["uncatalogued_phases"]


def test_pipe_block_without_separator_remains_paragraph(report_module, tmp_path: Path):
    docx = pytest.importorskip("docx")

    md = "\n".join(
        [
            "# Titulo",
            "",
            "| A | B |",
            "| C | D |",
            "| E | F |",
        ]
    )
    out = tmp_path / "pipes.docx"

    report_module.md_to_docx(md, out, "demo")

    parsed = docx.Document(str(out))
    assert len(parsed.tables) == 0
    assert any("| A | B |" in p.text for p in parsed.paragraphs)


def test_docx_only_warns_when_markdown_is_stale(report_module, run_dir: Path, tmp_path: Path, monkeypatch, capsys):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setenv("AGENCIA_DOWNLOADS_DIR", str(downloads))

    report_module.generate(run_dir=run_dir, md_only=True)

    source = run_dir / "01_scout" / "scout.md"
    source.write_text(source.read_text(encoding="utf-8") + "\nactualizacion", encoding="utf-8")

    report_module.generate(run_dir=run_dir, docx_only=True)
    captured = capsys.readouterr()

    assert "CONSOLIDATED_REPORT.md es más antiguo" in captured.err


def test_cli_emits_parseable_json_block(report_module, run_dir: Path, tmp_path: Path):
    downloads = tmp_path / "downloads"
    downloads.mkdir()

    env = os.environ.copy()
    env["AGENCIA_DOWNLOADS_DIR"] = str(downloads)

    proc = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--run-dir", str(run_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )

    assert proc.returncode == 0
    assert "---JSON---" in proc.stdout

    blocks = re.findall(r"---JSON---\n(.*?)\n---JSON---", proc.stdout, flags=re.S)
    assert blocks, "No se encontró bloque JSON"

    payload = json.loads(blocks[-1])
    assert payload["status"] in {"SUCCESS", "PARTIAL"}
    assert "sections_included" in payload


def test_cli_importerror_shows_diagnostic_and_exit_1(run_dir: Path, tmp_path: Path):
    fake_site = tmp_path / "fake_site"
    fake_site.mkdir()
    (fake_site / "docx.py").write_text(
        "raise ImportError('simulated missing python-docx')\n",
        encoding="utf-8",
    )

    summary = run_dir / "00_summary"
    summary.mkdir(parents=True, exist_ok=True)
    (summary / "CONSOLIDATED_REPORT.md").write_text("# x", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(fake_site)
    env["AGENCIA_DOWNLOADS_DIR"] = str(tmp_path / "downloads")

    proc = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--run-dir", str(run_dir), "--docx-only"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )

    assert proc.returncode == 1
    assert "pip install python-docx --break-system-packages" in proc.stderr


def test_inline_guard_handles_very_long_line(report_module):
    class DummyParagraph:
        def __init__(self):
            self.runs = []

        def add_run(self, value):
            self.runs.append(value)
            return type("Run", (), {"font": type("Font", (), {})()})()

    para = DummyParagraph()
    text = "*" * 50000 + "fin"

    report_module._apply_inline(para, text)

    assert len(para.runs) == 1
    assert para.runs[0].endswith("fin")
