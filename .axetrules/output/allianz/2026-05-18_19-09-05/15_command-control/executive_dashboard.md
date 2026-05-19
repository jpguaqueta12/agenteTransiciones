# 📊 Executive Dashboard — allianz

**Proyecto:** allianz  
**Fase:** Command & Control  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 1) Estado general (semaforización)

**Gate actual recomendado:** **Gate 2 — Comprensión Técnica**  
**Estado global:** **🟡 ATENCIÓN / EN RIESGO**

**Racional:** existe evidencia técnica base (stack/arquitectura/seguridad/roadmap), pero hay bloqueantes operativos P1 para “Día 1 Ready” y riesgos críticos sin cierre (secretos + auth + OpenAPI).

---

## 2) Semáforo por Gate (0→5)

| Gate | Estado | Qué significa en este run |
|---:|---|---|
| 0 | 🟡 En progreso | Kickoff/alcance/equipo/plan no evidenciados en outputs |
| 1 | 🔴 Bloqueado | Accesos a DBs + observabilidad + secret manager no confirmados |
| 2 | 🟡 En riesgo | 3 secretos + posible AuthZ inconsistente + OpenAPI no publicado |
| 3 | 🟡 En riesgo | Capacidades y flujos inferidos; KT pendiente; P1 abiertas |
| 4 | ⚪ No iniciado | Sin operación supervisada ni validación runtime de runbooks |
| 5 | ⚪ No iniciado | Informe final Word no generado; falta aprobación/firmas |

---

## 3) Top 5 riesgos (acción ejecutiva requerida)

| Rank | Riesgo | Severidad | Por qué importa | Acción inmediata |
|---:|---|---|---|---|
| 1 | Secretos hardcodeados (3) | 🔴 Crítico | Compromete DB/infra; bloqueo compliance | Rotar y remover (PR Día 1) |
| 2 | Endpoints críticos consumidos sin token | 🔴 Crítico | Posible exposición de backlog/uploads/chat | Validar AuthZ server-side / WAF |
| 3 | Acceso a DBs no evidenciado | 🔴 Crítico | Sin DB no hay operación/diagnóstico | Entregar endpoints+roles+prueba |
| 4 | Observabilidad no evidenciada | 🔴 Crítico | MTTR alto y operación insegura | Entregar acceso dashboards+logs |
| 5 | OpenAPI no publicado | 🟠 Alto | Gobierno/API contract débil; riesgo de cambios | Publicar `/openapi.json` + versionar |

Fuente ampliada: `15_command-control/raid_register.md`.

---

## 4) Bloqueantes P1 (Día 1 Ready)

| ID | Bloqueante | Owner sugerido | Fecha |
|---|---|---|---|
| P1-01 | Acceso Postgres/Redis/Azure SQL (hosts+roles+credenciales mínimas) | Plataforma/DBA | Día 1 |
| P1-02 | Acceso a observabilidad (logs+métricas+alerting) | SRE/Observability | Día 1 |
| P1-03 | Identificar secret manager + permisos mínimos + proceso rotación | Sec/Plataforma | Día 1 |
| P1-04 | Rotar/remover 3 secretos hardcodeados | Backend Lead + Sec | Día 1 |
| P1-05 | Confirmar enforcement AuthZ server-side en backlog/upload/chat/session | Backend Lead + Sec | Día 1 |

---

## 5) Próximas decisiones (DEC) a tomar

| DEC | Decisión | Fecha objetivo | Impacto |
|---|---|---|---|
| DEC-01 | Estrategia de secretos y rotación (AKV vs Vault vs ASM; identidad) | Día 1 | Desbloquea Gates 1/2 |
| DEC-02 | Modelo de seguridad para endpoints críticos (backend vs gateway/WAF) | Día 1 | Reduce riesgo R-02 |
| DEC-03 | Source of truth de datos (Postgres vs Azure SQL) + ownership/backups | Semana 1 | Afecta continuidad y roadmap |

---

## 6) KPIs sugeridos para seguimiento (semanal)

- **# P1 abiertos:** meta 0 en Día 1 + Semana 1  
- **Tiempo a “Día 1 Ready” (Gate 1):** meta ≤ 1 día  
- **Riesgos score ≥ 6:** meta ≤ 2 en Semana 1  
- **Evidencias operativas agregadas:** accesos DB/obs/secret manager + URLs FE/BE  
- **Estado OpenAPI:** publicado + versionado (sí/no)

---

## 7) Evidencia (archivos clave)

- `14_exit-criteria/gate_status_report.md`
- `14_exit-criteria/deliverables_matrix.md`
- `06_access-readiness/access_readiness_report.md`
- `04_auditor/security_report.md`
- `09_api-integration/api_integration_report.md`
- `15_command-control/raid_register.md`

---

*Generado por Agencia de Transición — 2026-05-18*
