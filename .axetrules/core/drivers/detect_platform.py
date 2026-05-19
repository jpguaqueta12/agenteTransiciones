#!/usr/bin/env python3
"""
detect_platform.py — Agencia de Transición
Detecta automáticamente la plataforma Git a partir de cualquier URL
y actualiza credentials/.env con los valores correctos.

Uso:
    python .axetrules/core/drivers/detect_platform.py <URL>
    python .axetrules/core/drivers/detect_platform.py https://github.com/org/repo
    python .axetrules/core/drivers/detect_platform.py https://umane.emeal.nttdata.com/git/GRUPO/repo.git

También importable:
    from core.drivers.detect_platform import detect_platform, PlatformInfo
    info = detect_platform("https://gitlab.com/grupo/repo")
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


# ── Modelo de resultado ───────────────────────────────────────────────────────

@dataclass
class PlatformInfo:
    platform: str           # gitlab | github | azure | bitbucket | unknown
    base_url: str           # https://hostname  (sin path)
    project_id: str         # namespace/repo  o  org/project/repo (Azure)
    project_name: str       # solo el nombre del repo
    group: str              # organización / grupo / workspace
    project_url: str        # URL de clonado normalizada (https, sin .git al final)
    clone_url: str          # URL con .git para git clone
    confidence: str         # ALTA | MEDIA | BAJA
    token_url: str          # URL donde crear el token
    token_scopes: str       # scopes necesarios
    notes: str = ""         # advertencias o aclaraciones
    original_url: str = ""  # URL original recibida


# ── Reglas de detección ───────────────────────────────────────────────────────

_RULES = [
    # (patrón en hostname o path, plataforma, confianza)
    (r"github\.com",                    "github",    "ALTA"),
    (r"api\.github\.com",               "github",    "ALTA"),
    (r"^gitlab\.com$",                  "gitlab",    "ALTA"),
    (r"gitlab\.",                        "gitlab",    "ALTA"),
    (r"dev\.azure\.com",                "azure",     "ALTA"),
    (r"\.visualstudio\.com",            "azure",     "ALTA"),
    (r"bitbucket\.org",                 "bitbucket", "ALTA"),
    (r"bitbucket\.",                    "bitbucket", "MEDIA"),
    (r"/api/v4",                        "gitlab",    "ALTA"),   # path signal
    (r"/git/",                          "gitlab",    "MEDIA"),  # common self-hosted path
]

_TOKEN_INFO = {
    "gitlab": {
        "scopes": "read_api, read_repository",
        "url_template": "{base_url}/-/profile/personal_access_tokens",
    },
    "github": {
        "scopes": "Contents: Read, Metadata: Read, Pull requests: Read",
        "url_template": "https://github.com/settings/tokens/new",
    },
    "azure": {
        "scopes": "Code (Read), Project and Team (Read)",
        "url_template": "https://dev.azure.com/{group}/_usersSettings/tokens",
    },
    "bitbucket": {
        "scopes": "Repositories: Read, Pull requests: Read",
        "url_template": "https://bitbucket.org/account/settings/app-passwords/new",
    },
    "unknown": {
        "scopes": "Permisos de lectura de repositorio",
        "url_template": "",
    },
}


# ── Lógica de detección ───────────────────────────────────────────────────────

def detect_platform(url: str) -> PlatformInfo:
    """
    Detecta la plataforma Git a partir de una URL.

    Acepta:
      - https://github.com/org/repo
      - https://gitlab.com/grupo/sub/repo.git
      - https://umane.emeal.nttdata.com/git/GRUPO/repo.git
      - https://dev.azure.com/org/project/_git/repo
      - https://bitbucket.org/workspace/repo
      - git@github.com:org/repo.git
    """
    original = url.strip()

    # Normalizar SSH → HTTPS para parsear
    url = _normalize_ssh(original)

    parsed = urlparse(url if "://" in url else f"https://{url}")
    hostname = parsed.hostname or ""
    path = parsed.path.strip("/")

    # ── Detectar plataforma ───────────────────────────────────────────────────
    platform, confidence = _match_platform(hostname, path)

    # ── Extraer componentes según plataforma ──────────────────────────────────
    if platform == "github":
        return _parse_github(parsed, hostname, path, confidence, original)
    elif platform == "gitlab":
        return _parse_gitlab(parsed, hostname, path, confidence, original)
    elif platform == "azure":
        return _parse_azure(parsed, hostname, path, confidence, original)
    elif platform == "bitbucket":
        return _parse_bitbucket(parsed, hostname, path, confidence, original)
    else:
        return _parse_unknown(parsed, hostname, path, original)


def _normalize_ssh(url: str) -> str:
    """Convierte git@github.com:org/repo.git → https://github.com/org/repo.git"""
    m = re.match(r"git@([^:]+):(.+)", url)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}"
    return url


