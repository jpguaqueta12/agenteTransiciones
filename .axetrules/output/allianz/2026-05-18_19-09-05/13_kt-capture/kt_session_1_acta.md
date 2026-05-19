# 🎙️ KT Session 1 — Acta (PENDIENTE) — allianz

**Proyecto:** allianz  
**Fase:** KT Capture  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Estado

**PENDIENTE DE REALIZAR** — no se recibieron notas/transcripción KT del usuario en esta ejecución.

> Este documento provee una **estructura de acta** y una lista de temas/preguntas sugeridas basadas en evidencia técnica (outputs CORE + extendidos).  
> Completar con participantes, decisiones y evidencias de operación (URLs, owners, SLAs, entornos).

---

## 1) Metadatos de la sesión

- **Sesión #:** 1  
- **Duración:** _TBD_  
- **Fecha/Hora:** _TBD_  
- **Modalidad:** _TBD_ (Teams/Meet/Presencial)  
- **Participantes (equipo saliente):** _TBD_  
- **Participantes (equipo entrante):** _TBD_  
- **Objetivo:** Transferencia de conocimiento para operar el sistema de planificación (PI, capacidad, backlog, SLA/dashboards, uploads, IA/chat).

---

## 2) Agenda sugerida (90 min)

1. Contexto de negocio: qué problema resuelve y quiénes lo usan (10m)  
2. Arquitectura general: FE/BE + dependencias (15m)  
3. Datos y DBs: Postgres vs Azure SQL; ownership; backups (15m)  
4. Seguridad: AuthN/AuthZ real; rotación de secretos; roles (15m)  
5. Flujos críticos: PI → Capacidad → Backlog → SLA/Dashboards (20m)  
6. Operación: despliegue, observabilidad, on-call, runbooks (15m)  

---

## 3) Resumen del sistema (para alinear lenguaje)

Basado en outputs:

- Repo: `jpguaqueta12/allianz` (GitHub)  
- Componentes:
  - `front-planificacion` (React + Vite + TS)  
  - `back-planificacion` (FastAPI)  
- Dependencias: PostgreSQL, SQL Server/Azure SQL, Redis, Azure Identity, LLM provider  
- Flujos principales (inferidos): Auth, Config PI, Capacidad, Backlog, SLA/Alertas/Dashboards, Upload Excel, Estimación IA + export Word, Session/Chat  
- Riesgos críticos:
  - Secretos hardcodeados (3 hallazgos)  
  - Autorización potencialmente inconsistente (cliente usa `fetch` sin token en backlog/chat)  
  - Accesos Día 1 no evidenciados (DBs/observabilidad/secret manager)  

---

## 4) Decisiones a capturar (plantilla)

> Completar durante la sesión.

| ID | Decisión | Contexto | Alternativas | Responsable | Fecha | Evidencia |
|---|---|---|---|---|---|---|
| DEC-KT-01 | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

---

## 5) Flujos discutidos (plantilla)

| Flujo | Descripción oral | Sistemas mencionados | Validado con código | Delta vs evidencia |
|---|---|---|---|---|
| Auth | _TBD_ | FE/BE | No | _TBD_ |
| PI | _TBD_ | FE/BE/DB | No | _TBD_ |
| Capacidad | _TBD_ | FE/BE/DB | No | _TBD_ |
| Backlog | _TBD_ | FE/BE/DB | No | _TBD_ |
| SLA/Dashboards | _TBD_ | FE/BE/DB | No | _TBD_ |
| Upload Excel | _TBD_ | FE/BE | No | _TBD_ |
| Estimation/Word | _TBD_ | FE/BE/LLM | No | _TBD_ |
| Session/Chat | _TBD_ | FE/BE/LLM | No | _TBD_ |

---

## 6) Riesgos verbalizados (captura durante sesión)

| Riesgo | Contexto | Probabilidad (A/M/B) | Impacto (A/M/B) | Acción sugerida | Evidencia |
|---|---|---|---|---|---|
| _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

---

## 7) Temas KT prioritarios (inferidos de la evidencia)

### KT-P1 — Seguridad y acceso (bloqueante)
1. Confirmar si **AuthZ se valida server-side** en endpoints críticos:
   - `/api/v1/backlog/*`
   - `/api/v1/upload/*`
   - `/api/v1/chat`, `/api/v1/session`
2. Confirmar modelo de roles: ¿solo `superuser`/`user`? ¿hay scopes/permisos por módulo?
3. Rotación y eliminación de secretos detectados (3):
   - `back-planificacion/app/db/connection.py`
   - `back-planificacion/scripts/seed_azure_sql.py`
   - `back-planificacion/scripts/test_sql_connection.py`
4. ¿Qué Secret Manager se usa? (AKV/Vault/ASM/otro) y proceso de rotación.

### KT-P1 — Datos y dependencias (bloqueante)
1. ¿Cuál es el **source of truth**? (Postgres vs Azure SQL)  
2. Esquemas principales (tablas core) y ownership de cada DB.  
3. Backups, retención, restore, migraciones (alembic/ddl manual).  
4. Redis: ¿qué guarda realmente? (cache, sesión, locks) + TTLs.

### KT-P1 — Operación en runtime (bloqueante)
1. URLs reales FE/BE por ambiente (dev/qa/prod).  
2. Dónde corre: K8s/VM/PaaS; cómo se despliega; pipeline (GitHub Actions u otro).  
3. Observabilidad: logs/métricas/tracing; dashboards críticos; alertas; on-call.

### KT-P2 — Reglas de negocio core
1. Definición exacta de PI activo y reglas de activación.  
2. Reglas de capacidad (horas, reservas, seniority, sincronización).  
3. Reglas de backlog: estados, validaciones por módulo, concurrencia.  
4. SLA y escalamiento: pausas, reinicios, fechas, cálculo.

### KT-P3 — Flujos auxiliares
1. Upload Excel: formatos soportados, columnas, validaciones, límites.  
2. Estimation IA: proveedores/modelos, timeouts, costos, criterios de uso.  
3. Export Word: plantillas, datos sensibles, PII.

---

## 8) Evidencias a solicitar al equipo saliente (checklist)

- [ ] Capturas/links de:
  - [ ] GitHub Actions (runs, secrets/vars si aplica)
  - [ ] Observabilidad (logs + dashboard + alertas)
  - [ ] Secret manager (path/policies)
- [ ] URLs dev/qa/prod FE/BE
- [ ] Documentación de DBs (hosts, owners, backups)
- [ ] OpenAPI del backend (`/openapi.json`) o repositorio con contrato
- [ ] Diagrama actualizado (si existe) y ADRs relevantes

---

## 9) Output relacionados (referencia)

- `11_functional-flow/functional_flow_report.md`
- `12_knowledge-mgmt/onboarding_guide.md`
- `12_knowledge-mgmt/runbooks/runbook_operaciones.md`
- `04_auditor/security_report.md`
- `06_access-readiness/access_readiness_report.md`

---

*Generado por Agencia de Transición — 2026-05-18*
