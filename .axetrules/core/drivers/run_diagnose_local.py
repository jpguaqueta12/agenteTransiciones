#!/usr/bin/env python3
"""
run_diagnose_local.py — Fase Diagnose (stack + quality) para el proyecto activo.

- Lee .axetrules/memory/agency_state.json (active_project)
- Clona a /tmp/repo-intel/<project_name> (depth=1)
- Ejecuta LocalAnalyzerCompat + AgencyOrchestrator.run_phase("diagnose")
- Persiste resultados en .axetrules/memory/agency_state.json
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

# Bootstrap imports: permitir ejecutar desde la raíz del repo sin instalar paquete.
import sys

ROOT = Path(__file__).resolve().parents[3]  # repo root
AXE_DIR = ROOT / ".axetrules"
CORE_DIR = AXE_DIR / "core"

for p in (AXE_DIR, CORE_DIR):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from core.drivers.env_loader import load_credentials
from core.local_analyzer_compat import LocalAnalyzerCompat
from core.orchestrator import AgencyOrchestrator


def main() -> int:
    orch = AgencyOrchestrator()
    ap = orch.state.get("active_project") or {}
    name = ap.get("name") or orch.creds.get("PROJECT_NAME") or "repo"
    clone_url = ap.get("url") or orch.creds.get("PROJECT_URL")

    if not clone_url:
        raise ValueError("No hay PROJECT_URL ni active_project.url. Ejecuta discovery + selección primero.")

    # Credenciales
    creds = orch.creds or load_credentials()
    token = creds.get("TOKEN", "")
    if not token:
        raise ValueError("TOKEN vacío en .axetrules/credentials/.env")

    # Clonado
    clone_dir = Path(f"/tmp/repo-intel/{name}")
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    clone_dir.parent.mkdir(parents=True, exist_ok=True)

    # GitHub: x-access-token
    url_with_token = clone_url.replace("https://", f"https://x-access-token:{token}@")

    subprocess.run(
        ["git", "clone", "--depth", "1", url_with_token, str(clone_dir)],
        check=True,
    )

    analyzer = LocalAnalyzerCompat(str(clone_dir))
    orch.run_phase("diagnose", analyzer=analyzer)

    # Salida resumida
    stack = orch.state.get("results", {}).get("stack", {})
    quality = orch.state.get("results", {}).get("quality", {})
    print("✅ Fase diagnose completada")
    print("Stack:", json.dumps(stack, indent=2, ensure_ascii=False))
    print("Quality:", json.dumps(quality, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
