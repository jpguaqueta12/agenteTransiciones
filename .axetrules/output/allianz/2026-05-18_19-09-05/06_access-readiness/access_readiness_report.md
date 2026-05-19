# 🔑 Access Readiness — Accesos Día 1

**Proyecto:** allianz  
**Fase:** Access Readiness  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Resumen Ejecutivo

Este reporte valida la **preparación de accesos** para que el equipo entrante pueda operar el servicio desde el **Día 1** sin bloqueos.

**Resultado:** 🟡 *Parcialmente listo* — existen accesos verificables (GitHub) pero quedan **accesos no evidenciables** con la información actual (cloud, observabilidad, BD, secretos, ITSM).

> Nota: Este análisis se basa en evidencia disponible en los outputs CORE (Scout/Analyst/Architect/Auditor).  
> Para cerrar el gate “Día 1 listo” se requiere confirmación/inputs del equipo (cuentas, roles, URLs de herramientas, y pruebas de login).

---

## 🔎 Evidencia Analizada (inputs CORE)

- `01_scout/projects_discovered.md` (repositorios detectados y visibilidad)
- `01_scout/branches_discovered.md` (rama analizada)
- `02_analyst/stack_quality_report.md` (stack + CI/CD + Docker)
- `03_architect/architecture_report.md` (arquitectura y comunicaciones externas)
- `04_auditor/security_report.md` (secretos expuestos)

---

## ✅ Contexto del repositorio (verificable)

| Item | Evidencia | Estado |
|---|---|---|
| Repo principal | `jpguaqueta12/allianz` (GitHub) | ✅ Verificable |
| Rama analizada | `main` | ✅ Verificable |
| Clonado técnico | `/tmp/repo-intel/allianz@main` | ✅ Verificable |

---

## 🧩 Mapa de accesos requeridos (por categoría)

### 1) Repositorios (GitHub)

| Sistema | Acceso mínimo | Evidencia | Estado |
|---|---|---|---|
| GitHub repo `allianz` | `Read` (clone) + `Write` (push PRs) | Pipeline CORE pudo clonar con TOKEN | ✅ OK (para el token configurado) |
| GitHub org/user `jpguaqueta12` | `Metadata/Contents Read` | Descubrió 2 repos | ✅ OK |

**Riesgo:** el token usado es un **PAT personal**. Para operación real se recomienda migrar a credencial corporativa / GitHub App / Fine-grained token por repo.

---

### 2) CI/CD

| Sistema | Acceso mínimo | Evidencia | Estado |
|---|---|---|---|
| GitHub Actions | Lectura de workflows + runs | Detectado “GitHub Actions” (Analyst) | 🟡 Requiere validación (no se verificó acceso a Actions API/UI) |

**Acción sugerida:** confirmar que el equipo entrante tiene acceso a:
- `Actions` (lectura de runs, logs, artifacts)
- `Secrets/Variables` (solo si corresponde por rol)

---

### 3) Infraestructura / Runtime

| Sistema | Acceso mínimo | Evidencia | Estado |
|---|---|---|---|
| Docker / Docker registry | Pull de imágenes (si aplica) | Detectado “Docker” (Analyst) | 🟡 Requiere validación |
| Orquestador (K8s / VM / PaaS) | Lectura de estado + reinicios controlados | No hay evidencia directa en outputs | ⚪ Desconocido |

---

### 4) Bases de datos y storage

El stack reporta **PostgreSQL, Redis, SQL Server**.

| Sistema | Acceso mínimo | Evidencia | Estado |
|---|---|---|---|
| PostgreSQL | Usuario de lectura + esquema | Detectado en stack (Analyst) | 🔴 No evidenciado |
| Redis | Lectura/diagnóstico + flush limitado (según políticas) | Detectado en stack (Analyst) | 🔴 No evidenciado |
| SQL Server / Azure SQL | Lectura/diagnóstico | Detectado en stack (Analyst) | 🔴 No evidenciado |

---

### 5) Observabilidad

| Sistema | Acceso mínimo | Evidencia | Estado |
|---|---|---|---|
| Logs centralizados | consulta + export | No hay evidencia directa | 🔴 No evidenciado |
| Métricas/APM | lectura dashboards + traces | No hay evidencia directa | 🔴 No evidenciado |
| Alerting/on-call | ver reglas + ack | No hay evidencia directa | 🔴 No evidenciado |

---

