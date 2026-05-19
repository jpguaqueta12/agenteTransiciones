#!/usr/bin/env python3
"""
run_full_pipeline.py — Agencia de Transición
El orquestador (AGENCY.md / Director) es quien pregunta al usuario y construye
los comandos. Este script NUNCA usa input() — recibe todo por argumentos CLI.

Modos:

  # 1. Descubrir todos los repos del usuario/org → JSON para el orquestador
  python .axetrules/core/drivers/run_full_pipeline.py --discover

  # 2. Listar todas las ramas de un repo → JSON para el orquestador
  python .axetrules/core/drivers/run_full_pipeline.py --branches --url <repo_url>

  # 3. Pipeline completo (el orquestador ya preguntó y eligió)
  python .axetrules/core/drivers/run_full_pipeline.py --url <repo_url> --branch <rama>

  # 4. Fase individual
  python .axetrules/core/drivers/run_full_pipeline.py --url <repo_url> --branch <rama> --fase analyst

  # 5. Historial de sesiones anteriores
  python .axetrules/core/drivers/run_full_pipeline.py --history

Las credenciales se leen automáticamente desde credentials/.env
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Resolver paths ────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent          # core/drivers/
_CORE = _HERE.parent                             # core/
_AXETRULES = _CORE.parent                        # .axetrules/
_WORKSPACE = _AXETRULES.parent                   # raíz del workspace

# Permitir imports como paquete (core.*) y mantener compatibilidad con imports locales
sys.path.insert(0, str(_AXETRULES))   # para `import core...`
sys.path.insert(0, str(_WORKSPACE))   # raíz del repo
sys.path.insert(0, str(_HERE))        # para imports legacy en drivers/
sys.path.insert(0, str(_CORE))        # para imports legacy en core/

from env_loader import load_credentials, print_summary
from output_writer import (
    OutputWriter,
    build_stack_report,
    build_architecture_report,
    build_security_report,
    build_roadmap_report,
    build_full_summary,
    build_detection_report,
    build_scout_report,
    build_branches_report,
)
from session_manager import SessionManager
from detect_platform import detect_platform, update_agency_state


# ── Helpers ───────────────────────────────────────────────────────────────────

def _banner(title: str) -> None:
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}\n")


def _fetch_all_projects(creds: dict) -> list:
    """Descubre todos los repos del usuario/org via API. Retorna [] si falla.

    GitHub distingue entre usuarios (/users/) y organizaciones (/orgs/).
    Probamos ambos endpoints y fusionamos resultados para no perder repos.
    GitLab/Azure/Bitbucket usan el endpoint de grupos estándar.
    """
    try:
        sys.path.insert(0, str(_HERE))
        from platform_client import PlatformClient, RepoContext
        from urllib.parse import urlparse

        url      = creds.get("URL", "")
        parsed   = urlparse(url if "://" in url else f"https://{url}")
        parts    = [p for p in parsed.path.strip("/").split("/") if p]
        group    = creds.get("GROUP", "") or (parts[0] if parts else "")
        platform = creds.get("PLATFORM", "github")

        if not group:
            return []

        ctx = RepoContext(
            platform=platform,
            base_url=creds.get("BASE_URL", ""),
            token=creds["TOKEN"],
            project_id="",
            project_name="",
            project_url="",
        )
        with PlatformClient(ctx) as client:
            if platform == "github":
                # GitHub tiene endpoints distintos para usuarios y organizaciones.
                # /users/{name}/repos  → funciona para cuentas personales
                # /orgs/{name}/repos   → funciona para organizaciones (con token)
                # Probamos ambos y fusionamos para no perder ningún repo.
                projects: list = []
                seen_ids: set  = set()
                for endpoint in [
                    f"https://api.github.com/users/{group}/repos",
                    f"https://api.github.com/orgs/{group}/repos",
                ]:
                    try:
                        resp = client._get(
                            endpoint,
                            params={"per_page": 100, "sort": "pushed", "type": "all"},
                        )
                        if isinstance(resp, list):
                            for r in resp:
                                p = client._normalize_project(r)
                                if p.id not in seen_ids:
                                    seen_ids.add(p.id)
                                    projects.append(p)
                    except Exception:
                        pass
                return sorted(projects, key=lambda p: p.last_activity or "", reverse=True)
            else:
                return client.list_projects_in_group(group)
    except Exception:
        return []


def _fetch_branches(project: dict, creds: dict) -> list:
    """Obtiene ramas via API. Retorna lista vacía si falla."""
    try:
        sys.path.insert(0, str(_HERE))
        from platform_client import PlatformClient, RepoContext
        ctx = RepoContext(
            platform=creds.get("PLATFORM", "github"),
            base_url=creds.get("BASE_URL", ""),
            token=creds["TOKEN"],
            project_id=project["id"],
            project_name=project["name"],
            project_url=project["url"],
        )
        with PlatformClient(ctx) as client:
            branches = client.get_branches()
        # Rama por defecto primero, luego alfabético
        return sorted(branches, key=lambda b: (not b.is_default, b.name))
    except Exception:
        return []




def _clone_repo(project: dict, token: str, platform: str, clone_base: str,
                branch: str = "main") -> Path:
    safe_name   = project["name"].replace(" ", "-").replace("/", "-")
    safe_branch = branch.replace("/", "-").replace("\\", "-")
    clone_path  = Path(clone_base) / f"{safe_name}@{safe_branch}"

    if clone_path.exists():
        print(f"  ✓ Repo ya clonado en {clone_path}")
        return clone_path

    print(f"  📥 Clonando {project['name']} — rama: {branch}")
    url = project["url"]

    auth_map = {
        "gitlab":    f"https://oauth2:{token}@",
        "github":    f"https://x-access-token:{token}@",
        "azure":     f"https://anything:{token}@",
        "bitbucket": f"https://x-token-auth:{token}@",
    }
    prefix   = auth_map.get(platform, f"https://oauth2:{token}@")
    auth_url = url.replace("https://", prefix)

    clone_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, auth_url, str(clone_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Error clonando repo:\n{result.stderr}")

    print(f"  ✅ Clonado en {clone_path}")
    return clone_path


def _resolve_project_from_url(url: str, sm: SessionManager) -> dict:
    """Detecta plataforma desde URL y construye el dict de proyecto."""
    info = detect_platform(url)
    try:
        update_agency_state(info)  # solo persiste en memory/, nunca toca credentials/.env
    except Exception:
        pass
    project = {
        "index": str(len(sm.list_session_projects()) + 1),
        "id":    info.project_id,
        "name":  info.project_name or info.project_id.split("/")[-1],
        "url":   info.clone_url,
    }
    sm.add_project(project)
    return project




# ── Fases ─────────────────────────────────────────────────────────────────────

def fase_analyst(analyzer, writer: OutputWriter, project_url: str, sm: SessionManager):
    _banner("📊 FASE 2 — ANALYST: Stack & Calidad")
    stack   = analyzer.detect_stack()
    quality = analyzer.analyze_quality()
    path = build_stack_report(stack, quality, writer, project_url)
    print(f"  ✅ Output: {path}")

    state = sm.get_state()
    state["results"]["stack"] = {
        "primary_language": stack.primary_language,
        "frameworks":       stack.frameworks,
        "databases":        stack.databases,
        "infrastructure":   stack.infrastructure,
        "project_type":     stack.project_type,
        "test_framework":   stack.test_framework,
        "has_tests":        stack.has_tests,
        "test_ratio":       stack.test_ratio,
    }
    state["results"]["quality"] = {
        "overall_score":   quality.overall_score,
        "has_readme":      quality.has_readme,
        "readme_score":    quality.readme_score,
        "has_tests":       quality.has_tests,
        "test_ratio":      quality.test_ratio,
        "has_linting":     quality.has_linting,
        "has_ci_cd":       quality.has_ci_cd,
        "has_dockerfile":  quality.has_dockerfile,
        "has_env_example": quality.has_env_example,
        "has_gitignore":   quality.has_gitignore,
        "has_license":     quality.has_license,
        "has_changelog":   quality.has_changelog,
    }
    if "diagnose" not in state["phases_completed"]:
        state["phases_completed"].append("diagnose")
    sm.save_state(state)
    return stack, quality


def fase_architect(analyzer, writer: OutputWriter, project_url: str, sm: SessionManager):
    _banner("🏛️  FASE 2b — ARCHITECT: Arquitectura")
    report = analyzer.analyze_architecture()
    path = build_architecture_report(report, writer, project_url)
    print(f"  ✅ Output: {path}")

    state = sm.get_state()
    state["results"]["architecture"] = {
        "deployment":      report.deployment_style.name,
        "primary_pattern": report.primary_pattern.name,
        "pattern_score":   report.primary_pattern.score,
        "confidence":      report.primary_pattern.confidence,
        "violations":      len(report.layer_violations),
        "mermaid":         report.mermaid_diagram,
    }
    if "architect" not in state["phases_completed"]:
        state["phases_completed"].append("architect")
    sm.save_state(state)
    return report


def fase_auditor(analyzer, writer: OutputWriter, project_url: str, sm: SessionManager):
    _banner("🔐 FASE 3 — AUDITOR: Seguridad & CVEs")
    secrets = analyzer.scan_secrets()
    cve_summary = None
    try:
        from osv_client import OSVClient, detect_and_parse_manifest
        manifests = analyzer.find_manifest_files() if hasattr(analyzer, "find_manifest_files") else []
        all_deps = []
        for fname, content in manifests:
            all_deps.extend(detect_and_parse_manifest(fname, content))
        if all_deps:
            with OSVClient() as osv:
                cve_summary = osv.scan_dependencies(all_deps)
    except Exception as e:
        print(f"  ⚠️  CVE scan omitido: {e}")

    path = build_security_report(secrets, cve_summary, writer, project_url)
    print(f"  ✅ Output: {path}")

    state = sm.get_state()
    state["results"]["audit"] = {
        "secrets_count": len(secrets),
        "secrets": [{"type": s.secret_type, "file": s.file_path, "line": s.line_number} for s in secrets],
        "verdict": "RIESGO_DETECTADO" if secrets else "APTO",
    }
    if "audit" not in state["phases_completed"]:
        state["phases_completed"].append("audit")
    sm.save_state(state)
    return secrets, cve_summary


def fase_strategist(stack, quality, arch_report, secrets, writer: OutputWriter,
                    project_url: str, sm: SessionManager):
    _banner("🚀 FASE 4 — STRATEGIST: Roadmap de Transición")
    path = build_roadmap_report(stack, quality, arch_report, secrets, writer, project_url)
    print(f"  ✅ Output: {path}")

    # Copia rápida en memory/
    roadmap_content = Path(path).read_text(encoding="utf-8")
    roadmap_memory  = _AXETRULES / "memory" / "TRANSITION_ROADMAP.md"
    roadmap_memory.write_text(roadmap_content, encoding="utf-8")
    print(f"  📋 Copia en memory: {roadmap_memory}")

    state = sm.get_state()
    if "strategy" not in state["phases_completed"]:
        state["phases_completed"].append("strategy")
    sm.save_state(state)


# ── Pipeline para un repo ─────────────────────────────────────────────────────

def run_single(project: dict, creds: dict, sm: SessionManager,
               only_fase: str | None = None, branch: str = "main",
               all_projects: list | None = None,
               all_branches: list | None = None) -> None:
    start = time.time()

    print(f"\n  📦 Proyecto : {project['name']}")
    print(f"  🔗 URL      : {project['url']}")
    print(f"  🌿 Rama     : {branch}")

    # OutputWriter — run_id por proyecto
    run_id = sm.get_session_id() or datetime.now().strftime("%Y-%m-%d_%H-%M")
    writer = OutputWriter(project_name=project["name"], run_id=run_id)
    print(f"  📁 Output   : {writer.get_run_dir()}")

    state = sm.get_state()
    state["last_run_id"]      = run_id
    state["selected_branch"]  = branch
    sm.save_state(state)

    # ── Scout: guardar exploración completa SIEMPRE ───────────────────────────
    # Todos los repos del org y todas las ramas del repo se persisten en output
    # independientemente de cuál se haya seleccionado para análisis.
    _banner("🕵️  Scout — Guardando exploración completa")

    # Si el llamador no pasó las listas, descubrirlas ahora
    if not all_projects:
        print("  🔍 Descubriendo todos los repositorios del org/usuario...")
        all_projects = _fetch_all_projects(creds)
        print(f"  → {len(all_projects)} repositorio(s) encontrado(s)")

    if not all_branches:
        print("  🌿 Obteniendo todas las ramas del repositorio...")
        all_branches = _fetch_branches(project, creds)
        print(f"  → {len(all_branches)} rama(s) encontrada(s)")

    try:
        p_path = build_scout_report(all_projects, writer, selected_name=project["name"])
        print(f"  ✅ Proyectos ({len(all_projects)} en total): {p_path}")
    except Exception as e:
        print(f"  ⚠️  No se pudo guardar lista de proyectos: {e}")
    try:
        b_path = build_branches_report(all_branches, branch, writer)
        print(f"  ✅ Ramas ({len(all_branches)} en total): {b_path}")
    except Exception as e:
        print(f"  ⚠️  No se pudo guardar lista de ramas: {e}")

    # Clonar
    _banner("📥 Clonando repositorio")
    clone_path = _clone_repo(
        project,
        token=creds["TOKEN"],
        platform=creds.get("PLATFORM", "github"),
        clone_base=creds.get("CLONE_BASE_DIR", "/tmp/repo-intel"),
        branch=branch,
    )

    # Analyzer (import como paquete para evitar "attempted relative import")
    from core.local_analyzer_compat import LocalAnalyzerCompat
    analyzer    = LocalAnalyzerCompat(str(clone_path))
    project_url = project["url"]

    stack = quality = arch_report = secrets = None

    if only_fase in (None, "analyst"):
        stack, quality = fase_analyst(analyzer, writer, project_url, sm)

    if only_fase in (None, "architect"):
        arch_report = fase_architect(analyzer, writer, project_url, sm)

    if only_fase in (None, "auditor"):
        secrets, _ = fase_auditor(analyzer, writer, project_url, sm)

    if only_fase in (None, "strategist"):
        if stack is None or quality is None:
            r = sm.get_state().get("results", {})
            if "stack" in r and "quality" in r:
                stack   = type("S", (), r["stack"])()
                quality = type("Q", (), r["quality"])()
            else:
                print("  ⚠️  Ejecuta analyst primero.")
                return
        if arch_report is None:
            arch_report = type("A", (), {
                "primary_pattern": type("P", (), {
                    "name": sm.get_state().get("results", {}).get("architecture", {}).get("primary_pattern", "—")
                })(),
                "layer_violations": [],
            })()
        if secrets is None:
            secrets = []
        fase_strategist(stack, quality, arch_report, secrets, writer, project_url, sm)

    # Índice parcial (solo fases CORE)
    _banner("📋 Generando índice CORE")
    index = writer.finalize(sm.get_state())
    print(f"  ✅ Índice CORE: {index}")

    # Pre-crear todas las carpetas de agentes extendidos
    _banner("📂 Pre-creando carpetas de agentes extendidos")
    extended_phases = [
        "access-readiness", "app-inventory", "dependency-mapping",
        "api-integration", "business-capability", "functional-flow",
        "knowledge-mgmt", "kt-capture", "exit-criteria", "command-control",
    ]
    for phase in extended_phases:
        d = writer.get_phase_dir(phase)
        print(f"  📁 {d}")

    elapsed = time.time() - start
    run_dir = writer.get_run_dir()
    print(f"\n  ✅ Pipeline CORE completado en {elapsed:.1f}s")
    print(f"  📁 Outputs en: {run_dir}\n")
    for f in writer.list_outputs():
        print(f"    • [{f['phase']}] {f['file']}")

    print("\n" + "="*55)
    print("  ⏭️  DIRECTOR: continúa con los pasos 4-13 (agentes")
    print("     extendidos). El pipeline NO ha terminado.")
    print(f"  📂 RUN_DIR = {run_dir}")
    print("="*55 + "\n")


# ── Modos de descubrimiento (salida JSON para el orquestador) ─────────────────

def cmd_discover() -> None:
    """Lista todos los repos del usuario/org como JSON. El orquestador muestra
    la lista al usuario y pregunta cuál analizar."""
    creds    = load_credentials()
    projects = _fetch_all_projects(creds)
    output   = [
        {
            "index":          i,
            "name":           p.name,
            "id":             str(p.id),
            "url":            p.clone_url_https,
            "visibility":     p.visibility,
            "default_branch": p.default_branch,
            "last_activity":  p.last_activity,
        }
        for i, p in enumerate(projects, 1)
    ]
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_list_branches(repo_url: str) -> None:
    """Lista todas las ramas de un repo como JSON. El orquestador muestra
    la lista al usuario y pregunta cuál analizar."""
    creds     = load_credentials()
    repo_info = detect_platform(repo_url)
    eff_creds = {**creds, "PLATFORM": repo_info.platform, "BASE_URL": repo_info.base_url}
    project   = {
        "id":   repo_info.project_id,
        "name": repo_info.project_name or repo_info.project_id.split("/")[-1],
        "url":  repo_info.clone_url,
    }
    branches = _fetch_branches(project, eff_creds)
    output   = [
        {
            "name":                b.name,
            "is_default":          b.is_default,
            "is_protected":        b.is_protected,
            "last_commit_date":    b.last_commit_date,
            "last_commit_author":  b.last_commit_author,
            "last_commit_message": b.last_commit_message,
        }
        for b in branches
    ]
    print(json.dumps(output, indent=2, ensure_ascii=False))


# ── Pipeline principal ────────────────────────────────────────────────────────

def run(url: str, branch: str, fase: str | None = None,
        show_history: bool = False) -> None:
    """Ejecuta el pipeline. El orquestador ya preguntó al usuario y pasó
    --url y --branch como argumentos. No se usa input() en ningún punto."""

    sm = SessionManager()

    if show_history:
        _banner("📚 Historial de Sesiones")
        sessions = sm.list_past_sessions()
        if not sessions:
            print("  No hay sesiones anteriores.\n")
        else:
            for s in sessions[:15]:
                print(f"  [{s['run_id']}] {s['project']} — {s['files']} archivos")
                print(f"    📁 {s['path']}")
            print()
        return

    # Sesión nueva — borrón y cuenta nueva
    session_id = sm.new_session()
    _banner(f"🏢 Agencia de Transición — Sesión {session_id}")

    creds = load_credentials()
    print_summary(creds)

    # Detectar plataforma del repo específico (puede diferir del .env)
    repo_info   = detect_platform(url)
    update_agency_state(repo_info)
    eff_creds   = {**creds, "PLATFORM": repo_info.platform, "BASE_URL": repo_info.base_url}

    project = {
        "index": "1",
        "id":    repo_info.project_id,
        "name":  repo_info.project_name or repo_info.project_id.split("/")[-1],
        "url":   repo_info.clone_url,
        "branch": branch,
    }
    sm.add_project(project)

    state = sm.get_state()
    state["active_project"]   = project
    state["selected_branch"]  = branch
    state["phases_completed"] = []
    state["results"]          = {}
    sm.save_state(state)

    run_single(project, eff_creds, sm, only_fase=fase, branch=branch)

    _banner("📊 Resumen de Sesión")
    print(f"  ✅ {project['name']} — rama: {branch}")
    print(f"\n  Todos los outputs en: {_AXETRULES / 'output'}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    def _arg(flag: str) -> str | None:
        if flag in args:
            idx = args.index(flag)
            return args[idx + 1] if idx + 1 < len(args) else None
        return None

    try:
        if "--history" in args:
            run(url="", branch="", show_history=True)

        elif "--discover" in args:
            cmd_discover()

        elif "--branches" in args:
            repo_url = _arg("--url")
            if not repo_url:
                print("❌ --branches requiere --url <repo_url>")
                sys.exit(1)
            cmd_list_branches(repo_url)

        else:
            repo_url = _arg("--url")
            branch   = _arg("--branch")
            fase     = _arg("--fase")

            if not repo_url:
                print(
                    "\n❌ El orquestador debe pasar --url y --branch.\n"
                    "\nModos disponibles:\n"
                    "  --discover                       Lista todos los repos (JSON)\n"
                    "  --branches --url <url>           Lista todas las ramas (JSON)\n"
                    "  --url <url> --branch <rama>      Pipeline completo\n"
                    "  --url <url> --branch <rama> --fase <analyst|architect|auditor|strategist>\n"
                    "  --history                        Historial de sesiones\n"
                )
                sys.exit(1)
            if not branch:
                print("❌ Falta --branch <nombre_de_rama>")
                print("   Usa --branches --url <url> para ver las ramas disponibles.")
                sys.exit(1)

            run(url=repo_url, branch=branch, fase=fase)

    except FileNotFoundError as e:
        print(f"\n❌ {e}\n")
        sys.exit(1)
    except ValueError as e:
        print(f"\n⚠️  {e}\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n  Interrumpido.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
