# 📦 Application Inventory — Inventario de Aplicaciones

**Proyecto:** allianz  
**Fase:** App Inventory  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Resumen Ejecutivo

Este documento construye el **inventario real** de aplicaciones/servicios asociados al alcance técnico observable desde el repositorio analizado y la evidencia CORE.

**Resultado:** ⚪ *Inventario parcial (por evidencia limitada)* — con los outputs actuales solo es posible inventariar con alta confianza:
- 1 repositorio principal analizado (`allianz`)
- señales internas de que el repositorio contiene **al menos 2 componentes** (frontend + backend) por estructura (`front-planificacion/`, `back-planificacion/`) detectada indirectamente por *entry points* y hallazgos de seguridad.

> Nota: este agente normalmente cruza también evidencias de despliegue/observabilidad/CI recientes. Aquí solo contamos con evidencia estática (código + metadatos Git).

---

## 🔎 Evidencia Analizada

- `01_scout/projects_discovered.md` (repositorios accesibles y actividad)
- `01_scout/branches_discovered.md` (rama analizada: `main`)
- `02_analyst/stack_quality_report.md` (stack: FastAPI + React/Vite; DBs: Postgres/Redis/SQL Server; Infra: Docker + GitHub Actions)
- `03_architect/architecture_report.md` (microservicio; patrón hexagonal con baja confianza; señales de HTTP/REST)
- `04_auditor/security_report.md` (3 secretos expuestos con paths en `back-planificacion/`)

---

## 🧾 Inventario detectado (técnico)

### Aplicaciones / componentes en el repositorio `allianz`

| Aplicación / Componente | Tipo | Ruta | Stack principal | Entorno (inferido) | Estado | Evidencia | En scope |
|---|---|---|---|---|---|---|---|
| back-planificacion | Backend / API | `back-planificacion/` | Python + FastAPI | Container (Docker) | 🟡 ACTIVA-LEGACY* | Entry point `back-planificacion/app/main.py` + uso de DBs + secretos detectados | Sí |
| front-planificacion | Frontend / SPA | `front-planificacion/` | React + Vite (TS/TSX) | Static/Container | 🟡 ACTIVA-LEGACY* | Frameworks detectados (React/Vite) + presencia de TSX en distribución | Sí |

\* **ACTIVA-LEGACY**: clasificación conservadora. No hay evidencia directa de despliegue, tráfico ni pipelines recientes (solo inferencia por presencia en repo). Confirmar con el equipo.

---

## 🧩 Dependencias de plataforma (no son “apps” pero sí activos operativos)

Estos activos deben considerarse parte del inventario operativo del servicio (aunque no existan como repos separados):

| Activo | Tipo | Criticidad | Evidencia | Estado de evidencia |
|---|---|---:|---|---|
| PostgreSQL | Base de datos | 🔴 Alta | Detectado por Analyst | 🔴 No evidenciado (sin host/credenciales) |
| Redis | Cache | 🟠 Media/Alta | Detectado por Analyst | 🔴 No evidenciado |
| SQL Server / Azure SQL | Base de datos | 🔴 Alta | Detectado por Analyst | 🔴 No evidenciado |
| GitHub Actions | CI/CD | 🟠 Media | Detectado por Analyst | 🟡 Parcial |
| Docker | Runtime/build | 🟠 Media | Detectado por Analyst | 🟡 Parcial |

---

## 📊 Inventario por estado

> Dado que no hay evidencia de deploy/observabilidad, la clasificación se limita a lo observable en código.

- 🟢 **Activas:** 0 (no verificable)
- 🟡 **Activa-legacy (por evidencia estática):** 2
- 🟠 **Mantenimiento:** 0
- 🔴 **Obsoletas:** 0
- ⚪ **Desconocidas / sin evidencia suficiente:** N/A

---

## ⚠️ Gaps de inventario (información faltante)

Para convertir este inventario “estático” en un inventario **operativo real**, se requiere:

1) **Entornos desplegados**
- ¿Dónde corre el backend? (K8s, VM, PaaS)
- ¿Dónde se sirve el frontend? (S3/CloudFront, nginx, Vercel, etc.)
- URL(s) de ambientes: dev/qa/prod

2) **Observabilidad**
- Herramientas: Grafana/DataDog/Splunk/CloudWatch
- Dashboards/alertas asociadas al servicio

3) **Artefactos**
- Registry de imágenes Docker (ECR/ACR/GHCR)
- Repositorio de paquetes (Nexus/Artifactory) si aplica

4) **Propiedad / ownership**
- Equipo dueño, guardias, SLAs, ITSM

---

## ✅ Acciones sugeridas (inventario “Día 1”)

| ID | Acción | Responsable sugerido | Criticidad |
|---|---|---|---|
| AI-01 | Confirmar lista de componentes desplegados en prod (backend/frontend/workers) | Tech Lead / SRE | 🔴 |
| AI-02 | Documentar URLs de ambientes (dev/qa/prod) y método de despliegue | SRE / DevOps | 🔴 |
| AI-03 | Identificar y documentar DB endpoints + propietarios (Postgres/Redis/Azure SQL) | DBA / Plataforma | 🔴 |
| AI-04 | Identificar registry de imágenes y estrategia de tagging/promoción | DevOps | 🟠 |
| AI-05 | Validar si existen repos adicionales fuera de `jpguaqueta12` (org corporativa) | PM/Delivery | 🟡 |

---

## Conclusión

Con la evidencia CORE actual, el inventario confiable se reduce al repositorio `allianz` y dos componentes internos (frontend + backend). Para un inventario completo alineado a operación (Día 1) se requieren confirmaciones de despliegue, observabilidad, dependencias y ownership.

---

*Generado por Agencia de Transición — 2026-05-18*
