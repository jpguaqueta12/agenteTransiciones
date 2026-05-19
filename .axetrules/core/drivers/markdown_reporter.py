#!/usr/bin/env python3
"""
Generador de reportes en formato Markdown para análisis de repositorios.
Crea documentos estructurados con los resultados de cada tipo de análisis.

Todos los archivos se escriben via OutputWriter en:
  .axetrules/output/<proyecto>/<run_id>/
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# OutputWriter centralizado — importación lazy para evitar ciclos
_output_writer_cls = None

def _get_writer_cls():
    global _output_writer_cls
    if _output_writer_cls is None:
        try:
            from output_writer import OutputWriter
        except ImportError:
            from core.drivers.output_writer import OutputWriter
        _output_writer_cls = OutputWriter
    return _output_writer_cls


class MarkdownReporter:
    """Genera reportes markdown estructurados para análisis de repositorios."""
    
    def __init__(self, project_name: str, run_id: Optional[str] = None):
        self.project_name = project_name
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Inicializar OutputWriter centralizado
        WriterCls = _get_writer_cls()
        self._writer = WriterCls(project_name=project_name, run_id=run_id)
        
        # Mantener compatibilidad con código que usa analysis_dir directamente
        self.analysis_dir = self._writer.get_run_dir()
    
    def _sanitize_filename(self, name: str) -> str:
        """Convierte nombre de proyecto en nombre de archivo seguro."""
        return name.replace(" ", "-").replace("/", "-").replace("\\", "-").lower()
    
    def _create_header(self, title: str, analysis_type: str, project_url: str = None) -> str:
        """Genera encabezado estándar para reportes."""
        header = f"""# {title}

