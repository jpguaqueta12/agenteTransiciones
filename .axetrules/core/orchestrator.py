import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .local_analyzer_compat import LocalAnalyzerCompat
from .drivers.lock_manager import LockManager
from .drivers.repo_logger import get_logger
from .drivers.env_loader import load_credentials, get_clone_url

class AgencyOrchestrator:
    """
    Cerebro central de la Agencia. 
    Coordina la ejecución de motores y la persistencia de estado en memory/.
    """
    
    def __init__(self, memory_path: str = ".axetrules/memory/agency_state.json"):
        self.memory_path = Path(memory_path)
        self.logger = get_logger("agency-orchestrator")
        self.state = self._load_state()
        # Cargar credenciales desde credentials/.env
        try:
            self.creds = load_credentials()
        except (FileNotFoundError, ValueError) as e:
            self.logger.warning(f"⚠️  Credenciales no disponibles: {e}")
            self.creds = {}
        
    def _load_state(self) -> Dict[str, Any]:
        if self.memory_path.exists():
            try:
                with open(self.memory_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "active_project": None,
            "phases_completed": [],
            "results": {}
        }

    def save_state(self):
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.memory_path, "w") as f:
            json.dump(self.state, f, indent=4)

    def run_phase(self, phase_name: str, analyzer: Optional[LocalAnalyzerCompat] = None):
        """Ejecuta una fase específica delegando a los motores correspondientes."""
        self.logger.info(f"🚀 Iniciando fase: {phase_name}")
        
        try:
            if phase_name == "diagnose":
                if not analyzer: raise ValueError("Se requiere un analyzer para el diagnóstico")
                self.state["results"]["stack"] = analyzer.detect_stack().__dict__
                self.state["results"]["quality"] = analyzer.analyze_quality().__dict__
                self.state["phases_completed"].append("diagnose")
                
            elif phase_name == "architect":
                if not analyzer: raise ValueError("Se requiere un analyzer para arquitectura")
                report = analyzer.analyze_architecture()
                # Serialización básica para JSON
                self.state["results"]["architecture"] = {
                    "deployment": report.deployment_style.__dict__,
                    "primary_pattern": report.primary_pattern.__dict__,
                    "mermaid": report.mermaid_diagram
                }
                self.state["phases_completed"].append("architect")
                
            elif phase_name == "audit":
                if not analyzer: raise ValueError("Se requiere un analyzer para auditoría")
                secrets = [s.__dict__ for s in analyzer.scan_secrets()]
                self.state["results"]["audit"] = {"secrets": secrets}
                self.state["phases_completed"].append("audit")
                
            self.save_state()
            self.logger.success(f"✅ Fase {phase_name} completada")
            
        except Exception as e:
            self.logger.error(f"❌ Error en fase {phase_name}: {str(e)}")
            raise

    def get_summary(self) -> str:
        """Genera un resumen ejecutivo del estado actual."""
        completed = ", ".join(self.state["phases_completed"])
        return f"Agencia Status: Proyectos activos: {self.state['active_project']}. Fases completadas: {completed}"
