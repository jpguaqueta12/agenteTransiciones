#!/usr/bin/env python3
"""
Análisis de Ramas — RepoIntel
Ejecuta el análisis de ramas para el proyecto seleccionado.

Uso: python analyze_branches.py <token> [base_url]
"""
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from platform_client import PlatformClient, RepoContext
except ImportError as e:
    print(f"❌ Error importando dependencias: {e}")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "pydantic", "--quiet"])
    from platform_client import PlatformClient, RepoContext

# Validar argumentos
if len(sys.argv) < 2:
    print("\n❌ Error: Token requerido")
    print("Uso: python analyze_branches.py <token> [base_url]")
    print("\nEjemplo:")
    print("  python analyze_branches.py glpat-xxxxxxxxxxxx https://gitlab.com\n")
    sys.exit(1)

TOKEN = sys.argv[1]
BASE_URL = sys.argv[2] if len(sys.argv) > 2 else None

# Leer datos del proyecto desde archivo
try:
    with open(".repo_intel_projects.txt") as f:
        line = f.readline().strip()
        parts = line.split("|")
        PROJECT_ID = parts[1]
        PROJECT_NAME = parts[2]
        PROJECT_URL = parts[3]
        
        # Si no se proporcionó BASE_URL, extraerla de PROJECT_URL
        if not BASE_URL:
            from urllib.parse import urlparse
            parsed = urlparse(PROJECT_URL)
            BASE_URL = f"{parsed.scheme}://{parsed.netloc}"
except FileNotFoundError:
    print("\n❌ Error: Archivo .repo_intel_projects.txt no encontrado")
    print("Ejecuta primero el discovery de proyectos.\n")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error leyendo proyecto: {e}\n")
    sys.exit(1)

def days_since(date_str: str) -> int:
    """Calcula días desde una fecha ISO 8601."""
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        delta = datetime.now(date.tzinfo) - date
        return delta.days
    except:
        return 999

def classify_branch(days: int, has_pr: bool) -> tuple[str, str]:
    """Clasifica una rama según antigüedad y estado de PR."""
    if days <= 7:
        return "🟢 ACTIVA", "green"
    elif has_pr:
        return "🟡 EN REVISIÓN", "yellow"
    elif days <= 30:
        return "🟡 RECIENTE", "yellow"
    elif days <= 90:
        return "🟠 INACTIVA", "orange"
    else:
        return "🔴 ABANDONADA", "red"

def health_score(days: int, commits_behind: int = 0) -> int:
    """Calcula health score de una rama."""
    score = 100
    if days > 90:    score -= 40
    elif days > 30:  score -= 20
    elif days > 7:   score -= 5
    if commits_behind > 100: score -= 30
    elif commits_behind > 50: score -= 15
    elif commits_behind > 10: score -= 5
    return max(0, score)