**Proyecto:** {self.project_name}  
**Tipo de Análisis:** {analysis_type}  
**Fecha:** {self.timestamp}  
"""
        if project_url:
            header += f"**URL:** {project_url}  \n"
        
        header += "\n---\n\n"
        return header

    def _write(self, phase: str, filename: str, content: str) -> str:
        """Escribe via OutputWriter y retorna la ruta como string."""
        path = self._writer.write(phase, filename, content)
        return str(path)
    
    def generate_activity_report(self, commit_data: dict, pr_data: dict) -> str:
        """Genera reporte de actividad homologado con analyze_activity.py."""
        filename = "activity_report.md"

        content = f"# 📊 ACTIVIDAD DEL EQUIPO — {self.project_name}\n\n"
        content += f"**Fecha del análisis:** {self.timestamp}\n\n"
        content += "---\n\n"

        # Commits
        content += "## 📝 Commits (últimos 90 días)\n\n"
        total_commits = commit_data.get("total", 0)
        content += f"- **Total:** {total_commits}\n"

        if total_commits > 0:
            avg_per_day = total_commits / 90
            content += f"- **Promedio:** {avg_per_day:.1f}/día\n\n"

            by_author = commit_data.get("by_author", {})
            content += "### 👥 Contribuidores\n\n"
            content += f"- **Total activos:** {len(by_author)}\n"

            # Bus factor
            bus_factor = 0
            if by_author:
                total = sum(by_author.values())
                cumulative = 0
                for _, commits in sorted(by_author.items(), key=lambda x: x[1], reverse=True):
                    cumulative += commits
                    bus_factor += 1
                    if cumulative >= total * 0.5:
                        break

            content += f"- **Bus Factor:** {bus_factor}"
            if bus_factor <= 2 and bus_factor > 0:
                content += " ⚠️ RIESGO ALTO"
            content += "\n\n"

            if by_author:
                content += "| Contribuidor | Commits | % Total |\n"
                content += "|--------------|---------|----------|\n"
                for author, count in sorted(by_author.items(), key=lambda x: x[1], reverse=True)[:10]:
                    pct = (count / total_commits) * 100
                    content += f"| {author} | {count} | {pct:.1f}% |\n"
                content += "\n"

        # Pull Requests
        content += "## 🔀 Pull Requests\n\n"
        content += f"- **Abiertos:** {pr_data.get('open', 0)}\n"
        content += f"- **Mergeados (período):** {pr_data.get('merged', 0)}\n"
        content += f"- **Tiempo promedio de merge:** {pr_data.get('avg_merge_hours', 0):.1f}h\n"

        stale = pr_data.get("stale", 0)
        content += f"- **PRs sin actividad >14 días:** {stale}"
        if stale > 0:
            content += " ⚠️"
        content += "\n\n"

        # Alertas
        content += "## ⚠️ Alertas\n\n"
        alerts = []

        if bus_factor <= 2 and bus_factor > 0:
            alerts.append("🔴 **Bus Factor crítico** - Alta dependencia de pocas personas")

        if pr_data.get("avg_merge_hours", 0) > 72:
            alerts.append("🟡 **Tiempo de merge elevado** - Posible cuello de botella en reviews")

        if stale > 0:
            alerts.append(f"🟡 **PRs obsoletos** - {stale} PRs sin actividad >14 días")

        if alerts:
            for alert in alerts:
                content += f"- {alert}\n"
        else:
            content += "✅ No se detectaron alertas críticas\n"

        content += "\n---\n\n"
        content += "*Generado por repo-intel activity-reporter*\n"

        return self._write("analyst", filename, content)

    def generate_architecture_report(self, result, project_url: str = None) -> str:
        """Genera reporte de análisis de arquitectura."""
        filename = f"{self._sanitize_filename(self.project_name)}_arquitectura.md"
        
        content = self._create_header(
            f"Reporte de Arquitectura - {self.project_name}",
            "Arquitectura de Software",
            project_url
        )
        
        # Resumen Ejecutivo
        content += "## 📊 Resumen Ejecutivo\n\n"
        content += f"- **Estilo de Despliegue:** {result.deployment_style.name} (Confianza: {result.deployment_style.confidence})\n"
        content += f"- **Patrón Arquitectónico Principal:** {result.primary_pattern.name} (Score: {result.primary_pattern.score}/100)\n"
        
        if result.services:
            content += f"- **Tipo de Repositorio:** Monorepo ({len(result.services)} servicios detectados)\n"
        else:
            content += "- **Tipo de Repositorio:** Single-Service\n"
        
        if result.layer_violations:
            content += f"- **⚠️ Violaciones Detectadas:** {len(result.layer_violations)}\n"
        
        content += "\n---\n\n"
        
        # Patrón Principal
        content += "## 🏗️ Patrón Arquitectónico Principal\n\n"
        content += f"### {result.primary_pattern.name}\n\n"
        content += f"**Confianza:** {result.primary_pattern.confidence}  \n"
        content += f"**Score:** {result.primary_pattern.score}/100\n\n"
        
        if result.primary_pattern.evidence:
            content += "**Evidencia Detectada:**\n\n"
            for ev in result.primary_pattern.evidence:
                content += f"- {ev}\n"
            content += "\n"
        
        # Patrones Secundarios
        if result.secondary_patterns:
            content += "## 🔸 Patrones Secundarios\n\n"
            for pattern in result.secondary_patterns:
                content += f"### {pattern.name}\n\n"
                content += f"- **Score:** {pattern.score}/100\n"
                content += f"- **Confianza:** {pattern.confidence}\n"
                if pattern.evidence:
                    content += "- **Evidencia:**\n"
                    for ev in pattern.evidence[:3]:
                        content += f"  - {ev}\n"
                content += "\n"
        
        # Patrones de Diseño
        if result.design_patterns:
            content += "## 🎨 Patrones de Diseño Detectados\n\n"
            content += "| Patrón | Implementaciones |\n"
            content += "|--------|------------------|\n"
            for pattern, files in result.design_patterns.items():
                content += f"| {pattern} | {len(files)} |\n"
            content += "\n"
            
            content += "**Detalle de Implementaciones:**\n\n"
            for pattern, files in result.design_patterns.items():
                content += f"### {pattern}\n\n"
                for file in files[:5]:  # Máximo 5 archivos por patrón
                    content += f"- `{file}`\n"
                if len(files) > 5:
                    content += f"- *...y {len(files) - 5} más*\n"
                content += "\n"
        
        # Servicios (Monorepo)
        if result.services:
            content += f"## 🔧 Servicios Detectados ({len(result.services)})\n\n"
            content += "| Servicio | Lenguaje Principal | Framework | LOC |\n"
            content += "|----------|-------------------|-----------|-----|\n"
            for svc in result.services:
                content += f"| {svc.name} | {svc.primary_language} | {svc.frameworks[0] if svc.frameworks else 'N/A'} | {svc.loc:,} |\n"
            content += "\n"
        
        # Comunicación Externa
        if result.external_comms:
            content += "## 🌐 Comunicación Externa\n\n"
            content += "| Protocolo/Tecnología | Archivos Detectados |\n"
            content += "|----------------------|--------------------|\n"
            for protocol, files in result.external_comms.items():
                content += f"| {protocol} | {len(files)} |\n"
            content += "\n"
        
        # Violaciones
        if result.layer_violations:
            content += "## ⚠️ Violaciones de Arquitectura\n\n"
            content += f"**Total:** {len(result.layer_violations)} violación(es) detectada(s)\n\n"
            for i, violation in enumerate(result.layer_violations, 1):
                content += f"{i}. {violation}\n"
            content += "\n"
        
        # Diagrama Mermaid
        content += "## 📐 Diagrama de Arquitectura\n\n"
        content += "```mermaid\n"
        content += result.mermaid_diagram
        content += "\n```\n\n"
        
        # Footer
        content += "---\n\n"
        content += f"*Reporte generado automáticamente por RepoIntel Suite v2.0*  \n"
        content += f"*Fecha de generación: {self.timestamp}*\n"
        
        return self._write("architect", filename, content)
    
    def generate_volumetry_report(self, result, project_url: str = None) -> str:
        """Genera reporte de análisis de volumetría."""
        filename = f"{self._sanitize_filename(self.project_name)}_volumetria.md"
        
        content = self._create_header(
            f"Reporte de Volumetría - {self.project_name}",
            "Análisis de Volumetría",
            project_url
        )
        
        # Resumen Ejecutivo
        content += "## 📊 Resumen Ejecutivo\n\n"
        content += f"- **Total de Líneas:** {result['total_lines']:,}\n"
        content += f"- **Total de Archivos:** {result['total_files']:,}\n"
        content += f"- **Lenguajes Detectados:** {len(result['by_language'])}\n"
        content += f"- **Tamaño Total:** {result['total_size_mb']:.2f} MB\n"
        content += "\n---\n\n"
        
        # Distribución por Lenguaje
        content += "## 💻 Distribución por Lenguaje\n\n"
        content += "| Lenguaje | LOC | Archivos | % del Total |\n"
        content += "|----------|-----|----------|-------------|\n"
        
        sorted_langs = sorted(
            result['by_language'].items(),
            key=lambda x: x[1]['lines'],
            reverse=True
        )
        
        for lang, data in sorted_langs:
            percentage = (data['lines'] / result['total_lines']) * 100
            content += f"| {lang} | {data['lines']:,} | {data['files']} | {percentage:.1f}% |\n"
        content += "\n"
        
        # Archivos Más Grandes
        if result.get('largest_files'):
            content += "## 📦 Archivos Más Grandes\n\n"
            content += "| Archivo | Líneas | Tamaño |\n"
            content += "|---------|--------|--------|\n"
            for file_info in result['largest_files'][:10]:
                content += f"| `{file_info['path']}` | {file_info['lines']:,} | {file_info['size_kb']:.1f} KB |\n"
            content += "\n"
        
        # Métricas de Complejidad
        if result.get('complexity_metrics'):
            content += "## 🔍 Métricas de Complejidad\n\n"
            metrics = result['complexity_metrics']
            content += f"- **Promedio de líneas por archivo:** {metrics['avg_lines_per_file']:.0f}\n"
            content += f"- **Archivos grandes (>500 LOC):** {metrics['large_files_count']}\n"
            content += f"- **Archivos muy grandes (>1000 LOC):** {metrics['very_large_files_count']}\n"
            content += "\n"
        
        # Footer
        content += "---\n\n"
        content += f"*Reporte generado automáticamente por RepoIntel Suite v2.0*  \n"
        content += f"*Fecha de generación: {self.timestamp}*\n"
        
        return self._write("analyst", filename, content)
    
    def generate_branches_report(self, branches_data: list, project_url: str = None) -> str:
        """Genera reporte de análisis de ramas."""
        filename = f"{self._sanitize_filename(self.project_name)}_ramas.md"
        
        content = self._create_header(
            f"Reporte de Ramas - {self.project_name}",
            "Análisis de Ramas",
            project_url
        )
        
        active_branches = [b for b in branches_data if b.get('is_active', True)]
        stale_branches = [b for b in branches_data if not b.get('is_active', True)]
        
        # Resumen Ejecutivo
        content += "## 📊 Resumen Ejecutivo\n\n"
        content += f"- **Total de Ramas:** {len(branches_data)}\n"
        content += f"- **Ramas Activas:** {len(active_branches)}\n"
        content += f"- **Ramas Inactivas:** {len(stale_branches)}\n"
        content += "\n---\n\n"
        
        # Ramas Activas
        if active_branches:
            content += "## ✅ Ramas Activas\n\n"
            content += "| Rama | Último Commit | Autor | Días desde Último Commit |\n"
            content += "|------|---------------|-------|-------------------------|\n"
            for branch in active_branches[:20]:  # Máximo 20
                content += f"| `{branch['name']}` | {branch.get('last_commit_date', 'N/A')} | {branch.get('author', 'N/A')} | {branch.get('days_since_commit', 'N/A')} |\n"
            content += "\n"
        
        # Ramas Inactivas
        if stale_branches:
            content += "## ⚠️ Ramas Inactivas (Candidatas para Limpieza)\n\n"
            content += "| Rama | Último Commit | Días Inactiva |\n"
            content += "|------|---------------|---------------|\n"
            for branch in stale_branches[:20]:  # Máximo 20
                content += f"| `{branch['name']}` | {branch.get('last_commit_date', 'N/A')} | {branch.get('days_since_commit', 'N/A')} |\n"
            content += "\n"
            
            content += "### 💡 Sugerencias de Limpieza\n\n"
            content += f"- Total de ramas inactivas: **{len(stale_branches)}**\n"
            content += "- Considerar eliminar ramas con más de 90 días de inactividad\n"
            content += "- Verificar si hay ramas ya mergeadas a main/master\n"
            content += "\n"
        
        # Footer
        content += "---\n\n"
        content += f"*Reporte generado automáticamente por RepoIntel Suite v2.0*  \n"
        content += f"*Fecha de generación: {self.timestamp}*\n"
        
        return self._write("scout", filename, content)
    
    def generate_quality_report(self, quality, stack, project_url: str = None) -> str:
        """Genera reporte de análisis de calidad."""
        filename = f"{self._sanitize_filename(self.project_name)}_calidad.md"
        
        content = self._create_header(
            f"Reporte de Calidad - {self.project_name}",
            "Análisis de Calidad y Mejores Prácticas",
            project_url
        )
        
        # Score y Calificación
        content += "## 📊 Score de Calidad\n\n"
        content += f"### Score General: **{quality.overall_score}/100**\n\n"
        
        grade_map = {
            "A": ("🟢", "Excelente", 90),
            "B": ("🟡", "Bueno", 80),
            "C": ("🟠", "Aceptable", 60),
            "D": ("🔴", "Necesita Mejoras", 40),
            "F": ("⚫", "Crítico", 0)
        }
        
        grade = "A" if quality.overall_score >= 90 else \
                "B" if quality.overall_score >= 80 else \
                "C" if quality.overall_score >= 60 else \
                "D" if quality.overall_score >= 40 else "F"
        
        emoji, description, _ = grade_map[grade]
        content += f"**Calificación:** {emoji} **{grade}** - {description}\n\n"
        content += "---\n\n"
        
        # Documentación
        content += "## 📝 Documentación\n\n"
        content += "| Elemento | Estado | Score |\n"
        content += "|----------|--------|-------|\n"
        content += f"| README.md | {'✅ Presente' if quality.has_readme else '❌ Ausente'} | {quality.readme_score if quality.has_readme else 0}/100 |\n"
        content += f"| LICENSE | {'✅ Presente' if quality.has_license else '❌ Ausente'} | - |\n"
        content += f"| CHANGELOG | {'✅ Presente' if quality.has_changelog else '❌ Ausente'} | - |\n"
        content += f"| .gitignore | {'✅ Presente' if quality.has_gitignore else '❌ Ausente'} | - |\n"
        content += f"| .env.example | {'✅ Presente' if quality.has_env_example else '❌ Ausente'} | - |\n"
        content += "\n"
        
        if quality.has_readme and quality.readme_score < 70:
            content += "### 💡 Mejoras Sugeridas para README\n\n"
            content += "- Agregar ejemplos de uso\n"
            content += "- Incluir instrucciones de instalación detalladas\n"
            content += "- Documentar requisitos previos\n"
            content += "- Agregar badges de estado\n\n"
        
        # Testing
        content += "## 🧪 Testing\n\n"
        if quality.has_tests:
            content += f"**Estado:** ✅ Tests detectados\n\n"
            content += f"**Ratio de Tests:** {int(quality.test_ratio * 100)}%\n\n"
            if stack.test_framework != "Desconocido":
                content += f"**Framework de Testing:** {stack.test_framework}\n\n"
            
            if quality.test_ratio < 0.3:
                content += "### ⚠️ Cobertura Baja\n\n"
                content += f"La cobertura actual ({int(quality.test_ratio * 100)}%) está por debajo del recomendado (30%).\n\n"
                content += "**Recomendaciones:**\n"
                content += "- Aumentar cobertura gradualmente\n"
                content += "- Priorizar componentes críticos\n"
                content += "- Implementar tests de integración\n\n"
        else:
            content += "**Estado:** ❌ No se detectaron tests\n\n"
            content += "### 🚨 Acción Requerida\n\n"
            content += "El proyecto no tiene tests automatizados. Esto es crítico para:\n"
            content += "- Prevenir regresiones\n"
            content += "- Facilitar refactorings\n"
            content += "- Documentar comportamiento esperado\n"
            content += "- Aumentar confianza en deployments\n\n"
        
        # Infraestructura
        content += "## 🔧 Infraestructura y DevOps\n\n"
        content += "| Componente | Estado |\n"
        content += "|------------|--------|\n"
        content += f"| CI/CD Pipeline | {'✅ Configurado' if quality.has_ci_cd else '❌ No configurado'} |\n"
        content += f"| Dockerfile | {'✅ Presente' if quality.has_dockerfile else '❌ Ausente'} |\n"
        content += f"| Herramienta de Linting | {'✅ Configurada' if quality.has_linting else '❌ No configurada'} |\n"
        content += "\n"
        
        # Stack Tecnológico
        content += "## 🏗️ Stack Tecnológico\n\n"
        content += f"**Lenguaje Principal:** {stack.primary_language}\n\n"
        content += f"**Tipo de Proyecto:** {stack.project_type}\n\n"
        
        if stack.frameworks:
            content += "**Frameworks:**\n"
            for fw in stack.frameworks[:5]:
                content += f"- {fw}\n"
            content += "\n"
        
        if stack.databases:
            content += "**Bases de Datos:**\n"
            for db in stack.databases:
                content += f"- {db}\n"
            content += "\n"
        
        if stack.infrastructure:
            content += "**Infraestructura:**\n"
            for infra in stack.infrastructure[:5]:
                content += f"- {infra}\n"
            content += "\n"
        
        # Recomendaciones Priorizadas
        content += "## 📈 Recomendaciones Priorizadas\n\n"
        
        recommendations = []
        
        # Alta prioridad
        if not quality.has_tests:
            recommendations.append(("🔴 ALTA", "Implementar tests automatizados", "Crítico para calidad del código"))
        elif quality.test_ratio < 0.3:
            recommendations.append(("🟠 MEDIA", f"Aumentar cobertura de tests a 30%+", f"Actual: {int(quality.test_ratio*100)}%"))
        
        if not quality.has_ci_cd:
            recommendations.append(("🔴 ALTA", "Configurar pipeline CI/CD", "Automatizar testing y deployment"))
        
        if not quality.has_readme:
            recommendations.append(("🔴 ALTA", "Crear README.md", "Documentación esencial del proyecto"))
        elif quality.readme_score < 70:
            recommendations.append(("🟠 MEDIA", "Mejorar README", f"Score actual: {quality.readme_score}/100"))
        
        # Media prioridad
        if not quality.has_linting:
            recommendations.append(("🟠 MEDIA", "Configurar herramienta de linting", "Mantener consistencia en el código"))
        
        if not quality.has_gitignore:
            recommendations.append(("🟠 MEDIA", "Agregar .gitignore apropiado", "Evitar commits de archivos innecesarios"))
        
        if not quality.has_dockerfile:
            recommendations.append(("🟡 BAJA", "Crear Dockerfile", "Facilitar deployment y desarrollo"))
        
        # Baja prioridad
        if not quality.has_license:
            recommendations.append(("🟡 BAJA", "Agregar archivo LICENSE", "Clarificar términos de uso"))
        
        if not quality.has_changelog:
            recommendations.append(("🟡 BAJA", "Mantener CHANGELOG.md", "Documentar cambios entre versiones"))
        
        if not quality.has_env_example:
            recommendations.append(("🟡 BAJA", "Crear .env.example", "Documentar variables de entorno"))
        
        if recommendations:
            content += "| Prioridad | Recomendación | Justificación |\n"
            content += "|-----------|---------------|---------------|\n"
            for priority, rec, justif in recommendations:
                content += f"| {priority} | {rec} | {justif} |\n"
            content += "\n"
        else:
            content += "✨ **¡Excelente!** El proyecto sigue las mejores prácticas.\n\n"
            content += "No se detectaron áreas críticas de mejora.\n\n"
        
        # Plan de Acción
        if recommendations:
            content += "## 🎯 Plan de Acción Sugerido\n\n"
            content += "### Semana 1-2 (Prioridad Alta)\n\n"
            high_priority = [r for r in recommendations if "ALTA" in r[0]]
            if high_priority:
                for i, (_, rec, _) in enumerate(high_priority, 1):
                    content += f"{i}. {rec}\n"
                content += "\n"
            
            content += "### Semana 3-4 (Prioridad Media)\n\n"
            medium_priority = [r for r in recommendations if "MEDIA" in r[0]]
            if medium_priority:
                for i, (_, rec, _) in enumerate(medium_priority, 1):
                    content += f"{i}. {rec}\n"
                content += "\n"
            
            content += "### Backlog (Prioridad Baja)\n\n"
            low_priority = [r for r in recommendations if "BAJA" in r[0]]
            if low_priority:
                for i, (_, rec, _) in enumerate(low_priority, 1):
                    content += f"{i}. {rec}\n"
                content += "\n"
        
        # Footer
        content += "---\n\n"
        content += f"*Reporte generado automáticamente por RepoIntel Suite v2.0*  \n"
        content += f"*Fecha de generación: {self.timestamp}*\n"
        
        return self._write("analyst", filename, content)
    
    def generate_combined_report(self, analyses: dict, project_url: str = None) -> str:
        """Genera reporte combinado con múltiples análisis."""
        filename = f"{self._sanitize_filename(self.project_name)}_completo.md"
        
        content = f"""# Reporte Completo de Análisis

