# 🧾 Exit Criteria — Gate Status Report — allianz

**Proyecto:** allianz  
**Fase:** Exit Criteria  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 1) Resumen ejecutivo

**Gate actual recomendado:** **Gate 2 — Comprensión Técnica**  
**Estado:** **🟡 EN RIESGO** (la evidencia existe, pero hay bloqueantes P1 que impiden operación segura Día 1 y aprobación de gates posteriores)

> Nota: el run se basa en evidencia estática (código + outputs CORE/extendidos).  
> “Aprobado” requiere evidencia operacional (accesos/URLs/runtime) y cierre de P1.

---

## 2) Semáforo por Gate

| Gate | Nombre | Estado | Motivo principal |
|---:|---|---|---|
| 0 | Inicio | 🟡 En progreso | No hay evidencia de kickoff/alcance/equipo/plan firmado (fuera de repo) |
| 1 | Discovery Completo / Día 1 Ready | 🔴 Bloqueado | Accesos a DBs/observabilidad/secret manager no evidenciados |
| 2 | Comprensión Técnica | 🟡 En riesgo | Stack/arquitectura/auditoría listos, pero 3 secretos + gaps auth/openapi |
| 3 | Comprensión de Negocio | 🟡 En riesgo | Capacidades y flujos inferidos; KT pendiente; P1 abiertas |
| 4 | Operación Supervisada | ⚪ No iniciado | Sin evidencia de incidentes operados ni runbooks validados en runtime |
| 5 | Aceptación Final | ⚪ No iniciado | RAID y aprobación formal pendientes; informe final aún no generado |

---

## 3) Bloqueantes (P1) para Gate 1 / Día 1 Ready

| ID | Bloqueante | Impacto | Evidencia |
|---|---|---|---|
| B-01 | **Acceso a DBs** (Postgres / Redis / Azure SQL): hosts, roles, credenciales mínimas | Sin DB no hay operación; diagnóstico imposible | `06_access-readiness/access_readiness_report.md` |
| B-02 | **Acceso a observabilidad** (logs/métricas/alerting) | Operación insegura; MTTR alto | `06_access-readiness/access_readiness_report.md` |
| B-03 | **Acceso a secret manager + rotación** | Riesgo de compromiso; incumplimiento | `04_auditor/security_report.md` + `06_access-readiness/access_readiness_report.md` |

---

## 4) Riesgos técnicos clave que impiden “Aprobado” de Gate 2

| Riesgo | Severidad | Qué falta | Evidencia |
|---|---:|---|---|
| Secretos hardcodeados detectados (3) | 🔴 | PR con remoción + rotación + verificación runtime | `04_auditor/security_report.md` |
| AuthZ inconsistente / cliente consume endpoints sin token | 🔴 | Confirmar enforcement server-side o capa perimetral (gateway/WAF) | `09_api-integration/api_integration_report.md`, `11_functional-flow/functional_flow_report.md` |
| Contrato OpenAPI no publicado | 🟠 | Publicar `/openapi.json` y versionarlo | `09_api-integration/api_integration_report.md` |
| Arquitectura con baja confianza | 🟡 | Validar con dueños; documentar ADRs/diagrama real | `03_architect/architecture_report.md` |

---

## 5) Criterio de “Ready to Advance” (acciones mínimas)

Para pasar de **🟡/🔴 → ✅ Aprobado**:

### Gate 1 — Día 1 Ready (P1)
- [ ] Entregar accesos a Postgres/Redis/Azure SQL (prueba de conexión)  
- [ ] Entregar accesos a observabilidad (logs + dashboards + alerting)  
- [ ] Identificar secret manager + permisos mínimos + proceso rotación  

### Gate 2 — Comprensión técnica (P1)
- [ ] Rotar y remover los 3 secretos (PR mergeado)  
- [ ] Confirmar enforcement AuthZ server-side en `/backlog/*` `/upload/*` `/chat` `/session`  
- [ ] Publicar OpenAPI (`/openapi.json`) y versionarlo  

### Gate 3 — Negocio
- [ ] Ejecutar KT Session 1 (acta completa)  
- [ ] Cerrar preguntas P1 de `13_kt-capture/open_questions.md`  

---

## 6) Referencias (outputs)

- `14_exit-criteria/deliverables_matrix.md`
- `06_access-readiness/access_readiness_report.md`
- `04_auditor/security_report.md`
- `09_api-integration/api_integration_report.md`
- `13_kt-capture/open_questions.md`
- `13_kt-capture/kt_backlog.md`

---

*Generado por Agencia de Transición — 2026-05-18*
