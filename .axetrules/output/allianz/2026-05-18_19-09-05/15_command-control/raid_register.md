# 🧾 Command & Control — RAID Register — allianz

**Proyecto:** allianz  
**Fase:** Command & Control  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Propósito

Centralizar el registro **RAID** de la transición:

- **Riesgos** (Risk)
- **Acciones** (Actions)
- **Issues** (Incidents / Issues)
- **Dependencias** (Dependencies)

Este RAID se basa en evidencia estática del repo y outputs del run. Debe mantenerse vivo durante la transición.

---

## 0) Resumen (situación actual)

- **Gate recomendado:** Gate 2 — Comprensión Técnica (**🟡 En riesgo**)  
- **Bloqueantes Día 1 (P1):** accesos DBs + observabilidad + secret manager/rotación  
- **Riesgos críticos inmediatos:** secretos hardcodeados + posible AuthZ inconsistente + contrato OpenAPI no publicado

---

## 1) R — Risks (Riesgos)

**Escala:** Probabilidad (1–3) × Impacto (1–3) = Score (1–9).  
Se consideran **alto riesgo** los score ≥ 6.

| ID | Categoría | Riesgo | Prob. | Impacto | Score | Mitigación | Responsable | Estado | Fuente |
|---|---|---|---:|---:|---:|---|---|---|---|
| R-01 | Seguridad | **Secretos hardcodeados** (3 hallazgos) en repo (conexión DB/scripts) | 3 | 3 | 9 | Remover secretos del código + rotar credenciales en secret manager + invalidar credenciales expuestas | Backend Lead + Sec | Abierto | `04_auditor/security_report.md` |
| R-02 | Seguridad | **AuthZ potencialmente inconsistente**: cliente consume `/backlog/*`, `/upload/*`, `/chat`, `/session` sin token (riesgo si backend no valida server-side) | 3 | 3 | 9 | Confirmar enforcement server-side o compensación perimetral (gateway/WAF/ACL); alinear FE para usar `authFetch` donde aplique | Backend Lead + Sec | Abierto | `09_api-integration/api_integration_report.md`, `11_functional-flow/functional_flow_report.md` |
| R-03 | Operación | **No evidencia de accesos a DBs** (Postgres/Redis/Azure SQL) para el equipo entrante | 3 | 3 | 9 | Entregar endpoints + roles + credenciales mínimas (read/diag) + prueba de conexión | Plataforma/DBA | Abierto | `06_access-readiness/access_readiness_report.md` |
| R-04 | Operación | **Sin observabilidad** evidenciada (logs/métricas/alerting) | 3 | 3 | 9 | Provisionar accesos a herramienta de observabilidad + dashboards críticos + alertas y on-call | SRE/Observability | Abierto | `06_access-readiness/access_readiness_report.md` |
| R-05 | Seguridad / Operación | **Secret manager desconocido** / rotación no evidenciada | 3 | 3 | 9 | Identificar gestor (AKV/Vault/ASM), dar permisos mínimos, ejecutar rotación y registrar evidencia | Sec/Plataforma | Abierto | `06_access-readiness/access_readiness_report.md`, `04_auditor/security_report.md` |
| R-06 | API / Gobierno | **OpenAPI no publicado/versionado** (contrato implícito) | 2 | 2 | 4 | Publicar `/openapi.json` + versionar `openapi.yaml` + convención de breaking changes | Backend Lead | Abierto | `09_api-integration/api_integration_report.md` |
| R-07 | Arquitectura | **Arquitectura con baja confianza** (patrón inferido, falta validación con dueños/ADRs) | 2 | 2 | 4 | Validar diagrama y decisiones con owners; crear ADRs; actualizar docs | Arquitecto/Tech Lead | Abierto | `03_architect/architecture_report.md` |
| R-08 | Continuidad | **SPOFs potenciales**: Postgres/Redis/Azure SQL sin evidencia de HA/failover | 2 | 3 | 6 | Documentar HA/tiers/replicas, RPO/RTO, backups/restore probados | Plataforma/DBA | Abierto | `08_dependency-mapping/dependency_map_report.md` |
| R-09 | Costos / Robustez | Dependencia externa LLM (chat/estimación): **rate limits/costos/latencia** | 2 | 2 | 4 | Rate limiting, timeouts, métricas de costo, cuotas por usuario, fallback | Backend Lead | Abierto | `08_dependency-mapping/dependency_map_report.md` |

---

## 2) A — Actions (Acciones)

**Convención de prioridad:** P1 (Día 1) / P2 (Semana 1) / P3 (Semana 2+)