### 6) Gestión de secretos (CRÍTICO)

El Auditor detectó **3 secretos expuestos en código** (passwords genéricos). Esto implica que el equipo entrante necesita:

| Sistema | Acceso mínimo | Evidencia | Estado |
|---|---|---|---|
| Gestor de secretos (Vault/ASM/AKV/etc.) | lectura (runtime) + rotación (admin limitado) | No hay evidencia del gestor | 🔴 No evidenciado |
| Repositorio | permisos para remover secretos y hacer PR | Token pudo clonar | ✅ OK |

---

### 7) ITSM / Ticketing / Comunicación

| Sistema | Acceso mínimo | Evidencia | Estado |
|---|---|---|---|
| Jira/ServiceNow/Azure Boards | lectura + creación de tickets | No hay evidencia | ⚪ Desconocido |
| Canales de comunicación (Teams/Slack) | acceso a canales del servicio | No hay evidencia | ⚪ Desconocido |
| Wiki/Docs (Confluence/SharePoint) | lectura + edición | No hay evidencia | ⚪ Desconocido |

---

## 🚫 Bloqueos Día 1 (según evidencia disponible)

> Un “bloqueo” aquí significa: **no se puede confirmar con evidencia** que el acceso exista.

| Criticidad | Bloqueo | Por qué | Fecha límite |
|---|---|---|---|
| 🔴 BLOQUEANTE | Acceso a PostgreSQL/Redis/SQL Server | DBs detectadas pero sin credenciales/hosts/roles evidenciados | Día 1 |
| 🔴 BLOQUEANTE | Acceso a gestor de secretos | Hay secretos que deben rotarse; no se identifica el sistema de secretos | Día 1 |
| 🔴 BLOQUEANTE | Acceso a observabilidad (logs + métricas) | Sin observabilidad no hay operación segura | Día 1 |
| 🟠 NECESARIO | Acceso a GitHub Actions (runs/logs/artifacts) | Hay CI/CD; se requiere para investigar fallos de pipeline | Semana 1 |
| 🟡 DESEABLE | Acceso a registry / entorno de despliegue | Docker detectado; se requiere para operar despliegues | Semana 2 |

---

## 🛠️ Solicitudes de remediación (lista accionable)

| ID | Sistema | Acción concreta | Responsable sugerido | Criticidad | Evidencia requerida |
|---|---|---|---|---|---|
| AR-01 | DBs (Postgres/Redis/SQL Server) | Entregar endpoints + credenciales (mínimo read-only) + rotación programada | Equipo plataforma / DBA | 🔴 | Prueba de conexión + rol asignado |
| AR-02 | Secret Manager | Identificar gestor (Vault/AKV/ASM/etc.) + dar permisos a equipo entrante | Seguridad/Plataforma | 🔴 | Login exitoso + policy/role |
| AR-03 | Observabilidad | Proveer acceso a dashboards + búsqueda de logs + alerting | SRE/Observability | 🔴 | Captura de pantalla + grupo/role |
| AR-04 | GitHub Actions | Acceso al repo con permisos para ver logs/artifacts | Repo Admin | 🟠 | Acceso UI Actions + descarga artifact |
| AR-05 | Flujo de rotación de secretos | Rotar los 3 secretos detectados y eliminar del código | Dev lead + Sec | 🔴 | PR mergeado + verificación en runtime |

---

## ✅ Checklist Día 1 (para cerrar gate)

- [ ] Acceso de lectura/escritura al repo GitHub (confirmado por usuario, no solo por token local)
- [ ] Acceso a CI/CD (GitHub Actions: runs, logs, artifacts)
- [ ] Acceso a runtime/infra (K8s/VM/PaaS) con permisos mínimos
- [ ] Acceso a bases de datos (Postgres/Redis/SQL Server) con credenciales y roles documentados
- [ ] Acceso a observabilidad (logs, métricas, alerting)
- [ ] Acceso a gestor de secretos + proceso de rotación operativo
- [ ] Rotación de secretos detectados por Auditor (3 hallazgos) y PR mergeado

---

## Conclusión

Con la evidencia actual, el repositorio y el pipeline de análisis son accesibles; sin embargo, **faltan pruebas/inputs** para confirmar accesos operativos a infraestructura, bases de datos, observabilidad y gestión de secretos. Esto debe resolverse antes de declarar “Día 1 listo”.

---

*Generado por Agencia de Transición — 2026-05-18*
