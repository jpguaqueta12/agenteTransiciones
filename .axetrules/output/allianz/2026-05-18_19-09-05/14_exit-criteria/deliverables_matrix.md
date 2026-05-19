# ✅ Exit Criteria — Deliverables Matrix — allianz

**Proyecto:** allianz  
**Fase:** Exit Criteria  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Propósito

Esta matriz define **entregables obligatorios**, su **gate** asociado y el **estado** actual según la evidencia disponible en el RUN_DIR.

> Nota: Este run se generó con evidencia estática (outputs CORE + extendidos).  
> Algunos entregables requieren confirmación operacional (accesos, URLs reales, observabilidad, secret manager).

---

## 🧭 Gates de transición (resumen)

- **Gate 0 — Inicio**: alcance, equipo, plan base
- **Gate 1 — Discovery Completo / Día 1 Ready**: inventario + accesos + dependencias
- **Gate 2 — Comprensión Técnica**: stack, arquitectura, seguridad, APIs, dependencias
- **Gate 3 — Comprensión de Negocio**: capacidades + flujos + KT validado + preguntas P1 cerradas
- **Gate 4 — Operación Supervisada**: runbooks probados en runtime + incidentes operados
- **Gate 5 — Aceptación Final**: firma, RAID estabilizado, deliverables aprobados

---

## 📦 Matriz de entregables

**Convenciones de estado:**
- **Pendiente**: no existe output / sin evidencia
- **Listo**: existe output con contenido
- **En riesgo**: existe output pero con bloqueos/gaps P1
- **Aprobado**: requiere confirmación explícita (cliente/Delivery) — no se asume en este run

| ID | Entregable | Gate | Responsable | Estado | Evidencia / Archivo |
|---|---|---:|---|---|---|
| D-00 | Detección de plataforma documentada | 1 | Detector (CORE) | Listo | `00_deteccion/platform_detection.md` |
| D-01 | Discovery de repos (scope técnico inicial) | 1 | Scout (CORE) | Listo | `01_scout/projects_discovered.md` |
| D-02 | Discovery de ramas (rama analizada) | 1 | Scout (CORE) | Listo | `01_scout/branches_discovered.md` |
| D-03 | Stack + score de calidad | 2 | Analyst (CORE) | En riesgo | `02_analyst/stack_quality_report.md` (calidad 42/100; sin README/lint/.env.example) |
| D-04 | Arquitectura (patrón + diagrama) | 2 | Architect (CORE) | En riesgo | `03_architect/architecture_report.md` (confianza baja) |
| D-05 | Auditoría de secretos/CVEs | 2 | Auditor (CORE) | En riesgo | `04_auditor/security_report.md` (3 secretos) |
| D-06 | Roadmap de transición | 2 | Strategist (CORE) | Listo | `05_strategist/TRANSITION_ROADMAP.md` |
| D-07 | Access Readiness (Día 1) | 1 | Access Readiness | En riesgo | `06_access-readiness/access_readiness_report.md` (DB/obs/secret manager no evidenciados) |
| D-08 | Inventario real de aplicaciones | 1 | App Inventory | En riesgo | `07_app-inventory/application_inventory_report.md` (inventario parcial por evidencia) |
| D-09 | Mapa de dependencias + SPOFs | 1 | Dependency Mapping | En riesgo | `08_dependency-mapping/dependency_map_report.md` (SPOFs/HA no evidenciados) |
| D-10 | Catálogo de APIs e integraciones | 2 | API Integration | En riesgo | `09_api-integration/api_integration_report.md` (OpenAPI no evidenciada; endpoints sin auth en cliente) |
| D-11 | Mapa de capacidades de negocio | 3 | Business Capability | Listo | `10_business-capability/business_capability_report.md` |
| D-12 | Flujos funcionales críticos (happy path + excepciones) | 3 | Functional Flow | En riesgo | `11_functional-flow/functional_flow_report.md` (parcial/inferido desde frontend) |
| D-13 | Knowledge Graph + onboarding guide | 3 | Knowledge Mgmt | En riesgo | `12_knowledge-mgmt/knowledge_graph.md`, `12_knowledge-mgmt/onboarding_guide.md` (faltan URLs/owners/runtime) |
| D-14 | Runbooks operativos (Día 1) | 4 | Knowledge Mgmt | En riesgo | `12_knowledge-mgmt/runbooks/runbook_operaciones.md` (sin evidencias runtime/owners) |
| D-15 | Acta KT Session 1 | 3 | KT Capture | Pendiente | `13_kt-capture/kt_session_1_acta.md` (marcada PENDIENTE) |
| D-16 | KT Open Questions | 3 | KT Capture | En riesgo | `13_kt-capture/open_questions.md` (P1 abiertas) |
| D-17 | KT Backlog / acciones de cierre | 3 | KT Capture | En riesgo | `13_kt-capture/kt_backlog.md` (P1 Día 1) |
| D-18 | Matriz de deliverables (este documento) | 5 | Exit Criteria | Listo | `14_exit-criteria/deliverables_matrix.md` |
| D-19 | Gate status report (este documento) | 5 | Exit Criteria | Listo | `14_exit-criteria/gate_status_report.md` |
| D-20 | RAID Register | 5 | Command & Control | Pendiente | `15_command-control/raid_register.md` |
| D-21 | Executive Dashboard | 5 | Command & Control | Pendiente | `15_command-control/executive_dashboard.md` |
| D-22 | Informe consolidado (Markdown) | 5 | Report Generator | Pendiente | `00_summary/CONSOLIDATED_REPORT.md` |
| D-23 | Informe Word (.docx) | 5 | Report Generator | Pendiente | `00_summary/INFORME_TRANSICION_ALLIANZ.docx` |

---

## 🧱 Bloqueantes típicos para “Aprobado” (evidencia requerida)

Para pasar de **Listo/En riesgo → Aprobado** se requiere normalmente:

- Capturas/links de accesos: DBs (Postgres/Redis/Azure SQL), observabilidad, secret manager
- URLs reales FE/BE por ambiente (dev/qa/prod)
- Confirmación de enforcement AuthZ server-side en endpoints críticos (backlog/uploads/chat/session)
- Evidencia de rotación/remoción de secretos (PR mergeado + verificación runtime)
- OpenAPI publicado (`/openapi.json`) y versionado

---

*Generado por Agencia de Transición — 2026-05-18*
