#!/usr/bin/env python3
"""
Ejecución de análisis de dependencias (Dependency Graph + CVEs via OSV)
"""

import os
import sys
from local_analyzer import LocalAnalyzer
from osv_client import OSVClient, detect_and_parse_manifest, format_summary_report
from markdown_reporter import MarkdownReporter

def main():
    # Leer proyecto seleccionado
    with open(".repo_intel_projects.txt", "r", encoding="utf-8") as f:
        line = f.readline().strip()
        parts = line.split("|")
        project_id = parts[1]
        project_name = parts[2]
        project_url = parts[3]

    clone_path = ".tmp/" + project_name.replace(" ", "-").replace("/", "-")

    if not os.path.exists(clone_path):
        print("❌ El repositorio no está clonado en .tmp/")
        sys.exit(1)

    print(f"\n📦 Proyecto: {project_name}")
    print("🔍 Analizando dependencias...\n")

    analyzer = LocalAnalyzer(clone_path)
    manifests = analyzer.find_manifest_files()

    all_deps = []
    for filename, content in manifests:
        deps = detect_and_parse_manifest(filename, content)
        all_deps.extend(deps)

    print(f"📦 Dependencias detectadas: {len(all_deps)}")

    summary = None
    if all_deps:
        with OSVClient() as osv:
            summary = osv.scan_dependencies(all_deps)
            print(format_summary_report(summary))
    else:
        print("⚠️ No se detectaron manifiestos compatibles.")

    # Generar reporte Markdown homologado
    reporter = MarkdownReporter(project_name)
    report_path = reporter.generate_combined_report(
        {"dependencies": True},
        project_url
    )

    print(f"\n📄 Reporte generado en: {report_path}")
    print("✅ Análisis de dependencias completado")

if __name__ == "__main__":
    main()
