# 🔗 Dependency Mapping — Mapa de Dependencias

**Proyecto:** allianz  
**Fase:** Dependency Mapping  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  
**CLONE_DIR:** `/tmp/repo-intel/allianz@main/`  

---

## 📌 Resumen Ejecutivo

Este documento mapea las **dependencias técnicas reales** del sistema a partir de evidencia estática (manifiestos y estructura del repo clonado). El objetivo es identificar:

- Dependencias de librerías (backend + frontend)
- Dependencias de infraestructura (DB/cache/identity)
- Dependencias externas probables (Azure SQL / Azure Identity / OpenAI)
- **SPOFs** (Single Points of Failure) inferidos
- Riesgos de acoplamiento que impactan continuidad operativa y transición

**Resultado:** mapa parcial (sin evidencia de runtime/K8s/Terraform). Con alta confianza se detectan:
- Backend FastAPI con dependencias de Postgres (`asyncpg`), SQL Server/Azure SQL (`pyodbc`), Redis (`redis`)
- Frontend React/Vite (SPA) con stack moderno (React Router, Zustand, React Query)
- Integraciones potenciales con Azure AD / Managed Identity (`azure-identity`)
- Integraciones de IA (`langchain-openai`, `langgraph`) → dependencia externa probable (OpenAI u otro provider compatible)

---

## 🔎 Evidencia Analizada

### Manifiestos encontrados en el CLONE_DIR

- `back-planificacion/requirements.txt`
- `front-planificacion/package.json`

> No se encontraron (en el escaneo realizado): `docker-compose.yml`, manifiestos `k8s/`, `*.tf`, `pom.xml`, `go.mod`.

---

## 🧱 Dependencias por componente

### 1) `back-planificacion` (Backend / API)

**Framework / runtime**
- `fastapi==0.115.0`
- `uvicorn[standard]==0.30.0`

**Autenticación / seguridad**
- `python-jose[cryptography]==3.3.0` (JWT / JOSE)
- `passlib[bcrypt]==1.7.4`
- `bcrypt==4.0.1`

**IA / Orquestación**
- `langchain>=0.3.0,<0.4`
- `langchain-openai>=0.2.0,<0.3`
- `langgraph>=0.2.14,<0.3`

**Persistencia / datos**
- `asyncpg==0.29.0` → PostgreSQL (🔴 crítica)
- `pyodbc==5.2.0` → SQL Server / Azure SQL (🔴 crítica)
- `redis[hstore]==5.0.8` → Redis (🟠 alta)

**Plataforma**
- `azure-identity==1.25.1` → Azure AD / Managed Identity / Service Principal (🟠 alta)

**Observabilidad / utilitarios**
- `structlog==24.4.0` (logging estructurado)

**Soporte de features**
- `python-multipart==0.0.12` (uploads/form-data)
- `openpyxl==3.1.5` (Excel)
- `pypdf>=4.0.0` (PDF)
- `python-docx>=1.1.0` (Word)

---

### 2) `front-planificacion` (Frontend / SPA)

**Core**
- `react@^18.3.1`
- `react-dom@^18.3.1`
- `vite@^5.4.0`

**Routing / estado / data fetching**
- `react-router-dom@^6.26.0`
- `zustand@^4.5.4`
- `@tanstack/react-query@^5.51.0`

**UI / utils**
- `tailwindcss@^3.4.7`
- `lucide-react@^0.427.0`
- `date-fns@^3.6.0`
- `clsx@^2.1.1`
- `xlsx@^0.18.5`

---

## 🧩 Dependencias de infraestructura (servicios)

> Estas dependencias son **operativas**: sin ellas el sistema no funciona correctamente en producción.

| Dependencia | Tipo | Criticidad | Evidencia | Observación |
|---|---|---:|---|---|
| PostgreSQL | Base de datos | 🔴 Alta | `asyncpg` en `requirements.txt` | No hay host/URL en evidencia actual |
| SQL Server / Azure SQL | Base de datos | 🔴 Alta | `pyodbc` en `requirements.txt` | Auditor detectó scripts y passwords en `seed_azure_sql.py` / `test_sql_connection.py` |
| Redis | Cache / store | 🟠 Media/Alta | `redis` en `requirements.txt` | Sin evidencia de HA/failover |
| Azure AD / Identity | IAM | 🟠 Media/Alta | `azure-identity` | Puede ser auth a DB/KeyVault/Graph |
| LLM Provider (OpenAI u otro) | API externa | 🟠 Media/Alta | `langchain-openai` | Dependencia externa + costos/rate limits |

---

## 🔌 Dependencias externas (probables)

Sin leer código de configuración, solo se puede inferir por librerías:

| Servicio externo | Señal | Riesgo |
|---|---|---|
| OpenAI (u otro compatible) | `langchain-openai` | Rate limits / costos / disponibilidad |
| Azure SQL | `pyodbc` + scripts `seed_azure_sql.py` | Credenciales/rotación/seguridad |
| Azure Identity | `azure-identity` | Rotación de SP, políticas de acceso |

---

## ⚠️ SPOFs (Single Points of Failure) — inferidos

> No hay evidencia de HA, réplicas o mecanismos de resiliencia. Por lo tanto, los SPOFs se marcan como “potenciales”.

| SPOF potencial | Por qué | Impacto |
|---|---|---|
| PostgreSQL (único) | DB crítica detectada, sin evidencia de réplica/failover | Caída total del backend |
| Azure SQL / SQL Server (único) | DB crítica, además hay scripts de seed/conn test | Caída total / corrupción de datos |
| Redis (único) | Cache/sesiones potenciales | Degradación severa / fallos |
| LLM Provider | Dependencia externa (IA) | Flujos de IA se rompen si el provider cae |

---

## 🗺️ Grafo de dependencias (Mermaid)

```mermaid
graph LR
  FE[front-planificacion<br/>React + Vite] -->|HTTP| BE[back-planificacion<br/>FastAPI]

  BE --> PG[(PostgreSQL)]
  BE --> REDIS[(Redis)]
  BE --> MSSQL[(SQL Server / Azure SQL)]
  BE --> AZID[Azure Identity / AAD]
  BE --> LLM[LLM Provider (OpenAI/compatible)]
```

---

## ✅ Recomendaciones priorizadas

### P1 — Bloqueantes para transición / Día 1
1) **Identificar endpoints reales** (hosts, puertos, VNets) de PostgreSQL/Redis/Azure SQL.
2) **Validar ownership y SLAs** de cada dependencia crítica.
3) **Eliminar secretos del código y rotarlos** (ver Auditor: 3 hallazgos).

### P2 — Resiliencia / continuidad
4) Documentar HA/failover (réplicas Postgres, Redis cluster, Azure SQL tier/HA).
5) Definir timeouts/retries/circuit breaker para dependencias externas (LLM provider, APIs).

### P3 — Gobernanza técnica
6) Generar SBOM (software bill of materials) y correr CVE scan completo (OSV/Snyk/Dependabot).
7) Establecer “dependency update policy” (renovate/dependabot) por sprint.

---

## Limitaciones de evidencia

- No hay `docker-compose.yml`, `k8s`, `terraform` o config de runtime en el set analizado.
- No se ejecutaron llamadas dinámicas (tráfico/logs) ni se verificó despliegue real.
- Este documento debe confirmarse con inputs de DevOps/SRE y accesos de plataforma.

---

*Generado por Agencia de Transición — 2026-05-18*
