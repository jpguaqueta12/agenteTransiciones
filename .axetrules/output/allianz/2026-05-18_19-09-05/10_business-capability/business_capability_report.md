# 💼 Business Capability — Mapa de Capacidades de Negocio

**Proyecto:** allianz  
**Fase:** Business Capability  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Resumen Ejecutivo

Este reporte traduce evidencia técnica (stack, arquitectura, dependencias y endpoints) a un **mapa de capacidades de negocio**: qué hace el sistema para el negocio y qué tan crítico es cada capability.

**Contexto inferido:** el repositorio `allianz` contiene una solución de **planificación / gestión de capacidad y backlog** con:
- Configuración de PIs (Program Increments) y festivos
- Gestión de capacidad de personas y novedades de disponibilidad
- Gestión de backlog de tickets por módulo (alta/edición/borrado, responsables, SLA, escalamiento)
- Dashboards (general, fábrica, incidentes)
- Importación/analítica de Excel (backlog / incidentes)
- Estimación asistida (IA) y exportación a Word

> Estado de evidencia: **PARCIAL**. El mapeo se basa en endpoints consumidos por frontend (`api.ts`) y dependencias detectadas. Debe validarse con Product/Negocio y sesiones KT.

---

## 🔎 Evidencia Analizada

- `02_analyst/stack_quality_report.md`  
  - Stack: FastAPI + React/Vite, DBs: PostgreSQL/Redis/SQL Server, Infra: Docker + GitHub Actions
- `07_app-inventory/application_inventory_report.md`  
  - Componentes: `front-planificacion` (SPA) + `back-planificacion` (API)
- `08_dependency-mapping/dependency_map_report.md`  
  - Dependencias críticas operativas (Postgres, Redis, Azure SQL, LLM provider)
- `09_api-integration/api_integration_report.md`  
  - Endpoints REST consumidos por el frontend (evidencia de capabilities)
- Evidencia directa: `front-planificacion/src/services/api.ts`

---

## 🧩 Capacidades de negocio identificadas

### Catálogo de capabilities (con evidencia)

| Capability | Descripción | Endpoints / evidencias | Criticidad |
|---|---|---|---|
| Autenticación y autorización | Login, validación de rol para funciones administrativas | `POST /auth/login`, `GET /auth/me/any`, Bearer token en `authFetch()` | 🔴 CRÍTICA |
| Gestión de sesión / Chat | Sesión de usuario y chat (posible asistente IA) | `POST /session`, `POST /chat` | 🟠 ALTA |
| Visualización de dashboards | Reportes/indicadores para gestión | `GET /dashboard`, `/dashboard/fabrica`, `/dashboard/incidentes` | 🟠 ALTA |
| Configuración de PI | Alta/edición/borrado/activación de PI | `GET/POST /config/pis`, `PUT/DELETE /config/pis/{piId}`, `POST /activar` | 🔴 CRÍTICA |
| Calendario de festivos | Gestión de festivos del PI | `GET/POST /config/pis/{piId}/festivos`, `DELETE /festivos/{festivoId}` | 🟡 MEDIA |
| Capacidad de personas | Alta/baja/actualización/sincronización de capacidad | `POST /capacidad/nueva-persona`, `PATCH/DELETE /capacidad/personas/{id}`, `POST /capacidad/sincronizar` | 🔴 CRÍTICA |
| Novedades de disponibilidad | Gestión de ausencias/cambios de disponibilidad | `GET/POST /config/pis/{piId}/novedades`, `DELETE /novedades/{id}` | 🟠 ALTA |
| Proyectos dentro de PI | Alta/baja de proyectos asociados a PI/capacidad | `POST /config/pis/{piId}/proyectos/nuevo`, `DELETE /proyectos/{id}` | 🟡 MEDIA |
| Gestión de alertas | Alertas por módulo para priorización | `GET /alertas/{modulo}` | 🟠 ALTA |
| Gestión de SLA | Políticas y reporte de SLA por módulo | `GET /sla/{modulo}` | 🟠 ALTA |
| Gestión de backlog | CRUD y actualización de tickets (fecha, escalamiento, status, planificacion) | `GET/POST /backlog/{modulo}`, `PATCH /fecha-asignacion`, `PATCH /escalamiento`, `PATCH /status`, `PUT /planificacion`, `DELETE /{ticketId}` | 🔴 CRÍTICA |
| Responsables disponibles | Sourcing/asignación de responsables | `GET /backlog/{modulo}/responsables` | 🟠 ALTA |
| Importación/analítica de Excel | Cargar backlog/incidentes desde Excel y previsualización | `/upload/*` + `FormData` | 🟡 MEDIA |
| Estimación asistida / extracción de texto | Extracción texto de archivos y estimación (prob. IA) | `POST /estimation/extract-file`, `POST /estimation/estimar` | 🟡 MEDIA |
| Exportación a Word | Exportación de estimaciones a docx | `POST /estimation/export-word` (blob) | 🟢 BAJA |