def _match_platform(hostname: str, path: str) -> tuple[str, str]:
    """Aplica las reglas de detección y retorna (plataforma, confianza)."""
    combined = f"{hostname}/{path}".lower()
    for pattern, platform, confidence in _RULES:
        if re.search(pattern, combined):
            return platform, confidence
    # Fallback: URL corporativa desconocida → asumir GitLab self-hosted
    return "gitlab", "BAJA"


# ── Parsers por plataforma ────────────────────────────────────────────────────

def _parse_github(parsed, hostname, path, confidence, original) -> PlatformInfo:
    base_url = "https://github.com"
    parts = [p for p in path.split("/") if p]
    # Remover .git del último segmento
    if parts and parts[-1].endswith(".git"):
        parts[-1] = parts[-1][:-4]

    group = parts[0] if len(parts) >= 1 else ""
    repo  = parts[1] if len(parts) >= 2 else ""
    project_id = f"{group}/{repo}" if group and repo else path

    clone_url   = f"https://github.com/{project_id}.git"
    project_url = f"https://github.com/{project_id}"
    token_url   = "https://github.com/settings/tokens/new"

    return PlatformInfo(
        platform="github", base_url=base_url,
        project_id=project_id, project_name=repo, group=group,
        project_url=project_url, clone_url=clone_url,
        confidence=confidence,
        token_url=token_url,
        token_scopes="Contents: Read, Metadata: Read, Pull requests: Read",
        original_url=original,
    )


def _parse_gitlab(parsed, hostname, path, confidence, original) -> PlatformInfo:
    # Base URL: scheme + hostname (sin path de API ni /git/)
    scheme = parsed.scheme or "https"
    base_url = f"{scheme}://{hostname}"

    # Limpiar path: quitar prefijos comunes de self-hosted (/git/, /gitlab/, etc.)
    clean_path = re.sub(r"^(git|gitlab)/", "", path, flags=re.I)
    # Quitar .git del final
    clean_path = re.sub(r"\.git$", "", clean_path)

    parts = [p for p in clean_path.split("/") if p]

    # El repo es el último segmento; el grupo es todo lo anterior
    repo  = parts[-1] if parts else ""
    group = "/".join(parts[:-1]) if len(parts) > 1 else ""
    project_id = clean_path  # namespace/subgrupo/repo

    # Detectar prefijo de path del servidor (ej: /git en umane.emeal.nttdata.com/git)
    raw_parts = [p for p in path.split("/") if p]
    prefix = ""
    if raw_parts and raw_parts[0].lower() in ("git", "gitlab", "scm"):
        prefix = f"/{raw_parts[0]}"
        base_url = f"{scheme}://{hostname}{prefix}"

    clone_url   = f"{base_url}/{project_id}.git"
    project_url = f"{base_url}/{project_id}"

    token_url = f"{base_url}/-/profile/personal_access_tokens"
    notes = ""
    if confidence == "BAJA":
        notes = "URL corporativa — asumiendo GitLab Self-Hosted. Confirma si es otra plataforma."

    return PlatformInfo(
        platform="gitlab", base_url=base_url,
        project_id=project_id, project_name=repo, group=group,
        project_url=project_url, clone_url=clone_url,
        confidence=confidence,
        token_url=token_url,
        token_scopes="read_api, read_repository",
        notes=notes,
        original_url=original,
    )


