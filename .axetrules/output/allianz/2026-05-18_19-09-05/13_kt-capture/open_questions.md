# ❓ KT — Open Questions (PENDIENTE) — allianz

**Proyecto:** allianz  
**Fase:** KT Capture  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Estado

**PENDIENTE** — no se recibieron notas/transcripción KT.  
Este documento lista preguntas abiertas críticas inferidas de la evidencia técnica disponible.

---

## 1) Preguntas P1 (bloqueantes para operación / Día 1)

### Seguridad / Accesos
1. ¿Dónde se valida **AuthZ server-side** para endpoints críticos (`/backlog/*`, `/upload/*`, `/chat`, `/session`)?  
2. ¿Existe API Gateway / WAF / ACL de red que compense endpoints consumidos sin token desde el frontend?  
3. ¿Qué secret manager se usa (AKV/Vault/ASM/otro)? ¿cuál es el proceso de rotación y quién aprueba?  
4. ¿Cómo se gestionan credenciales de DB (Postgres/Azure SQL)? ¿existen usuarios “break-glass”?  
5. ¿Hay auditoría (quién hizo qué) para operaciones destructivas (`DELETE /config/pis/{piId}`, `DELETE /backlog/*`)?  

### Datos / Persistencia
6. ¿Cuál es el **source of truth** (Postgres vs Azure SQL)? ¿qué módulo usa cada DB?  
7. ¿Existe estrategia de backups/restore por ambiente? (RPO/RTO, retención, pruebas de restore)  
8. ¿Redis se usa para sesiones, caché o locks? ¿qué llaves/TTL son críticos?  
9. ¿Cómo se hacen migraciones de esquema? (Alembic, DDL manual, scripts)  

### Runtime / Operación
10. ¿Dónde corre el backend y frontend? (K8s/VM/PaaS/CDN) + URLs dev/qa/prod  
11. ¿Qué pipeline hace el despliegue (GitHub Actions u otro)? ¿cómo se promueve a prod?  
12. ¿Qué herramienta de observabilidad se usa? (logs/métricas/tracing/alerting) y dashboards críticos  

---

## 2) Preguntas P2 (alta prioridad — semana 1)

### Reglas de negocio
13. ¿Qué significa exactamente “PI activo” y cómo se determina? ¿pueden existir múltiples?  
14. ¿Cómo se calcula capacidad (horas por día, reservas, seniority) y cómo impacta planificación?  
15. ¿Estados válidos del backlog por módulo? ¿validaciones y transiciones permitidas?  
16. Reglas SLA y escalamiento: ¿qué dispara pausa/reinicio? ¿cómo se calculan fechas?  

### API / Contratos
17. ¿Existe OpenAPI publicado (`/openapi.json`) o archivo versionado? Si no, ¿cuál es el plan?  
18. ¿Qué endpoints deben ser públicos vs privados? (dashboards/backlog/chat)  
19. ¿Rate limits / cuotas para chat/estimación IA? ¿cómo controlan costos?  

---

## 3) Preguntas P3 (mejora / continuidad)

20. Upload Excel: formatos soportados, validaciones, límites (tamaño, columnas, encoding)  
21. Export Word: plantillas, datos sensibles, PII y controles  
22. ¿Owners por módulo (PI/capacidad/backlog/SLA/dashboards/chat)? ¿on-call/escalación?  

---

## 4) Evidencia relacionada (para responder)

- `06_access-readiness/access_readiness_report.md`
- `04_auditor/security_report.md`
- `09_api-integration/api_integration_report.md`
- `11_functional-flow/functional_flow_report.md`
- `12_knowledge-mgmt/onboarding_guide.md`
- `12_knowledge-mgmt/runbooks/runbook_operaciones.md`

---

*Generado por Agencia de Transición — 2026-05-18*