---

## 🧠 Mapa de capacidades (vista agregada)

### 🔴 Capacidades CRÍTICAS (sin ellas el negocio no opera)

1) **Gestión de backlog**  
   - Impacto: sin backlog no hay planificación/asignación/tracking operativo.  
   - Dependencias: DB (Postgres/SQL Server), API FastAPI, front SPA.

2) **Capacidad de personas + sincronización**  
   - Impacto: imposibilidad de planificar capacidad/fechas, afecta cumplimiento.  
   - Dependencias: DB + lógica de negocio.

3) **Configuración de PI (alta/activación/borrado)**  
   - Impacto: no se puede abrir/cerrar periodos de planificación; el resto del sistema pierde contexto.  
   - Riesgo adicional: borrado de PI sugiere operaciones destructivas → requiere controles.

4) **Autenticación/Autorización**  
   - Impacto: pérdida de control de acceso; exposición de datos/config.  
   - Evidencia: token + rol (`superuser`/`user`).

### 🟠 Capacidades ALTAS (impacto significativo)

- Dashboards (dirección/operación)  
- Novedades de disponibilidad  
- Alertas + SLA (priorización/seguimiento)  
- Responsables disponibles  
- Sesión/Chat (si soporta operación o decisiones, su caída degrada la experiencia)

### 🟡 Capacidades MEDIAS (workaround posible)

- Festivos  
- Proyectos en PI  
- Importación/analítica Excel  
- Estimación asistida / extracción de texto

### 🟢 Capacidades BAJAS

- Exportación a Word (export se puede hacer manual en emergencias)

---

## ⚠️ Riesgos de negocio y operación (inferidos)

1) **Autenticación inconsistente** (algunas rutas consumidas sin `authFetch`)  
   - Riesgo: exposición de capabilities críticas (backlog/config) si el backend no valida auth server-side.

2) **Dependencias críticas sin evidencia de HA** (Postgres / Azure SQL / Redis)  
   - Riesgo: caída total del capability “planificación/backlog” y “capacidad”.

3) **Dependencia externa de IA (LLM provider)**  
   - Riesgo: degradación en capabilities relacionadas con chat/estimación (costos, rate limits, disponibilidad).

4) **Operaciones destructivas** (`DELETE /config/pis/{piId}`, `DELETE /backlog/*`)  
   - Riesgo: borrados accidentales; requiere trazabilidad/auditoría.

---

## ✅ Priorización para transición (qué validar primero)

| Prioridad | Capability | Qué validar en KT / operación |
|---:|---|---|
| P1 | Backlog + Capacidad + PI | Reglas de negocio, modelo de datos, manejo de estados, permisos, criterios SLA, rollback |
| P1 | AuthN/AuthZ | Modelo de roles, enforcement en backend, rotación de tokens, expiración y auditoría |
| P2 | Alertas/SLA/Dashboards | Fuentes de datos, definiciones de métricas, ventanas, refresh |
| P2 | Novedades disponibilidad | Impacto en capacidad, reglas de solapamiento, validaciones |
| P3 | Excel uploads + estimación | Límites de tamaño, validaciones, formatos soportados, tiempos |
| P3 | Export Word | Formato, plantillas, seguridad (PII) |

---

## Recomendaciones

### Día 1 (bloqueantes)
1) Confirmar que **todas las capabilities críticas** validan autorización en backend.
2) Documentar **definiciones de negocio**: PI, backlog ticket, SLA, escalamiento, planificacion.
3) Asegurar accesos operativos a DBs (Postgres / Azure SQL) y Redis.

### Semana 1-2
4) Agregar auditoría/bitácora (quién cambia PI/backlog).
5) Documentar dashboards (KPIs y cálculos).
6) Formalizar contrato OpenAPI.

---

## Limitaciones de evidencia

- No se inspeccionaron routers/controladores FastAPI directamente.
- No hay evidencia de métricas reales de operación (tráfico, SLAs reales).
- No se cuenta con alcance contractual ni KT del negocio.

---

*Generado por Agencia de Transición — 2026-05-18*