| ID | Prioridad | Acción | Responsable | Fecha límite | Estado | Bloqueos | Dependencias | Evidencia objetivo |
|---|---|---|---|---|---|---|---|---|
| A-01 | P1 | Rotar y remover los 3 secretos hardcodeados (PR mergeado) | Backend Lead + Sec | Día 1 | Pendiente | Acceso a secret manager | D-05 | `04_auditor/security_report.md` + PR |
| A-02 | P1 | Confirmar enforcement AuthZ server-side en endpoints críticos (`/backlog/*`, `/upload/*`, `/chat`, `/session`) | Backend Lead + Sec | Día 1 | Pendiente | Falta KT/owners | D-10/D-12 | Evidencia: código + pruebas (401/403) |
| A-03 | P1 | Entregar accesos operativos a Postgres/Redis/Azure SQL + prueba conexión | Plataforma/DBA | Día 1 | Pendiente | Gestión de credenciales | D-07 | Capturas/outputs de conexión |
| A-04 | P1 | Entregar accesos a observabilidad (logs/métricas/alerting) + dashboards críticos | SRE/Observability | Día 1 | Pendiente | Provisionamiento cuentas | D-07 | Links + capturas |
| A-05 | P2 | Publicar OpenAPI (`/openapi.json`) y versionarlo | Backend Lead | Semana 1 | Pendiente | Confirmar routers | D-10 | Archivo `openapi.yaml`/endpoint |
| A-06 | P2 | Documentar URLs reales FE/BE por ambiente + deploy method (pipeline) | DevOps | Semana 1 | Pendiente | Falta info runtime | D-13 | Runbook/onboarding actualizado |
| A-07 | P2 | Definir source of truth de datos (Postgres vs Azure SQL), ownership y backups/restore | Arquitecto + DBA | Semana 1 | Pendiente | KT con dueños DB | D-09 | Documento de decisión + RPO/RTO |
| A-08 | P3 | Implementar rate limiting/cuotas para chat/estimación IA | Backend Lead | Semana 2 | Pendiente | Definir políticas | R-09 | Middleware + métricas |
| A-09 | P3 | Completar runbooks con owners reales, URLs herramientas, procedimientos on-call | SRE + Delivery | Semana 2 | Pendiente | Falta owners | D-14 | Runbook actualizado |

---

## 3) I — Issues (Incidencias / Issues)

> Nota: en este run no hay evidencia de incidentes reales. Se registran **issues potenciales** que deben convertirse en incidentes si se materializan en runtime.

| ID | Severidad | Issue | Impacto | Fecha apertura | Responsable | Estado | Resolución | Fuente |
|---|---|---|---|---|---|---|---|---|
| I-01 | Crítica | Posible exposición de endpoints críticos sin AuthZ efectivo | Pérdida/confidencialidad/integridad de backlog/config | 2026-05-18 | Backend Lead + Sec | Abierto | TBD (validación + fix) | `09_api-integration/api_integration_report.md` |
| I-02 | Alta | Secretos expuestos en repo | Compromiso credenciales/DB | 2026-05-18 | Backend Lead + Sec | Abierto | TBD (rotación + PR) | `04_auditor/security_report.md` |

---

## 4) D — Dependencies (Dependencias)

| ID | Tipo | Dependencia | Equipo origen | Equipo destino | Fecha requerida | Estado | Impacto si no se cumple | Evidencia |
|---|---|---|---|---|---|---|---|---|
| D-DEP-01 | Externo | Accesos DBs (Postgres/Redis/Azure SQL) | Equipo entrante | Plataforma/DBA | Día 1 | Pendiente | Bloquea operación/diagnóstico | `06_access-readiness/access_readiness_report.md` |
| D-DEP-02 | Externo | Acceso observabilidad (logs/métricas/alerting) | Equipo entrante | SRE/Observability | Día 1 | Pendiente | Operación insegura (MTTR alto) | `06_access-readiness/access_readiness_report.md` |
| D-DEP-03 | Externo | Acceso a secret manager + proceso rotación | Equipo entrante | Sec/Plataforma | Día 1 | Pendiente | No se pueden rotar secretos (incumplimiento) | `06_access-readiness/access_readiness_report.md` |
| D-DEP-04 | Interno | Validación de reglas de negocio core (PI activo, capacidad, SLA/escalamiento) | Equipo entrante | PO/BA + Backend | Semana 1 | En riesgo | Bugs en planificación/backlog | `11_functional-flow/functional_flow_report.md` |

---

## 5) Próximas decisiones ejecutivas requeridas (DEC)

| ID | Decisión | Contexto | Opciones | Responsable | Fecha | Impacto | Evidencia |
|---|---|---|---|---|---|---|---|
| DEC-01 | Definir estrategia de rotación y almacenamiento de secretos | 3 secretos hardcodeados detectados | AKV vs Vault vs ASM; managed identity vs SP | Sec/Plataforma + Backend Lead | Día 1 | Desbloquea Gate 1/2 | `04_auditor/security_report.md` |
| DEC-02 | Definir enforcement de seguridad para endpoints críticos | Cliente consume endpoints sin token | Backend-only AuthZ vs gateway/WAF + backend | Backend Lead + Sec | Día 1 | Reduce riesgo R-02 | `09_api-integration/api_integration_report.md` |
| DEC-03 | Definir source of truth de datos (PG vs Azure SQL) | Dependencia dual DB detectada | PG principal vs SQL principal vs segregación por módulo | Arquitecto + DBA | Semana 1 | Afecta operación y roadmap | `08_dependency-mapping/dependency_map_report.md` |

---

*Generado por Agencia de Transición — 2026-05-18*
