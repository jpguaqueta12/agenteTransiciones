# 🧭 Guía de Onboarding — allianz (Día 1)

**Proyecto:** allianz  
**Fase:** Knowledge Management  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 1) ¿Qué hace este sistema? (vista negocio)

Solución de **planificación** enfocada en:

- Definir **PIs** (Program Increment) y su calendario (festivos)
- Gestionar **capacidad** (personas, horas, disponibilidad, sincronización)
- Operar **backlog** por módulos (CRUD, fechas, estados, escalamiento, SLA, planificación)
- Proveer **dashboards/alertas/SLA**
- Flujos auxiliares: **uploads Excel**, **estimación asistida (IA)** y **exportación a Word**
- Incluye un flujo de **sesión / chat** (posible asistente IA)

> La evidencia actual es principalmente estática (endpoints consumidos por frontend). Debe validarse con routers FastAPI y KT.

---

## 2) Componentes principales (vista técnica)

| Componente | Tipo | Stack | Ruta (inferida) | Rol |
|---|---|---|---|---|
| `front-planificacion` | SPA Frontend | React + Vite + TypeScript | `front-planificacion/` | UI + consumo de API `/api/v1/*` |
| `back-planificacion` | Backend API | Python + FastAPI | `back-planificacion/` | API principal + lógica de negocio |

### Dependencias críticas operativas (infra)

| Servicio | Señal | Criticidad | Observaciones |
|---|---|---:|---|
| PostgreSQL | `asyncpg` | 🔴 | No se evidencian hosts/roles/HA |
| SQL Server / Azure SQL | `pyodbc` + scripts | 🔴 | Auditor detectó passwords hardcodeados |
| Redis | `redis` | 🟠 | No hay evidencia de HA/failover |
| Azure Identity / AAD | `azure-identity` | 🟠 | Usado para auth/integraciones Azure (inferido) |
| LLM Provider (OpenAI/compatible) | `langchain-openai`, `langgraph` | 🟠 | Afecta chat/estimación |

---

## 3) Accesos mínimos para operar Día 1 (checklist)

Basado en `06_access-readiness/access_readiness_report.md`:

### Repositorio / CI
- [ ] Acceso al repo GitHub `jpguaqueta12/allianz` (clone + PRs)
- [ ] Acceso a GitHub Actions (runs/logs/artifacts) si se usa como CI

### Runtime / Infra (no evidenciado en outputs)
- [ ] Acceso al entorno donde corre el backend (K8s/VM/PaaS)
- [ ] Acceso al hosting del frontend (CDN/nginx/static hosting)

### Bases de datos / Cache (bloqueantes si es prod)
- [ ] Acceso a PostgreSQL (al menos read/diagnóstico)
- [ ] Acceso a SQL Server / Azure SQL (al menos read/diagnóstico)
- [ ] Acceso a Redis (diagnóstico, claves, métricas)

### Observabilidad (bloqueante)
- [ ] Logs centralizados
- [ ] Métricas/APM + dashboards
- [ ] Alerting/on-call

### Secret manager / rotación (bloqueante)
- [ ] Acceso a gestor de secretos (AKV/Vault/ASM/otro)
- [ ] Rotación de secretos detectados (3 hallazgos)

---

## 4) Variables de entorno (plantilla sugerida)

> No hay `.env.example` evidenciada. Esta lista es **inferida** y debe confirmarse en KT / config real.

### Frontend (Vite)
- `VITE_API_BASE_URL` — base URL del backend (sin `/api/v1`)

### Backend (FastAPI)
- `DATABASE_URL` o equivalente para Postgres
- `AZURE_SQL_*` o string de conexión para SQL Server/Azure SQL
- `REDIS_URL`
- Credenciales/variables para Azure Identity (si usa Service Principal / Managed Identity)
- Variables para LLM provider (API key, model, endpoint)

---

## 5) Flujos críticos que debes entender primero

Orden recomendado (P1 → P2):

### P1 — Operación core
1) **AuthN/AuthZ** (`/auth/*`)
2) **PI** (`/config/pis/*`)
3) **Capacidad** (`/config/pis/{piId}/capacidad/*`)
4) **Backlog** (`/backlog/*` + `planificacion` + `status` + `escalamiento`)

### P2 — Reporting
- Dashboards (`/dashboard*`)
- Alertas (`/alertas/{modulo}`)
- SLA (`/sla/{modulo}`)

### P3 — Auxiliares
- Uploads (`/upload/*`)
- Estimation (`/estimation/*`)
- Session/Chat (`/session`, `/chat`)

Ver detalle en: `11_functional-flow/functional_flow_report.md`.

---

## 6) Riesgos técnicos prioritarios (para no romper prod)

1) **Autorización inconsistente**: el frontend consume rutas críticas sin `authFetch` (riesgo si backend no valida auth).  
2) **Secretos hardcodeados** en scripts y conexión DB (3 hallazgos).  
3) **Dependencias infra sin evidencia de HA** (Postgres/Redis/Azure SQL).  
4) **Operaciones destructivas**: `DELETE /config/pis/{piId}`, `DELETE /backlog/*` (requiere auditoría/controles).

---

## 7) Preguntas KT recomendadas (Día 1 - Día 3)

### Negocio / reglas
- ¿Qué significa “PI activo”? ¿pueden existir múltiples PIs en paralelo?
- ¿Cómo se calculan fechas en planificación (`fecha_finalizacion`, `etc`, reservas)?
- ¿Reglas SLA y escalamiento: pausas, reinicios, condiciones?

### Seguridad / acceso
- ¿Qué roles existen realmente más allá de `superuser`/`user`?
- ¿AuthZ se valida server-side en backlog/upload/chat?

### Operación
- ¿Dónde corre en prod (URL FE/BE) y cómo se despliega?
- ¿Qué DB es source of truth (Postgres vs Azure SQL)? ¿qué tablas viven en cada una?
- ¿Qué herramienta de observabilidad se usa y qué dashboards son críticos?

---

## 8) “Cómo empezar” (pasos prácticos)

1) Confirmar accesos (sección 3).  
2) Obtener URLs reales de ambientes (dev/qa/prod): FE + API.  
3) Validar que el backend expone OpenAPI (`/openapi.json`) y versionarlo.  
4) Ejecutar smoke test por flujo:
   - Login
   - Listar PIs y PI activo
   - Listar capacidad
   - Listar backlog de un módulo
   - Consultar dashboard

---

## 9) Enlaces a outputs del run

- `06_access-readiness/access_readiness_report.md`
- `07_app-inventory/application_inventory_report.md`
- `08_dependency-mapping/dependency_map_report.md`
- `09_api-integration/api_integration_report.md`
- `10_business-capability/business_capability_report.md`
- `11_functional-flow/functional_flow_report.md`
- `12_knowledge-mgmt/knowledge_graph.md`

---

*Generado por Agencia de Transición — 2026-05-18*
