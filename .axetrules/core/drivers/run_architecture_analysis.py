#!/usr/bin/env python3
"""
Script especializado para ejecutar el análisis de arquitectura.
Maneja automáticamente: bloqueo, lectura de proyecto, clon y análisis.

Uso: python run_architecture_analysis.py <token>
"""
import os, sys, subprocess, time

# Validar argumentos
if len(sys.argv) < 2:
    print("\n❌ Error: Token requerido")
    print("Uso: python run_architecture_analysis.py <token>")
    print("\nEjemplo:")
    print("  python run_architecture_analysis.py glpat-xxxxxxxxxxxx\n")
    sys.exit(1)

TOKEN = sys.argv[1]
BASE_PATH = os.getcwd().replace("\\.axetrules\\scripts", "").replace("/.axetrules/scripts", "")
SCRIPTS_PATH = os.path.join(BASE_PATH, ".axetrules", "scripts")
os.chdir(SCRIPTS_PATH)

print("\n" + "="*60)
print("🏛️  ANÁLISIS DE ARQUITECTURA")
print("="*60 + "\n")

# PASO 1: Crear bloqueo
lock_path = ".analysis.lock"
with open(lock_path, "w") as f:
    f.write(f"ANALYSIS_IN_PROGRESS|architecture|{time.time()}")
print("🔒 Bloqueo establecido - Análisis iniciado\n")

# PASO 2: Leer proyecto
try:
    with open(".repo_intel_projects.txt") as f:
        line = f.readline().strip()
        parts = line.split("|")
        project_id, project_name, project_url = parts[1], parts[2], parts[3]
    print(f"📦 Proyecto: {project_name}")
    print(f"🆔 ID: {project_id}")
    print(f"🔗 URL: {project_url}\n")
except Exception as e:
    print(f"❌ Error leyendo proyecto: {e}")
    if os.path.exists(lock_path):
        os.remove(lock_path)
    sys.exit(1)

# PASO 3: Preparar ruta de clonado
clone_path = os.path.join(BASE_PATH, ".tmp", project_name.replace(" ", "-").replace("/", "-"))
os.makedirs(os.path.dirname(clone_path), exist_ok=True)

# PASO 4: Clonar si no existe
if not os.path.exists(clone_path):
    print(f"📥 Clonando repositorio...")
    clone_url = project_url.replace("https://", f"https://oauth2:{TOKEN}@")
    
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, clone_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Repositorio clonado exitosamente\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error clonando: {e.stderr}")
        if os.path.exists(lock_path):
            os.remove(lock_path)
        sys.exit(1)
else:
    print(f"✓ Repositorio ya existe: {clone_path}\n")

# PASO 5: Ejecutar análisis
print("🔍 Analizando arquitectura del proyecto...\n")

try:
    sys.path.insert(0, SCRIPTS_PATH)
    from local_analyzer import ArchitectureAnalyzer
    
    analyzer = ArchitectureAnalyzer(clone_path)
    result = analyzer.analyze()
    
    # Mostrar resultados
    print("\n" + "="*60)
    print(f"🏛️  RESULTADOS — {project_name}")
    print("="*60)
    print(f"\n📐 ESTILO DE DESPLIEGUE: {result.deployment_style.name}")
    print(f"   Confianza: {result.deployment_style.confidence}")
    
    print(f"\n🏗️  PATRÓN ARQUITECTÓNICO PRINCIPAL: {result.primary_pattern.name}")
    print(f"   Confianza: {result.primary_pattern.confidence}")
    print(f"   Score: {result.primary_pattern.score}/100")
    
    if result.primary_pattern.evidence:
        print(f"\n   📋 Evidencia detectada:")
        for ev in result.primary_pattern.evidence[:5]:
            print(f"      • {ev}")
    
    if result.secondary_patterns:
        print(f"\n🔸 PATRONES SECUNDARIOS:")
        for pattern in result.secondary_patterns[:2]:
            print(f"   • {pattern.name} (Score: {pattern.score})")
    
    if result.design_patterns:
        print(f"\n🎨 PATRONES DE DISEÑO DETECTADOS:")
        for pattern, files in list(result.design_patterns.items())[:5]:
            print(f"   • {pattern}: {len(files)} implementación(es)")
    
    if result.layer_violations:
        print(f"\n⚠️  VIOLACIONES DE ARQUITECTURA: {len(result.layer_violations)}")
        for violation in result.layer_violations[:3]:
            print(f"   {violation}")
    
    if result.external_comms:
        print(f"\n🌐 COMUNICACIÓN EXTERNA:")
        for protocol, files in result.external_comms.items():
            print(f"   • {protocol}: {len(files)} archivo(s)")
    
    if result.services:
        print(f"\n🔧 SERVICIOS DETECTADOS (Monorepo): {len(result.services)}")
        for svc in result.services[:5]:
            print(f"   • {svc.name} ({svc.primary_language})")
    
    print(f"\n📊 DIAGRAMA DE ARQUITECTURA:")
    print(result.mermaid_diagram)
    
    print("\n" + "="*60)
    print("✅ Análisis completado exitosamente")
    print("="*60 + "\n")
    
    # PASO 7: Generar reporte markdown
    print("📝 Generando reporte markdown...")
    try:
        from markdown_reporter import MarkdownReporter
        
        reporter = MarkdownReporter(project_name)
        report_path = reporter.generate_architecture_report(result, project_url)
        print(f"✅ Reporte generado: {report_path}\n")
    except Exception as e:
        print(f"⚠️  Error generando reporte markdown: {e}")
    
except Exception as e:
    print(f"\n❌ Error durante el análisis: {e}")
    import traceback
    traceback.print_exc()
    if os.path.exists(lock_path):
        os.remove(lock_path)
    sys.exit(1)

# PASO 6: Limpiar bloqueo
if os.path.exists(lock_path):
    os.remove(lock_path)
    print("🔓 Bloqueo removido\n")
