#!/usr/bin/env python3
"""
Validador de prerequisitos para RepoIntel
Verifica que todas las dependencias necesarias estén instaladas.

Uso: python check_prerequisites.py
"""
import subprocess
import sys
import os

def check_command(cmd):
    """Verifica si un comando está disponible en el sistema."""
    try:
        result = subprocess.run(
            [cmd, '--version'],
            capture_output=True,
            check=True,
            text=True
        )
        return True, result.stdout.split('\n')[0]
    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
        return False, None

def check_python_package(package_name, import_name=None):
    """Verifica si un paquete Python está instalado."""
    if import_name is None:
        import_name = package_name.replace('-', '_')
    
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def main():
    """Ejecuta todas las validaciones de prerequisitos."""
    print("\n" + "="*60)
    print("🔍 VALIDACIÓN DE PREREQUISITOS - RepoIntel")
    print("="*60 + "\n")
    
    all_ok = True
    
    # 1. Verificar comandos del sistema
    print("📋 Verificando comandos del sistema...\n")
    
    system_commands = {
        'git': 'Git - Control de versiones',
        'python': 'Python - Intérprete',
    }
    
    for cmd, description in system_commands.items():
        is_installed, version = check_command(cmd)
        if is_installed:
            print(f"✅ {description}")
            print(f"   Versión: {version}")
        else:
            print(f"❌ {description} - NO ENCONTRADO")
            all_ok = False
            
            if cmd == 'git':
                print("   Instalar: https://git-scm.com/downloads")
            elif cmd == 'python':
                print("   Instalar: https://www.python.org/downloads/")
        print()
    
    # 2. Verificar paquetes Python
    print("📦 Verificando paquetes Python...\n")
    
    python_packages = {
        'httpx': 'httpx',
        'pydantic': 'pydantic',
    }
    
    missing_packages = []
    
    for package, import_name in python_packages.items():
        if check_python_package(package, import_name):
            print(f"✅ {package}")
        else:
            print(f"❌ {package} - NO INSTALADO")
            missing_packages.append(package)
            all_ok = False
        print()
    
    # 3. Verificar permisos de escritura
    print("🔐 Verificando permisos de escritura...\n")
    
    test_file = ".prerequisite_test_file"
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("✅ Permisos de escritura en directorio actual")
    except (PermissionError, OSError) as e:
        print(f"❌ Sin permisos de escritura: {e}")
        all_ok = False
    
    print()
    
    # Resumen final
    print("="*60)
    
    if all_ok:
        print("✅ TODOS LOS PREREQUISITOS ESTÁN INSTALADOS")
        print("="*60 + "\n")
        print("🚀 RepoIntel está listo para usar\n")
        return 0
    else:
        print("❌ FALTAN PREREQUISITOS")
        print("="*60 + "\n")
        
        if missing_packages:
            print("📦 Para instalar paquetes Python faltantes:")
            print(f"   pip install {' '.join(missing_packages)}")
            print()
        
        print("⚠️  Instala los prerequisitos faltantes antes de continuar\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
