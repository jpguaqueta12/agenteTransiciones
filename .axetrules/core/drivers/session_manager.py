#!/usr/bin/env python3
"""
session_manager.py — Agencia de Transición
Gestiona el ciclo de vida de sesiones.

Cada vez que la agencia arranca una nueva sesión:
  1. Archiva el estado anterior en output/<proyecto>/<run_id>/session_archive/
  2. Limpia memory/ para empezar desde cero
  3. Crea un nuevo session_id

Esto garantiza que la agencia SIEMPRE pregunte al usuario qué quiere
hacer, sin asumir que el proyecto anterior sigue siendo el objetivo.

Uso:
    from core.drivers.session_manager import SessionManager
    sm = SessionManager()
    sm.new_session()          # limpia y archiva
    sm.is_fresh()             # True si no hay sesión activa
    sm.get_session_id()       # ID de la sesión actual
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def _find_axetrules() -> Path:
    current = Path.cwd()
    for p in [current, *current.parents]:
        if (p / ".axetrules").exists():
            return p / ".axetrules"
    script = Path(__file__).resolve().parent
    for p in [script, *script.parents]:
        if p.name == ".axetrules":
            return p
        if (p / ".axetrules").exists():
            return p / ".axetrules"
    raise FileNotFoundError("No se encontró .axetrules")


# Estado vacío que se escribe al limpiar
_EMPTY_STATE = {
    "session_id":        None,
    "session_started":   None,
    "active_project":    None,
    "active_projects":   [],        # ← soporte multi-repo
    "selected_branch":   None,      # ← rama seleccionada por el usuario
    "phases_completed":  [],
    "results":           {},
    "detected_platform": None,
    "last_scout_report": None,
    "last_run_id":       None,
}


class SessionManager:
    def __init__(self, axetrules: Optional[Path] = None):
        self.axetrules  = axetrules or _find_axetrules()
        self.memory_dir = self.axetrules / "memory"
        self.output_dir = self.axetrules / "output"
        self.state_path = self.memory_dir / "agency_state.json"
        self.projects_path = self.memory_dir / ".repo_intel_projects.txt"
        self.session_path  = self.memory_dir / ".current_session"

    # ── API pública ───────────────────────────────────────────────────────────

    def new_session(self) -> str:
        """
        Inicia una sesión nueva:
        - Archiva el estado anterior si existe
        - Limpia memory/agency_state.json y .repo_intel_projects.txt
        - Genera un nuevo session_id
        Retorna el session_id.
        """
        session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Archivar estado anterior si tiene datos reales
        self._archive_previous(session_id)

        # Limpiar estado
        self._reset_state(session_id)

        # Limpiar lista de proyectos
        self.projects_path.write_text("", encoding="utf-8")

        # Guardar session_id activo
        self.session_path.write_text(session_id, encoding="utf-8")

        return session_id

    def is_fresh(self) -> bool:
        """True si no hay sesión activa o el estado está vacío."""
        if not self.state_path.exists():
            return True
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            return state.get("active_project") is None and not state.get("active_projects")
        except Exception:
            return True

    def get_session_id(self) -> Optional[str]:
        """Retorna el session_id activo, o None si no hay sesión."""
        if self.session_path.exists():
            return self.session_path.read_text(encoding="utf-8").strip() or None
        return None

    def get_state(self) -> dict:
        """Lee el estado actual."""
        if not self.state_path.exists():
            return dict(_EMPTY_STATE)
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return dict(_EMPTY_STATE)

    def save_state(self, state: dict) -> None:
        """Persiste el estado."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

    def add_project(self, project: dict) -> None:
        """
        Agrega un proyecto a la lista activa (soporte multi-repo).
        project = {"id": ..., "name": ..., "url": ..., "index": ...}
        """
        state = self.get_state()

        # active_project = el más reciente (compatibilidad)
        state["active_project"] = project

        # active_projects = lista completa de la sesión
        projects = state.get("active_projects", [])
        ids = [p.get("id") for p in projects]
        if project.get("id") not in ids:
            projects.append(project)
        state["active_projects"] = projects

        self.save_state(state)

        # Actualizar .repo_intel_projects.txt (append si multi-repo)
        existing = self.projects_path.read_text(encoding="utf-8") if self.projects_path.exists() else ""
        line = f"{project.get('index','1')}|{project['id']}|{project['name']}|{project['url']}\n"
        if line not in existing:
            with open(self.projects_path, "a", encoding="utf-8") as f:
                f.write(line)

    def list_session_projects(self) -> list[dict]:
        """Lista todos los proyectos analizados en la sesión actual."""
        state = self.get_state()
        return state.get("active_projects", [])

    def reset_project(self) -> None:
        """
        Limpia solo el proyecto activo (para cambiar de repo sin nueva sesión).
        Mantiene el historial de active_projects.
        """
        state = self.get_state()
        state["active_project"]   = None
        state["phases_completed"] = []
        state["results"]          = {}
        self.save_state(state)
        self.projects_path.write_text("", encoding="utf-8")

    def list_past_sessions(self) -> list[dict]:
        """Lista sesiones anteriores desde output/."""
        sessions = []
        if not self.output_dir.exists():
            return sessions
        for project_dir in sorted(self.output_dir.iterdir()):
            if not project_dir.is_dir():
                continue
            for run_dir in sorted(project_dir.iterdir(), reverse=True):
                manifest = run_dir / "manifest.json"
                if manifest.exists():
                    try:
                        data = json.loads(manifest.read_text(encoding="utf-8"))
                        sessions.append({
                            "project": data.get("project", project_dir.name),
                            "run_id":  data.get("run_id", run_dir.name),
                            "started": data.get("started_at", ""),
                            "files":   len(data.get("files", [])),
                            "path":    str(run_dir),
                        })
                    except Exception:
                        pass
        return sessions

    # ── Internos ──────────────────────────────────────────────────────────────

    def _archive_previous(self, new_session_id: str) -> None:
        """Mueve el estado anterior al output del último run si tenía datos."""
        if not self.state_path.exists():
            return
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return

        # Solo archivar si había un proyecto activo
        project = state.get("active_project")
        run_id  = state.get("last_run_id")
        if not project or not run_id:
            return

        safe_name = project["name"].replace(" ", "-").replace("/", "-").lower()
        archive_dir = self.output_dir / safe_name / run_id / "session_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Copiar state y projects al archivo
        shutil.copy2(self.state_path, archive_dir / "agency_state.json")
        if self.projects_path.exists():
            shutil.copy2(self.projects_path, archive_dir / ".repo_intel_projects.txt")

    def _reset_state(self, session_id: str) -> None:
        """Escribe el estado vacío con el nuevo session_id."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        state = dict(_EMPTY_STATE)
        state["session_id"]      = session_id
        state["session_started"] = datetime.now().isoformat()
        self.save_state(state)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    sm = SessionManager()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "new":
        sid = sm.new_session()
        print(f"✅ Nueva sesión iniciada: {sid}")
        print(f"   Estado limpiado en: {sm.state_path}")

    elif cmd == "status":
        sid = sm.get_session_id()
        fresh = sm.is_fresh()
        state = sm.get_state()
        print(f"\n{'='*50}")
        print(f"  Estado de la Agencia")
        print(f"{'='*50}")
        print(f"  Session ID  : {sid or 'ninguna'}")
        print(f"  Estado      : {'🟢 Fresca (sin proyecto)' if fresh else '🟡 Con datos previos'}")
        project = state.get("active_project")
        if project:
            print(f"  Proyecto    : {project.get('name', '—')}")
        projects = state.get("active_projects", [])
        if projects:
            print(f"  Proyectos en sesión: {len(projects)}")
            for p in projects:
                print(f"    • {p.get('name', '—')}")
        phases = state.get("phases_completed", [])
        if phases:
            print(f"  Fases hechas: {', '.join(phases)}")
        print()

    elif cmd == "history":
        sessions = sm.list_past_sessions()
        if not sessions:
            print("No hay sesiones anteriores.")
        else:
            print(f"\n{'='*60}")
            print(f"  Historial de Sesiones ({len(sessions)} runs)")
            print(f"{'='*60}")
            for s in sessions[:10]:
                print(f"  [{s['run_id']}] {s['project']} — {s['files']} archivos")
            print()

    elif cmd == "reset":
        sm.reset_project()
        print("✅ Proyecto activo limpiado. La agencia preguntará de nuevo.")

    else:
        print(f"Comandos: new | status | history | reset")
