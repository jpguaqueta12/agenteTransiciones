#!/usr/bin/env python3
"""
Wrapper simplificado para ejecutar comandos adaptados al shell del usuario.
Lee el tipo de shell desde .shell_env y adapta la sintaxis automáticamente.

Uso: python run_cmd.py "comando1 && comando2 && comando3"

Este script elimina la necesidad de código inline complejo
repitiendo la lógica de adaptación de shell en múltiples lugares.
"""
import sys
import subprocess
import os

def get_shell_type():
    """Lee el tipo de shell desde .shell_env."""
    shell_env_file = ".shell_env"
    
    if not os.path.exists(shell_env_file):
        print(f"⚠️  Advertencia: {shell_env_file} no encontrado")
        print("   Ejecuta primero el script de detección de shell")
        return "bash"  # Default fallback
    
    try:
        with open(shell_env_file, 'r') as f:
            return f.read().strip()
    except IOError as e:
        print(f"❌ Error leyendo {shell_env_file}: {e}")
        return "bash"

def adapt_command_for_shell(cmd, shell_type):
    """
    Adapta sintaxis de comando según el shell.
    
    Args:
        cmd: Comando original (con sintaxis Bash/Unix)
        shell_type: Tipo de shell (powershell, cmd, bash)
    
    Returns:
        Comando adaptado para el shell objetivo
    """
    if shell_type == "powershell":
        # PowerShell: && se convierte en ;
        cmd = cmd.replace(' && ', '; ')
        # Manejo de cd: en PowerShell funciona igual
        return cmd
    
    elif shell_type == "cmd":
        # CMD: && se convierte en &
        cmd = cmd.replace(' && ', ' & ')
        return cmd
    
    else:  # bash, sh, zsh
        # Sin cambios para shells Unix
        return cmd

def run_command(cmd, verbose=False):
    """
    Ejecuta un comando adaptado al shell del usuario.
    
    Args:
        cmd: Comando a ejecutar
        verbose: Si True, muestra información de debug
    
    Returns:
        Código de salida del comando
    """
    shell_type = get_shell_type()
    adapted_cmd = adapt_command_for_shell(cmd, shell_type)
    
    if verbose:
        print(f"\n🐚 Shell detectado: {shell_type}")
        print(f"📝 Comando original: {cmd}")
        print(f"📝 Comando adaptado: {adapted_cmd}\n")
    
    try:
        result = subprocess.run(
            adapted_cmd,
            shell=True,
            text=True
        )
        return result.returncode
    
    except Exception as e:
        print(f"❌ Error ejecutando comando: {e}")
        return 1

def main():
    """CLI para ejecutar comandos adaptados."""
    if len(sys.argv) < 2:
        print("Uso: python run_cmd.py \"comando1 && comando2\"")
        print()
        print("Ejemplo:")
        print("  python run_cmd.py \"cd scripts && python discover_projects.py\"")
        print()
        print("Opciones:")
        print("  --verbose    Muestra información de debug")
        sys.exit(1)
    
    verbose = "--verbose" in sys.argv
    
    # Obtener el comando (ignorando flags)
    cmd = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            cmd = arg
            break
    
    if not cmd:
        print("❌ Error: Debes proporcionar un comando para ejecutar")
        sys.exit(1)
    
    exit_code = run_command(cmd, verbose=verbose)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
