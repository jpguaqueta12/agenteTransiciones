#!/usr/bin/env python3
"""
Discovery de proyectos en GitLab - RepoIntel
Ejecuta el descubrimiento de proyectos accesibles con el token proporcionado.

Uso: python discover_projects.py <base_url> <token> [group]
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from platform_client import PlatformClient, RepoContext
    import httpx
except ImportError as e:
    print(f"❌ Error importando dependencias: {e}")
    print("Instalando dependencias necesarias...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "pydantic", "--quiet"])
    from platform_client import PlatformClient, RepoContext
    import httpx

# Validar argumentos
if len(sys.argv) < 3:
    print("\n❌ Error: Se requieren base_url y token")
    print("Uso: python discover_projects.py <base_url> <token> [group]")
    print("\nEjemplos:")
    print("  python discover_projects.py https://gitlab.com glpat-xxxxxxxxxxxx")
    print("  python discover_projects.py https://gitlab.com glpat-xxxxxxxxxxxx mi-grupo\n")
    sys.exit(1)

BASE_URL = sys.argv[1].rstrip("/")
TOKEN = sys.argv[2]
GROUP = sys.argv[3] if len(sys.argv) > 3 else None


def discover_projects(base_url: str, token: str, group: str = None):
    """Descubre proyectos accesibles en la plataforma detectada (GitLab/GitHub/Azure/Bitbucket)."""
    
    print(f"\n🔍 Conectando a plataforma: {base_url}")
    print(f"🔑 Token: {token[:8]}...{token[-4:]}\n")
    
    # Detectar plataforma
    platform = PlatformClient.detect_platform(base_url)
    print(f"📡 Plataforma detectada: {platform.upper()}\n")
    
    # Crear contexto temporal para discovery
    context = RepoContext(
        platform=platform,
        base_url=base_url,
        token=token,
        project_id="",  # No necesario para discovery
        project_name="",
        project_url="",
    )
    
    try:
        with PlatformClient(context) as client:
            projects = []
            
            if group:
                # Listar proyectos de un grupo específico
                print(f"📂 Listando proyectos del grupo: {group}\n")
                projects = client.list_projects_in_group(group)
            else:
                # Intentar listar proyectos accesibles (puede requerir privilegios)
                print("📂 Listando proyectos accesibles con el token...\n")
                
                if platform == "gitlab":
                    # Para GitLab, intentamos obtener proyectos donde el usuario es miembro
                    url = f"{base_url}/api/v4/projects?membership=true&per_page=100"
                    response = client._get(url)
                    
                    if isinstance(response, list):
                        projects = [client._normalize_project(p) for p in response[:50]]
                    else:
                        print("⚠️  No se pudieron obtener proyectos directamente.")
                        print("Intenta proporcionar un group/namespace específico.\n")
                        return []
                
                elif platform == "github":
                    # Para GitHub, si no se especifica group, derivar el usuario desde la URL
                    # Ej: https://github.com/jpguaqueta12 → user = jpguaqueta12
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url if "://" in base_url else f"https://{base_url}")
                    user = parsed.path.strip("/").split("/")[0] if parsed.path.strip("/") else ""
                    if not user:
                        print("⚠️  No se pudo inferir el usuario/organización desde base_url.")
                        print("Proporciona GROUP (org) o usa base_url tipo https://github.com/<user>.\n")
                        return []
                    
                    url = f"https://api.github.com/users/{user}/repos"
                    response = client._get(url, params={"per_page": 100, "sort": "pushed"})
                    if isinstance(response, list):
                        projects = [client._normalize_project(p) for p in response[:50]]
                    else:
                        print("⚠️  No se pudieron obtener repositorios del usuario.")
                        print("Verifica el token o proporciona GROUP (org).\n")
                        return []
                
                else:
                    print(f"⚠️  Discovery sin GROUP no implementado para plataforma: {platform}")
                    print("Intenta proporcionar un group/namespace/organización.\n")
                    return []
            
            if not projects:
                print("⚠️  No se encontraron proyectos accesibles.")
                print("\nPosibles causas:")
                print("  • El token no tiene permisos suficientes")
                print("  • No hay repos/proyectos en el grupo/usuario especificado")
                print("  • Necesitas especificar un group/namespace/organización\n")
                return []
            
            # Mostrar proyectos encontrados
            print(f"✅ Encontrados {len(projects)} proyecto(s):\n")
            print("─" * 80)
            print(f"{'#':<4} {'NOMBRE':<30} {'VISIBILIDAD':<12} {'ÚLTIMA ACTIVIDAD'}")
            print("─" * 80)
            
            for i, proj in enumerate(projects, 1):
                name = proj.name[:28] + ".." if len(proj.name) > 30 else proj.name
                visibility = proj.visibility[:10]
                activity = proj.last_activity[:10] if proj.last_activity else "N/A"
                print(f"{i:<4} {name:<30} {visibility:<12} {activity}")
            
            print("─" * 80)
            print(f"\n💡 Para analizar un proyecto, selecciona el número (1-{len(projects)})")
            print(f"   O proporciona la ruta completa del proyecto\n")
            
            # Guardar lista para referencia
            with open(".repo_intel_projects.txt", "w", encoding="utf-8") as f:
                for i, proj in enumerate(projects, 1):
                    f.write(f"{i}|{proj.id}|{proj.name}|{proj.clone_url_https}\n")
            
            return projects
            
    except PermissionError as e:
        print(f"❌ Error de permisos: {e}")
        print("\nVerifica que tu token tenga permisos de lectura en la plataforma detectada.")
        print("  • GitLab: read_api + read_repository")
        print("  • GitHub: Contents: Read, Metadata: Read (y repo si es clásico)\n")
        return []
    
    except httpx.HTTPStatusError as e:
        print(f"❌ Error HTTP {e.response.status_code}: {e}")
        if e.response.status_code == 401:
            print("\n🔑 Token inválido o expirado")
        elif e.response.status_code == 403:
            print("\n🔒 Sin permisos suficientes")
        return []
    
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    # Ejecutar discovery con los argumentos proporcionados
    projects = discover_projects(BASE_URL, TOKEN, GROUP)
    
    if projects:
        print("✅ Discovery completado exitosamente")
        print(f"📄 Lista guardada en: .repo_intel_projects.txt\n")
    else:
        print("❌ No se pudieron obtener proyectos")
        print("\n💡 Soluciones:")
        print("   1. Verifica que el token sea correcto")
        print("   2. Proporciona un grupo/namespace específico")
        print("   3. Verifica la conectividad con el servidor Git\n")
