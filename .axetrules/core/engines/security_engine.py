import re
from typing import List
from ..models.models import SecretFinding

SECRET_PATTERNS = {
    "aws_access_key":    r"AKIA[0-9A-Z]{16}",
    "aws_secret_key":    r"(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})",
    "github_token":      r"gh[pousr]_[A-Za-z0-9]{36}",
    "gitlab_token":      r"glpat-[A-Za-z0-9\-]{20}",
    "google_api_key":    r"AIza[0-9A-Za-z\-_]{35}",
    "stripe_live_key":   r"sk_live_[A-Za-z0-9]{24,}",
    "jwt_token":         r"eyJ[A-Za-z0-9\-_]{10,}\.eyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}",
    "private_key":       r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "db_conn_string":    r"(?i)(mongodb|postgresql|postgres|mysql|redis)://[^:@\s]+:[^@\s]+@[^\s\"']+",
    "azure_conn_string": r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=",
    "generic_password":  r"(?i)(password|passwd|pwd)\s*[=:]\s*[\"']([^\"']{8,})[\"']",
    "generic_token":     r"(?i)(access_token|auth_token)\s*[=:]\s*[\"']([A-Za-z0-9_\-\.]{20,})[\"']",
}

HIGH_RISK_FILES = {
    ".env",".env.local",".env.production",".env.staging","config.yaml","config.yml",
    "secrets.yaml","secrets.yml","application.properties","application.yml",
    "appsettings.json","web.config","credentials","credentials.json",
}

EXCLUDE_SCAN_DIRS = {"test","tests","spec","__tests__","mocks","node_modules",".git","dist","build"}

class SecurityEngine:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def scan_secrets(self) -> List[SecretFinding]:
        RECS = {
            "aws_access_key":   "Revocar en AWS IAM Console y rotar credenciales",
            "github_token":     "Revocar en GitHub Settings → Developer settings → Tokens",
            "gitlab_token":     "Revocar en GitLab → User Settings → Access Tokens",
            "private_key":      "Rotar el par de claves y actualizar todos los servicios",
            "db_conn_string":   "Mover a variable de entorno — nunca hardcodear",
            "generic_password": "Usar variables de entorno o gestor de secretos",
            "jwt_token":        "Si es token de producción, invalidarlo inmediatamente",
        }
        findings: List[SecretFinding] = []
        for f in self.analyzer.all_files():
            if set(f.parts).intersection(EXCLUDE_SCAN_DIRS):
                if f.name not in HIGH_RISK_FILES: continue
            name_lower = f.name.lower()
            if any(x in name_lower for x in (".example",".sample",".template",".mock")): continue
            content = self.analyzer.read_safe(f, max_bytes=50_000)
            if not content: continue
            for stype, pattern in SECRET_PATTERNS.items():
                for m in re.finditer(pattern, content):
                    ln = content[:m.start()].count("\n") + 1
                    val = m.group(0)
                    redacted = val[:4] + "*" * max(0, len(val) - 8) + val[-4:] if len(val) > 8 else "*" * len(val)
                    findings.append(SecretFinding(stype, str(f.relative_to(self.analyzer.root)), ln,
                                                  redacted, "CRITICAL", RECS.get(stype,"")))
        seen: set = set()
        unique: List[SecretFinding] = []
        for f in findings:
            key = f"{f.file_path}:{f.line_number}:{f.secret_type}"
            if key not in seen: seen.add(key); unique.append(f)
        return unique
