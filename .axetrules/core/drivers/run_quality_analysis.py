#!/usr/bin/env python3
"""
Script especializado para ejecutar el análisis de calidad.
Maneja automáticamente: bloqueo, lectura de proyecto, clon y análisis.

Uso: python run_quality_analysis.py <token>
"""
import os, sys, subprocess, time

# Validar argumentos
if len(sys.argv) < 2:
    print("\n❌ Error: Token requerido")
    print("Uso: python run_quality_analysis.py <token>")
    print("\nEjemplo:")
    print("  python run_quality_analysis.py glpat-xxxxxxxxxxxx\n")
    sys.exit(1)

TOKEN = sys.argv[1]
BASE_PATH = os.getcwd().replace("\\.axetrules\\scripts", "").replace("/.axetrules/scripts", "")
SCRIPTS_PATH = os.path.join(BASE_PATH, ".axetrules", "scripts")
os.chdir(SCRIPTS_PATH)

print("\n" + "="*60)
print("✅ ANÁLISIS DE CALIDAD")
print("="*60 + "\n")

# PASO 1: Crear bloqueo
lock_path = ".analysis.lock"
with open(lock_path, "w") as f:
    f.write(f"ANALYSIS_IN_PROGRESS|quality|{time.time()}")
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
print("🔍 Analizando calidad del proyecto...\n")

try:
    sys.path.insert(0, SCRIPTS_PATH)
    from local_analyzer import LocalAnalyzer
    
    analyzer = LocalAnalyzer(clone_path)
    stack = analyzer.detect_stack()
    quality = analyzer.analyze_quality()
    
    # Mostrar resultados
    print("\n" + "="*60)
    print(f"✅ RESULTADOS — {project_name}")
    print("="*60)
    
    print(f"\n📊 SCORE DE CALIDAD: {quality.overall_score}/100")
    
    grade_colors = {
        "A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⚫"
    }
    grade = "A" if quality.overall_score >= 90 else \
            "B" if quality.overall_score >= 80 else \
            "C" if quality.overall_score >= 60 else \
            "D" if quality.overall_score >= 40 else "F"
    
    print(f"   Calificación: {grade_colors.get(grade, '')} {grade}")
    
    print(f"\n📝 DOCUMENTACIÓN:")
    print(f"   README: {'✅ Presente' if quality.has_readme else '❌ Ausente'}")
    if quality.has_readme:
        print(f"   Score README: {quality.readme_score}/100")
    print(f"   Licencia: {'✅' if quality.has_license else '❌'}")
    print(f"   CHANGELOG: {'✅' if quality.has_changelog else '❌'}")
    print(f"   .gitignore: {'✅' if quality.has_gitignore else '❌'}")
    print(f"   .env.example: {'✅' if quality.has_env_example else '❌'}")
    
    print(f"\n🧪 TESTING:")
    print(f"   Tests: {'✅ Detectados' if quality.has_tests else '❌ No detectados'}")
    if quality.has_tests:
        print(f"   Ratio de tests: {int(quality.test_ratio * 100)}%")
        if stack.test_framework != "Desconocido":
            print(f"   Framework: {stack.test_framework}")
    
    print(f"\n🔧 INFRAESTRUCTURA:")
    print(f"   CI/CD: {'✅ Configurado' if quality.has_ci_cd else '❌ No configurado'}")
    print(f"   Docker: {'✅' if quality.has_dockerfile else '❌'}")
    print(f"   Linting: {'✅' if quality.has_linting else '❌'}")
    
    print(f"\n🏗️  STACK TECNOLÓGICO:")
    print(f"   Lenguaje principal: {stack.primary_language}")
    print(f"   Tipo de proyecto: {stack.project_type}")
    
    if stack.frameworks:
        print(f"   Frameworks: {', '.join(stack.frameworks[:3])}")
    
    if stack.databases:
        print(f"   Bases de datos: {', '.join(stack.databases[:3])}")
    
    if stack.infrastructure:
        print(f"   Infraestructura: {', '.join(stack.infrastructure[:5])}")
    
    print(f"\n📈 RECOMENDACIONES:")
    recommendations = []
    
    if not quality.has_readme:
        recommendations.append("• Agregar README.md con documentación del proyecto")
    elif quality.readme_score < 70:
        recommendations.append("• Mejorar README (agregar ejemplos, instalación, uso)")
    
    if not quality.has_tests:
        recommendations.append("• Implementar tests automatizados")
    elif quality.test_ratio < 0.3:
        recommendations.append(f"• Aumentar cobertura de tests (actual: {int(quality.test_ratio*100)}%)")
    
    if not quality.has_ci_cd:
        recommendations.append("• Configurar pipeline CI/CD")
    
    if not quality.has_linting:
        recommendations.append("• Configurar herramienta de linting")
    
    if not quality.has_license:
        recommendations.append("• Agregar archivo LICENSE")
    
    if not quality.has_gitignore:
        recommendations.append("• Agregar .gitignore apropiado")
    
    if recommendations:
        for rec in recommendations[:5]:
            print(f"   {rec}")
    else:
        print("   ✨ ¡Excelente! Proyecto con buenas prácticas")
    
    print("\n" + "="*60)
    print("✅ Análisis completado exitosamente")
    print("="*60 + "\n")
    
    # PASO 7: Generar reporte markdown
    print("📝 Generando reporte markdown...")
    try:
        from markdown_reporter import MarkdownReporter
        
        reporter = MarkdownReporter(project_name)
        report_path = reporter.generate_quality_report(quality, stack, project_url)
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
