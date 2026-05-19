#!/usr/bin/env python3
"""
Activity Reporter - Analiza actividad del equipo en un repositorio
Parte de la suite repo-intel
"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.platform_client import PlatformClient, RepoContext


def parse_project_file():
    """Lee el archivo .repo_intel_projects.txt y extrae información del proyecto"""
    project_file = Path('.repo_intel_projects.txt')
    
    if not project_file.exists():
        print("❌ Error: .repo_intel_projects.txt no encontrado")
        print("   Ejecuta primero la fase de discovery")
        sys.exit(1)
    
    line = project_file.read_text().strip()
    if not line or '|' not in line:
        print("❌ Error: Formato inválido en .repo_intel_projects.txt")
        sys.exit(1)
    
    parts = line.split('|')
    if len(parts) < 4:
        print("❌ Error: Datos incompletos en .repo_intel_projects.txt")
        sys.exit(1)
    
    # Format: index|project_id|project_name|project_url
    project_id = parts[1]
    project_name = parts[2]
    project_url = parts[3]
    
    # Extraer base_url de project_url preservando /git si existe
    # Ejemplo esperado:
    # https://umane.emeal.nttdata.com/git/COITDEV/... → base_url = https://umane.emeal.nttdata.com/git
    from urllib.parse import urlparse
    parsed = urlparse(project_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    if "/git/" in project_url:
        base_url = f"{base_url}/git"
    
    return {
        'project_id': project_id,
        'project_name': project_name,
        'project_url': project_url,
        'base_url': base_url
    }


def group_by(items, key_func):
    """Agrupa items por una función de clave"""
    groups = defaultdict(list)
    for item in items:
        groups[key_func(item)].append(item)
    return dict(groups)


def analyze_commits(client, days=90):
    """Analiza commits de los últimos N días"""
    print(f"\n📊 Analizando commits (últimos {days} días)...")
    
    since = (datetime.now() - timedelta(days=days)).isoformat()
    commits = client.get_commits(since=since)
    
    if not commits:
        print("   ⚠️  No se encontraron commits en el período")
        return {}
    
    print(f"   ✅ {len(commits)} commits encontrados")
    
    # Agrupar por autor
    by_author = defaultdict(int)
    for commit in commits:
        by_author[commit.author_name] += 1
    
    # Agrupar por día de la semana
    by_weekday = defaultdict(int)
    for commit in commits:
        try:
            commit_date = datetime.fromisoformat(commit.authored_at.replace('Z', '+00:00'))
            by_weekday[commit_date.weekday()] += 1
        except:
            pass
    
    return {
        'total': len(commits),
        'by_author': dict(by_author),
        'by_weekday': dict(by_weekday),
        'commits': commits
    }


def analyze_pull_requests(client):
    """Analiza pull requests"""
    print("\n📋 Analizando pull requests...")
    
    open_prs = client.get_pull_requests('open')
    merged_prs = client.get_pull_requests('merged')
    
    print(f"   ✅ PRs abiertos: {len(open_prs)}")
    print(f"   ✅ PRs mergeados: {len(merged_prs)}")
    
    # Calcular tiempo promedio de merge
    merge_times = []
    for pr in merged_prs:
        try:
            created = datetime.fromisoformat(pr.created_at.replace('Z', '+00:00'))
            updated = datetime.fromisoformat(pr.updated_at.replace('Z', '+00:00'))
            hours = (updated - created).total_seconds() / 3600
            merge_times.append(hours)
        except:
            pass
    
    avg_merge_hours = sum(merge_times) / len(merge_times) if merge_times else 0
    
    # PRs sin actividad > 14 días
    stale_prs = []
    for pr in open_prs:
        try:
            updated = datetime.fromisoformat(pr.updated_at.replace('Z', '+00:00'))
            days_inactive = (datetime.now(updated.tzinfo) - updated).days
            if days_inactive > 14:
                stale_prs.append(pr)
        except:
            pass
    
    return {
        'open': len(open_prs),
        'merged': len(merged_prs),
        'avg_merge_hours': avg_merge_hours,
        'stale': len(stale_prs)
    }


def calculate_bus_factor(commits_by_author):
    """Calcula el bus factor del equipo"""
    if not commits_by_author:
        return 0
    
    total = sum(commits_by_author.values())
    sorted_authors = sorted(commits_by_author.items(), key=lambda x: x[1], reverse=True)
    
    cumulative = 0
    count = 0
    for author, commits in sorted_authors:
        cumulative += commits
        count += 1
        if cumulative >= total * 0.5:
            return count
    
    return count


def generate_report(project_info, commit_data, pr_data):
    """Genera reporte de actividad en formato Markdown"""
    
    # Crear directorio de análisis
    analysis_dir = Path(f"Analisis {project_info['project_name']}")
    analysis_dir.mkdir(exist_ok=True)
    
    report_file = analysis_dir / "activity_report.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 📊 ACTIVIDAD DEL EQUIPO — {project_info['project_name']}\n\n")
        f.write(f"**Fecha del análisis:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        # Commits
        f.write("## 📝 Commits (últimos 90 días)\n\n")
        f.write(f"- **Total:** {commit_data.get('total', 0)}\n")
        
        if commit_data.get('total', 0) > 0:
            avg_per_day = commit_data['total'] / 90
            f.write(f"- **Promedio:** {avg_per_day:.1f}/día\n\n")
            
            # Contribuidores
            f.write("### 👥 Contribuidores\n\n")
            by_author = commit_data.get('by_author', {})
            bus_factor = calculate_bus_factor(by_author)
            
            f.write(f"- **Total activos:** {len(by_author)}\n")
            f.write(f"- **Bus Factor:** {bus_factor}")
            if bus_factor <= 2:
                f.write(" ⚠️ RIESGO ALTO")
            f.write("\n\n")
            
            # Top contribuidores
            if by_author:
                f.write("| Contribuidor | Commits | % Total |\n")
                f.write("|--------------|---------|----------|\n")
                sorted_authors = sorted(by_author.items(), key=lambda x: x[1], reverse=True)
                for author, count in sorted_authors[:10]:
                    pct = (count / commit_data['total']) * 100
                    f.write(f"| {author} | {count} | {pct:.1f}% |\n")
                f.write("\n")
        
        # Pull Requests
        f.write("\n## 🔀 Pull Requests\n\n")
        f.write(f"- **Abiertos:** {pr_data.get('open', 0)}\n")
        f.write(f"- **Mergeados (período):** {pr_data.get('merged', 0)}\n")
        f.write(f"- **Tiempo promedio de merge:** {pr_data.get('avg_merge_hours', 0):.1f}h\n")
        
        stale = pr_data.get('stale', 0)
        f.write(f"- **PRs sin actividad >14 días:** {stale}")
        if stale > 0:
            f.write(" ⚠️")
        f.write("\n\n")
        
        # Alertas
        f.write("\n## ⚠️ Alertas\n\n")
        alerts = []
        
        bus_factor = calculate_bus_factor(commit_data.get('by_author', {}))
        if bus_factor <= 2:
            alerts.append("� **Bus Factor crítico** - Alta dependencia de pocas personas")
        
        if pr_data.get('avg_merge_hours', 0) > 72:
            alerts.append("🟡 **Tiempo de merge elevado** - Posible cuello de botella en reviews")
        
        if pr_data.get('stale', 0) > 0:
            alerts.append(f"🟡 **PRs obsoletos** - {pr_data['stale']} PRs sin actividad >14 días")
        
        if alerts:
            for alert in alerts:
                f.write(f"- {alert}\n")
        else:
            f.write("✅ No se detectaron alertas críticas\n")
        
        f.write("\n---\n\n")
        f.write(f"*Generado por repo-intel activity-reporter*\n")
    
    return report_file


def main():
    """Función principal"""
    print("\n� REPO-INTEL: Activity Reporter")
    print("=" * 60)
    
    # Leer información del proyecto
    project_info = parse_project_file()
    print(f"\n📦 Proyecto: {project_info['project_name']}")
    print(f"🔗 URL: {project_info['project_url']}")
    
    # Crear contexto del repositorio
    # Obtener token del environment o usar valor por defecto de prueba
    token = os.environ.get('GITLAB_TOKEN', 'JWKuZgHaceEMjp7p9zYo')
    
    ctx = RepoContext(
        platform='gitlab',
        base_url=project_info['base_url'],
        token=token,
        project_id=project_info['project_id'],
        project_name=project_info['project_name'],
        project_url=project_info['project_url']
    )
    
    # Inicializar cliente
    client = PlatformClient(ctx)
    
    # Análisis de commits
    commit_data = analyze_commits(client, days=90)
    
    # Análisis de PRs
    pr_data = analyze_pull_requests(client)
    
    # Generar reporte
    print("\n📄 Generando reporte...")
    report_file = generate_report(project_info, commit_data, pr_data)
    
    print(f"\n✅ Reporte generado: {report_file}")
    print(f"\n{'=' * 60}")
    print("✨ Análisis completado exitosamente")
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Análisis interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