def _parse_azure(parsed, hostname, path, confidence, original) -> PlatformInfo:
    base_url = "https://dev.azure.com"
    # Formato: dev.azure.com/{org}/{project}/_git/{repo}
    # o:       {org}.visualstudio.com/{project}/_git/{repo}
    parts = [p for p in path.split("/") if p and p != "_git"]

    if "visualstudio.com" in hostname:
        org = hostname.split(".")[0]
        parts = [org] + parts

    org     = parts[0] if len(parts) >= 1 else ""
    project = parts[1] if len(parts) >= 2 else ""
    repo    = parts[2] if len(parts) >= 3 else project

    project_id  = f"{org}/{project}/{repo}"
    project_url = f"https://dev.azure.com/{org}/{project}/_git/{repo}"
    clone_url   = project_url
    token_url   = f"https://dev.azure.com/{org}/_usersSettings/tokens"

    return PlatformInfo(
        platform="azure", base_url=base_url,
        project_id=project_id, project_name=repo, group=org,
        project_url=project_url, clone_url=clone_url,
        confidence=confidence,
        token_url=token_url,
        token_scopes="Code (Read), Project and Team (Read)",
        original_url=original,
    )


def _parse_bitbucket(parsed, hostname, path, confidence, original) -> PlatformInfo:
    scheme = parsed.scheme or "https"
    is_cloud = "bitbucket.org" in hostname
    base_url = "https://bitbucket.org" if is_cloud else f"{scheme}://{hostname}"

    clean_path = re.sub(r"\.git$", "", path)
    parts = [p for p in clean_path.split("/") if p]

    workspace = parts[0] if len(parts) >= 1 else ""
    repo      = parts[1] if len(parts) >= 2 else ""
    project_id = f"{workspace}/{repo}"

    clone_url   = f"{base_url}/{project_id}.git"
    project_url = f"{base_url}/{project_id}"

    if is_cloud:
        token_url   = "https://bitbucket.org/account/settings/app-passwords/new"
        token_scopes = "Repositories: Read, Pull requests: Read"
    else:
        token_url   = f"{base_url}/plugins/servlet/access-tokens/manage"
        token_scopes = "Repository read"

    return PlatformInfo(
        platform="bitbucket", base_url=base_url,
        project_id=project_id, project_name=repo, group=workspace,
        project_url=project_url, clone_url=clone_url,
        confidence=confidence,
        token_url=token_url,
        token_scopes=token_scopes,
        original_url=original,
    )


def _parse_unknown(parsed, hostname, path, original) -> PlatformInfo:
    scheme = parsed.scheme or "https"
    base_url = f"{scheme}://{hostname}"
    clean_path = re.sub(r"\.git$", "", path)
    parts = [p for p in clean_path.split("/") if p]
    repo = parts[-1] if parts else ""

    return PlatformInfo(
        platform="unknown", base_url=base_url,
        project_id=clean_path, project_name=repo, group="",
        project_url=f"{base_url}/{clean_path}",
        clone_url=f"{base_url}/{clean_path}.git",
        confidence="BAJA",
        token_url="",
        token_scopes="Permisos de lectura de repositorio",
        notes="No se pudo determinar la plataforma. Especifica PLATFORM manualmente en credentials/.env",
        original_url=original,
    )


# ── Actualizar credentials/.env ───────────────────────────────────────────────

def update_env_file(info: PlatformInfo, env_path: Optional[Path] = None) -> Path:
    """
    DEPRECATED — no llamar. credentials/.env solo contiene URL y TOKEN.
    Los datos derivados van a memory/agency_state.json via update_agency_state().
    Esta función existe solo por compatibilidad histórica y no debe invocarse.
    """
    if env_path is None:
        # Buscar el .env subiendo desde el directorio actual
        current = Path.cwd()
        for parent in [current, *current.parents]:
            candidate = parent / ".axetrules" / "credentials" / ".env"
            if candidate.exists():
                env_path = candidate
                break
        if env_path is None:
            # Buscar relativo al script
            script_dir = Path(__file__).resolve().parent
            for parent in [script_dir, *script_dir.parents]:
                candidate = parent / "credentials" / ".env"
                if candidate.exists():
                    env_path = candidate
                    break
        if env_path is None:
            raise FileNotFoundError(
                "No se encontró credentials/.env — "
                "asegúrate de estar en el directorio del workspace"
            )

    # Leer contenido actual
    lines = env_path.read_text(encoding="utf-8").splitlines()

    # Valores a actualizar (no tocar TOKEN ni CLONE_*)
    updates = {
        "PLATFORM":       info.platform,
        "BASE_URL":       info.base_url,
        "PROJECT_ID":     info.project_id,
        "PROJECT_NAME":   info.project_name,
        "PROJECT_URL":    info.clone_url,
        "GROUP":          info.group,
        "DEFAULT_BRANCH": "main",
    }

    new_lines = []
    updated_keys: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    # Agregar claves que no existían
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return env_path