def analyze_branches():
    """Ejecuta el análisis de ramas."""
    print("\n🌿 ANÁLISIS DE RAMAS — Agente Sanitizador Sonar")
    print("━" * 80)
    
    # Crear contexto
    platform = PlatformClient.detect_platform(BASE_URL)
    context = RepoContext(
        platform=platform,
        base_url=BASE_URL,
        token=TOKEN,
        project_id=PROJECT_ID,
        project_name=PROJECT_NAME,
        project_url=PROJECT_URL,
        default_branch="main"
    )
    
    try:
        with PlatformClient(context) as client:
            print("\n📡 Conectando a GitLab...\n")
            
            # Obtener ramas
            branches = client.get_branches()
            
            if not branches:
                print("⚠️  No se encontraron ramas en el repositorio.\n")
                return
            
            # Clasificar ramas
            classified = {
                "green": [], "yellow": [], "orange": [], "red": [], "protected": []
            }
            
            for branch in branches:
                days = days_since(branch.last_commit_date)
                status, color = classify_branch(days, False)
                
                if branch.is_protected:
                    classified["protected"].append((branch, days, status))
                else:
                    classified[color].append((branch, days, status))
            
            # Resumen
            total = len(branches)
            active = len(classified["green"])
            review = len([b for b in branches if "EN REVISIÓN" in classify_branch(days_since(b.last_commit_date), False)[0]])
            inactive = len(classified["orange"])
            abandoned = len(classified["red"])
            
            print(f"  Total: {total}  │  🟢 Activas: {active}  │  🟡 En review: {review}")
            print(f"              │  🟠 Inactivas: {inactive}  │  🔴 Abandonadas: {abandoned}\n")
            
            # Tabla de ramas
            print(f"{'RAMA':<35} {'ESTADO':<18} {'ÚLTIMO COMMIT':<15} {'AUTOR':<20} {'HEALTH':>7}")
            print("─" * 100)
            
            # Mostrar ramas protegidas primero
            for branch, days, status in classified["protected"]:
                author = branch.last_commit_author[:18] if branch.last_commit_author else "-"
                age = f"hace {days}d" if days > 0 else "hoy"
                score = health_score(days)
                
                print(f"{branch.name:<35} {'🔵 PROTEGIDA':<18} {age:<15} {author:<20} {score:>7}")
            
            # Mostrar ramas por estado
            for color in ["green", "yellow", "orange", "red"]:
                for branch, days, status in sorted(classified[color], key=lambda x: x[1]):
                    author = branch.last_commit_author[:18] if branch.last_commit_author else "-"
                    age = f"hace {days}d" if days > 0 else "hoy"
                    score = health_score(days)
                    
                    print(f"{branch.name:<35} {status:<18} {age:<15} {author:<20} {score:>7}")
            
            print("─" * 100)
            
            # Alertas
            if abandoned > 0:
                print(f"\n⚠️  ALERTAS")
                print(f"  • {abandoned} rama(s) llevan >90 días sin actividad — considerar eliminar")
            
            # Estadísticas adicionales
            print(f"\n📊 ESTADÍSTICAS")
            print(f"  • Rama más antigua: {max(days_since(b.last_commit_date) for b in branches)} días")
            print(f"  • Rama más reciente: {min(days_since(b.last_commit_date) for b in branches)} días")
            print(f"  • Promedio de antigüedad: {sum(days_since(b.last_commit_date) for b in branches) // len(branches)} días")
            
            print("\n✅ Análisis completado\n")

            # ─────────────────────────────────────────────
            # Generar reporte Markdown (homologado a analyze_activity)
            # ─────────────────────────────────────────────
            try:
                from pathlib import Path

                analysis_dir = Path(f"Analisis {PROJECT_NAME}")
                analysis_dir.mkdir(exist_ok=True)

                report_file = analysis_dir / "branches_report.md"

                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(f"# 🌿 ANÁLISIS DE RAMAS — {PROJECT_NAME}\n\n")
                    f.write(f"**Fecha del análisis:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")

                    # Resumen
                    f.write("## 📊 Resumen Ejecutivo\n\n")
                    f.write(f"- **Total de ramas:** {total}\n")
                    f.write(f"- **Activas:** {active}\n")
                    f.write(f"- **En revisión:** {review}\n")
                    f.write(f"- **Inactivas:** {inactive}\n")
                    f.write(f"- **Abandonadas:** {abandoned}\n\n")

                    # Detalle de ramas
                    f.write("## 📋 Detalle de Ramas\n\n")
                    f.write("| Rama | Estado | Último Commit | Autor | Health |\n")
                    f.write("|------|--------|--------------|--------|--------|\n")

                    for branch in branches:
                        days = days_since(branch.last_commit_date)
                        status, _ = classify_branch(days, False)
                        author = branch.last_commit_author or "-"
                        age = f"hace {days}d" if days > 0 else "hoy"
                        score = health_score(days)

                        f.write(
                            f"| `{branch.name}` | {status} | {age} | {author} | {score} |\n"
                        )

                    # Estadísticas
                    f.write("\n## 📈 Estadísticas\n\n")
                    f.write(f"- **Rama más antigua:** {max(days_since(b.last_commit_date) for b in branches)} días\n")
                    f.write(f"- **Rama más reciente:** {min(days_since(b.last_commit_date) for b in branches)} días\n")
                    f.write(f"- **Promedio de antigüedad:** {sum(days_since(b.last_commit_date) for b in branches) // len(branches)} días\n\n")

                    # Alertas
                    f.write("## ⚠️ Alertas\n\n")
                    if abandoned > 0:
                        f.write(f"- 🔴 {abandoned} rama(s) llevan >90 días sin actividad — considerar eliminar\n")
                    else:
                        f.write("✅ No se detectaron ramas abandonadas\n")

                    f.write("\n---\n\n")
                    f.write("*Generado por repo-intel branch-analyzer*\n")

                print(f"📄 Reporte Markdown generado: {report_file}\n")

            except Exception as e:
                print(f"⚠️  No se pudo generar el reporte Markdown: {e}\n")

    except PermissionError as e:
        print(f"❌ Error de permisos: {e}")
        print("\nVerifica que tu token tenga los siguientes scopes:")
        print("  • read_api")
        print("  • read_repository\n")
    
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_branches()
