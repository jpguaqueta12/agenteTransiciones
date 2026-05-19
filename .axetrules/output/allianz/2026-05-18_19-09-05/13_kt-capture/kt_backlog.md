# 🗂️ KT Backlog — Seguimiento Post-KT — allianz (PENDIENTE)

**Proyecto:** allianz  
**Fase:** KT Capture  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Estado

**PENDIENTE** — este backlog es **inferido** por evidencia técnica; debe priorizarse y asignarse durante la sesión KT.

> Objetivo: convertir preguntas abiertas y riesgos en trabajo accionable con responsables y fechas.

---

## 1) Backlog P1 — Día 1 (bloqueantes)

| ID | Tipo | Descripción | Responsable sugerido | Fecha límite | Estado | Evidencia |
|---|---|---|---|---|---|---|
| KT-01 | Seguridad | Confirmar enforcement **AuthN/AuthZ server-side** en endpoints críticos (`/backlog/*`, `/upload/*`, `/chat`, `/session`) | Backend Lead + Sec | Día 1 | Abierto | `09_api-integration/api_integration_report.md`, `11_functional-flow/functional_flow_report.md` |
| KT-02 | Accesos | Entregar accesos operativos a **Postgres / Azure SQL / Redis** (hosts, roles, credenciales mínimas) | Plataforma/DBA | Día 1 | Abierto | `06_access-readiness/access_readiness_report.md` |
| KT-03 | Observabilidad | Entregar accesos a **logs + métricas + alerting** y listar dashboards críticos | SRE/Observability | Día 1 | Abierto | `06_access-readiness/access_readiness_report.md` |
| KT-04 | Secretos | Rotar y eliminar los **3 secretos hardcodeados** detectados por Auditor | Backend Lead + Sec | Día 1 | Abierto | `04_auditor/security_report.md` |

---

## 2) Backlog P2 — Semana 1 (alta prioridad)

| ID | Tipo | Descripción | Responsable sugerido | Fecha límite | Estado | Evidencia |
|---|---|---|---|---|---|---|
| KT-05 | API/Contrato | Publicar OpenAPI del backend (`/openapi.json`) y versionarlo en repo | Backend Lead | Semana 1 | Abierto | `09_api-integration/api_integration_report.md` |
| KT-06 | Operación | Documentar **URLs reales** FE/BE (dev/qa/prod) + método de despliegue (pipeline) | DevOps | Semana 1 | Abierto | `12_knowledge-mgmt/onboarding_guide.md` |
| KT-07 | Datos | Definir **source of truth** (Postgres vs Azure SQL), módulos por DB, backups/restore | Arquitecto + DBA | Semana 1 | Abierto | `08_dependency-mapping/dependency_map_report.md`, `12_knowledge-mgmt/onboarding_guide.md` |
| KT-08 | Negocio | Documentar reglas de negocio core: PI activo, capacidad, estados backlog, SLA/escalamiento | PO/BA + Backend | Semana 1 | Abierto | `11_functional-flow/functional_flow_report.md` |

---

## 3) Backlog P3 — Semana 2 (mejora / continuidad)

| ID | Tipo | Descripción | Responsable sugerido | Fecha límite | Estado | Evidencia |
|---|---|---|---|---|---|---|
| KT-09 | Seguridad | Implementar rate limiting / cuotas para chat y estimación IA | Backend Lead | Semana 2 | Abierto | `09_api-integration/api_integration_report.md` |
| KT-10 | Uploads | Definir formatos soportados, límites y validaciones para upload Excel | Backend Lead + Negocio | Semana 2 | Abierto | `11_functional-flow/functional_flow_report.md` |
| KT-11 | Runbooks | Completar runbook con owners reales, URLs de herramientas, procedimientos de on-call | SRE + Delivery | Semana 2 | Abierto | `12_knowledge-mgmt/runbooks/runbook_operaciones.md` |

---

## 4) Definición de “Done” (DoD) sugerida por ítem

Un ítem se considera **Cerrado** cuando:
- Tiene **evidencia verificable** (link, captura, doc en repo, acceso probado)
- Tiene **owner responsable** y fecha
- Se actualiza `14_exit-criteria/` si impacta gates

---

*Generado por Agencia de Transición — 2026-05-18*