**Proyecto:** {self.project_name}  
**Fecha:** {self.timestamp}  
"""
        if project_url:
            content += f"**URL:** {project_url}  \n"
        
        content += "\n---\n\n"
        
        content += "## 📋 Tabla de Contenidos\n\n"
        
        # Generar TOC basado en análisis disponibles
        if 'architecture' in analyses:
            content += "1. [Análisis de Arquitectura](#arquitectura)\n"
        if 'volumetry' in analyses:
            content += "2. [Análisis de Volumetría](#volumetría)\n"
        if 'branches' in analyses:
            content += "3. [Análisis de Ramas](#ramas)\n"
        if 'security' in analyses:
            content += "4. [Análisis de Seguridad](#seguridad)\n"
        
        content += "\n---\n\n"
        
        # Incluir cada análisis
        if 'architecture' in analyses:
            content += "## 🏗️ Arquitectura\n\n"
            content += "Ver detalles en: [Reporte de Arquitectura](./)\n\n"
        
        if 'volumetry' in analyses:
            content += "## 📊 Volumetría\n\n"
            content += "Ver detalles en: [Reporte de Volumetría](./)\n\n"
        
        if 'branches' in analyses:
            content += "## 🌿 Ramas\n\n"
            content += "Ver detalles en: [Reporte de Ramas](./)\n\n"
        
        # Footer
        content += "---\n\n"
        content += f"*Reporte generado automáticamente por RepoIntel Suite v2.0*  \n"
        content += f"*Fecha de generación: {self.timestamp}*\n"
        
        return self._write("summary", filename, content)
