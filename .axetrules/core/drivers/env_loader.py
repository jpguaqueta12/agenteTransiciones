#!/usr/bin/env python3
"""
env_loader.py — Agencia de Transición
Lee credentials/.env (solo URL + TOKEN) y deriva todo lo demás
usando detect_platform internamente.

El usuario solo configura dos campos:
    URL=https://github.com/org/repo
    TOKEN=ghp_xxxxx

La agencia detecta automáticamente:
    - Plataforma (github | gitlab | azure | bitbucket)
    - Base URL
    - Project ID
    - Project Name
    - Group / Org
    - Clone URL

Uso:
    from core.drivers.env_loader import load_credentials
    creds = load_credentials()
    # creds["TOKEN"], creds["URL"], creds["PLATFORM"], creds["PROJECT_NAME"], ...
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

_PLACEHOLDER_TOKEN = "TU_TOKEN_AQUI"
_PLACEHOLDER_URL   = "https://github.com/org/repo"


def _find_env_file() -> Path:
    """Sube desde el CWD hasta encontrar .axetrules/credentials/.env"""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        candidate = parent / ".axetrules" / "credentials" / ".env"
        if candidate.exists():
            return candidate
    # Fallback relativo al script
    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir, *script_dir.parents]:
        for candidate in [
            parent / "credentials" / ".env",
            parent / ".axetrules" / "credentials" / ".env",
        ]:
            if candidate.exists():
                return candidate
    raise FileNotFoundError(
        "No se encontró credentials/.env\n"
        "Crea el archivo en: .axetrules/credentials/.env\n"
        "Solo necesitas dos líneas:\n"
        "  URL=https://github.com/org/repo\n"
        "  TOKEN=tu_token_aqui"
    )


def _parse_env_file(path: Path) -> Dict[str, str]:
    """Lee el .env y retorna un dict con las claves encontradas."""
    result: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key   = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


def load_credentials(env_path: Optional[str] = None) -> Dict[str, str]:
    """
    Carga URL y TOKEN desde credentials/.env y deriva el resto
    usando detect_platform.

    Returns:
        Dict con: URL, TOKEN, PLATFORM, BASE_URL, PROJECT_ID,
                  PROJECT_NAME, GROUP, CLONE_URL, CLONE_BASE_DIR
    Raises:
        FileNotFoundError: si no existe el .env
        ValueError: si URL o TOKEN están vacíos o son placeholders
    """
    path = Path(env_path) if env_path else _find_env_file()
    raw  = _parse_env_file(path)

    url   = raw.get("URL",   "").strip()
    token = raw.get("TOKEN", "").strip()

    # Validaciones mínimas
    if not url or url == _PLACEHOLDER_URL:
        raise ValueError(
            "Falta configurar URL en credentials/.env\n"
            f"Edita: {path}\n"
            "Ejemplo: URL=https://github.com/org/repo"
        )
    if not token or token == _PLACEHOLDER_TOKEN:
        raise ValueError(
            "Falta configurar TOKEN en credentials/.env\n"
            f"Edita: {path}\n"
            "Ejemplo: TOKEN=ghp_xxxxxxxxxxxxxxxx"
        )

    # Derivar todo lo demás con detect_platform
    try:
        # Import lazy para evitar ciclos
        _drivers = Path(__file__).resolve().parent
        if str(_drivers) not in sys.path:
            sys.path.insert(0, str(_drivers))
        from detect_platform import detect_platform
        info = detect_platform(url)
    except Exception as e:
        # Si detect_platform falla, devolver mínimo funcional
        return {
            "URL":            url,
            "TOKEN":          token,
            "PLATFORM":       "unknown",
            "BASE_URL":       url,
            "PROJECT_ID":     "",
            "PROJECT_NAME":   url.rstrip("/").split("/")[-1].replace(".git", ""),
            "GROUP":          "",
            "CLONE_URL":      url if url.endswith(".git") else url + ".git",
            "CLONE_BASE_DIR": "/tmp/repo-intel",
        }

    return {
        "URL":            url,
        "TOKEN":          token,
        "PLATFORM":       info.platform,
        "BASE_URL":       info.base_url,
        "PROJECT_ID":     info.project_id,
        "PROJECT_NAME":   info.project_name,
        "GROUP":          info.group,
        "CLONE_URL":      info.clone_url,
        "CLONE_BASE_DIR": "/tmp/repo-intel",
        # Compatibilidad con código que usa PROJECT_URL
        "PROJECT_URL":    info.clone_url,
        "DEFAULT_BRANCH": "main",
    }


def get_clone_url(creds: Dict[str, str]) -> str:
    """
    Construye la URL de clonado con el token embebido.
    """
    url      = creds.get("CLONE_URL") or creds.get("PROJECT_URL") or creds.get("URL", "")
    token    = creds.get("TOKEN", "")
    platform = creds.get("PLATFORM", "github")

    if "https://" not in url:
        return url  # SSH u otro protocolo

    auth_map = {
        "gitlab":    f"https://oauth2:{token}@",
        "github":    f"https://x-access-token:{token}@",
        "azure":     f"https://anything:{token}@",
        "bitbucket": f"https://x-token-auth:{token}@",
    }
    prefix = auth_map.get(platform, f"https://oauth2:{token}@")
    return url.replace("https://", prefix)


def print_summary(creds: Dict[str, str]) -> None:
    """Imprime un resumen sin exponer el token completo."""
    token = creds.get("TOKEN", "")
    token_preview = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"
    platform = creds.get("PLATFORM", "").upper()
    print(f"  Plataforma : {platform}")
    print(f"  URL        : {creds.get('URL', '')}")
    print(f"  Proyecto   : {creds.get('PROJECT_NAME', '—')}")
    print(f"  Token      : {token_preview}")


# ── CLI de diagnóstico ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("🔍 ENV LOADER — Diagnóstico de Credenciales")
    print("=" * 55 + "\n")
    try:
        creds = load_credentials()
        print_summary(creds)
        print(f"\n  Plataforma detectada : {creds['PLATFORM']}")
        print(f"  Base URL             : {creds['BASE_URL']}")
        print(f"  Project ID           : {creds['PROJECT_ID']}")
        print(f"  Group / Org          : {creds['GROUP'] or '—'}")
        print(f"  Clone URL            : {creds['CLONE_URL']}")
        print("\n✅ Credenciales válidas — Agencia lista para operar\n")
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"❌ {e}\n")
        sys.exit(1)
    except ValueError as e:
        print(f"⚠️  {e}\n")
        sys.exit(1)