# ── Actualizar agency_state.json ──────────────────────────────────────────────

def update_agency_state(info: PlatformInfo) -> None:
    """Persiste el resultado de detección en memory/agency_state.json"""
    # Buscar el archivo de estado
    current = Path.cwd()
    state_path = None
    for parent in [current, *current.parents]:
        candidate = parent / ".axetrules" / "memory" / "agency_state.json"
        if candidate.exists():
            state_path = candidate
            break
    if state_path is None:
        # Crear si no existe
        for parent in [current, *current.parents]:
            axe = parent / ".axetrules"
            if axe.exists():
                state_path = axe / "memory" / "agency_state.json"
                state_path.parent.mkdir(parents=True, exist_ok=True)
                break

    if state_path is None:
        return  # No se puede persistir, continuar sin error

    state: dict = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    state["detected_platform"] = {
        "platform":     info.platform,
        "base_url":     info.base_url,
        "confidence":   info.confidence,
        "detected_at":  datetime.now().isoformat(),
        "original_url": info.original_url,
    }

    state_path.write_text(json.dumps(state, indent=4, ensure_ascii=False), encoding="utf-8")


# ── Presentación ──────────────────────────────────────────────────────────────

_PLATFORM_LABELS = {
    "gitlab":    "GitLab",
    "github":    "GitHub",
    "azure":     "Azure DevOps",
    "bitbucket": "Bitbucket",
    "unknown":   "Desconocida",
}

_CONFIDENCE_ICONS = {"ALTA": "🟢", "MEDIA": "🟡", "BAJA": "🔴"}


def print_result(info: PlatformInfo, env_updated: bool = False) -> None:
    label = _PLATFORM_LABELS.get(info.platform, info.platform)
    icon  = _CONFIDENCE_ICONS.get(info.confidence, "⚪")

    print("\n" + "=" * 55)
    print("🔎 PLATAFORMA DETECTADA")
    print("=" * 55)
    print(f"  Plataforma   : {label}  {icon} (confianza: {info.confidence})")
    print(f"  Base URL     : {info.base_url}")
    print(f"  Project ID   : {info.project_id}")
    print(f"  Nombre       : {info.project_name}")
    if info.group:
        print(f"  Grupo/Org    : {info.group}")
    print(f"  Clone URL    : {info.clone_url}")
    if info.notes:
        print(f"\n  ⚠️  {info.notes}")
    print()
    print(f"  🔑 Token necesario:")
    print(f"     Scopes : {info.token_scopes}")
    if info.token_url:
        print(f"     Crear en: {info.token_url}")
    print("=" * 55)

    if env_updated:
        print("✅ credentials/.env actualizado")
        print("   Solo falta agregar el TOKEN\n")
    else:
        print()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUso: python detect_platform.py <URL>")
        print("\nEjemplos:")
        print("  python detect_platform.py https://github.com/org/repo")
        print("  python detect_platform.py https://gitlab.com/grupo/repo.git")
        print("  python detect_platform.py https://umane.emeal.nttdata.com/git/GRUPO/repo.git")
        print("  python detect_platform.py https://dev.azure.com/org/project/_git/repo")
        print("  python detect_platform.py git@github.com:org/repo.git\n")
        sys.exit(1)

    input_url = sys.argv[1]

    # Detectar
    info = detect_platform(input_url)

    # Mostrar resultado
    print_result(info)

    # Persistir SOLO en memory/agency_state.json — nunca tocar credentials/.env
    try:
        update_agency_state(info)
        print("✅ Plataforma guardada en memory/agency_state.json")
    except Exception:
        pass  # No crítico

    # Output JSON para integración con otros scripts
    if "--json" in sys.argv:
        print("\n--- JSON ---")
        print(json.dumps(asdict(info), indent=2, ensure_ascii=False))

    sys.exit(0 if info.platform != "unknown" else 1)
