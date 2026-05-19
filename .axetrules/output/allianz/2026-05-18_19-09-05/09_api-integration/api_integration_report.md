# 🔌 API Integration — Catálogo de APIs e Integraciones

**Proyecto:** allianz  
**Fase:** API Integration  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  
**CLONE_DIR:** `/tmp/repo-intel/allianz@main/`  

---

## 📌 Resumen Ejecutivo

Este reporte cataloga **APIs expuestas** y **integraciones salientes** inferidas por evidencia estática en el repositorio (frontend + backend). Se construye a partir de:

- Código del cliente HTTP en frontend (`front-planificacion/src/services/api.ts`)
- Convención de base URL (`VITE_API_BASE_URL` + `/api/v1`)
- Rutas consumidas vía `fetch` / `authFetch` y nombres de recursos

**Resultado:** Se observa un **backend FastAPI** (inferido por stack CORE) que expone una API REST versionada en `/api/v1` consumida por un SPA React/Vite.  
No se encontró (en la evidencia revisada) un contrato OpenAPI/Swagger explícito (`openapi.yaml`, `swagger.json`) ni AsyncAPI.

> Estado de evidencia: **PARCIAL**. Este catálogo refleja endpoints consumidos por el frontend (alta probabilidad de existir) pero no garantiza cobertura del 100% del backend.

---

## 🔎 Evidencia Analizada

### Archivos revisados (evidencia directa)

- `front-planificacion/src/services/api.ts`  
  - Define `BASE = ${VITE_API_BASE_URL}/api/v1`
  - Contiene wrappers `authFetch()` (Bearer token) y múltiples `fetch()` hacia recursos REST
- Señales adicionales:
  - Múltiples `r.json()` y validación de `r.ok` → API JSON
  - Endpoints de upload con `FormData` (`/upload/*`)
  - Exportación a Word desde backend (`/estimation/export-word`)

### Señales NO encontradas

- `openapi.yaml` / `openapi.json` / `swagger.yaml` / `swagger.json`
- `asyncapi.yaml` / `asyncapi.json`
- `protobuf` / `grpc` (sin evidencia en lo revisado)

---

## 🌐 API expuesta (REST) — Endpoints detectados

### Convenciones generales

- **Base:** `${VITE_API_BASE_URL}/api/v1`
- **Formato:** JSON (request/response) excepto uploads (multipart/form-data) y export (blob)
- **Errores:** backend retorna `{ detail: string }` (patrón típico FastAPI)
- **Auth:** Bearer token vía header `Authorization: Bearer <token>` para rutas `/config/*` y `/auth/me/any` (validación de token)

---

### 1) Autenticación / Sesiones / Chat

| Endpoint | Método | Auth | Request (inferido) | Response (inferido) | Consumidor |
|---|---|---|---|---|---|
| `/auth/login` | POST | No | `{ username, password }` | `{ access_token, token_type }` | Frontend |
| `/auth/me/any` | GET | Sí | — | `{ role }` (role: `superuser` \| `user`) | Frontend |
| `/session` | POST | No | `{ user: "planificador" }` | `{ session_id }` | Frontend |
| `/chat` | POST | No* | `{ session_id, message }` | `{ stream_url, session_id }` | Frontend |

\*Nota: No se observa header de auth en `/chat` desde el cliente; validar si el backend realmente requiere token.

---

### 2) Dashboards

| Endpoint | Método | Auth | Query params | Response | Consumidor |
|---|---|---|---|---|---|
| `/dashboard` | GET | No | `pi_id?` | `DashboardData` (tipo TS) | Frontend |
| `/dashboard/fabrica` | GET | No | `pi_id?` | `DashboardData` | Frontend |
| `/dashboard/incidentes` | GET | No | — | `DashboardData` | Frontend |

---

### 3) Configuración de PIs (Program Increments)

| Endpoint | Método | Auth | Request / Params | Response |
|---|---|---|---|---|
| `/config/pis` | GET | No | — | `PiInfo[]` |
| `/config/pis` | POST | Sí | `{ nombre, fecha_inicio, fecha_fin, dias_laborables, horas_por_dia, descripcion? }` | `PiInfo` |
| `/config/pis/{piId}` | PUT | Sí | `Partial<PiInfo>` | `PiInfo` |
| `/config/pis/{piId}` | DELETE | Sí | — | `{ deleted, deleted_counts, replacement_pi }` |
| `/config/pis/{piId}/activar` | POST | Sí | — | `PiInfo & { personas_copiadas, proyectos_copiados }` |
| `/config/pis/{piId}/festivos` | GET | No | — | `Festivo[]` |
| `/config/pis/{piId}/festivos` | POST | Sí | `{ fecha, nombre }` | `Festivo` |
| `/config/pis/{piId}/festivos/{festivoId}` | DELETE | Sí | — | `void` |

---

### 4) Capacidad de personas (dentro de PI)

| Endpoint | Método | Auth | Request | Response |
|---|---|---|---|---|
| `/config/pis/{piId}/capacidad/nueva-persona` | POST | Sí | `{ nombre, apellidos, tecnologia }` | `void` |
| `/config/pis/{piId}/capacidad/personas/{personaId}` | PATCH | Sí | `{ capacidad_horas?, reserva_estimacion_*?, senior? }` | `void` |
| `/config/pis/{piId}/capacidad/personas/{personaId}` | DELETE | Sí | — | `void` |
| `/config/pis/{piId}/capacidad/sincronizar` | POST | Sí | — | `{ actualizado, horas_por_persona }` |

---

### 5) Novedades de disponibilidad (dentro de PI)

| Endpoint | Método | Auth | Request | Response |
|---|---|---|---|---|
| `/config/pis/{piId}/novedades` | GET | No | — | `NovedadDisponibilidad[]` |
| `/config/pis/{piId}/novedades` | POST | Sí | `{ persona_id, tipo, fecha_inicio, fecha_fin, horas_por_dia?, descripcion? }` | `NovedadDisponibilidad` |
| `/config/pis/{piId}/novedades/{novedadId}` | DELETE | Sí | — | `void` |

---

### 6) Proyectos (dentro de PI / capacidad)

| Endpoint | Método | Auth | Request | Response |
|---|---|---|---|---|
| `/config/pis/{piId}/proyectos/nuevo` | POST | Sí | `{ nombre, identi, modulo }` | `void` |
| `/config/pis/{piId}/proyectos/{proyectoId}` | DELETE | Sí | — | `void` |

---

### 7) Alertas y SLA

| Endpoint | Método | Auth | Params | Response |
|---|---|---|---|---|
| `/alertas/{modulo}` | GET | No | `pi_id?` | `AlertaItem[]` |
| `/sla/{modulo}` | GET | No | `pi_id?` | `SlaReport` |

---

### 8) Backlog (gestión de tickets)

| Endpoint | Método | Auth | Params | Response |
|---|---|---|---|---|
| `/backlog/{modulo}` | GET | No | `pi_id?` | JSON (items) |
| `/backlog/{modulo}` | POST | No | `pi_id?` + `CreateBacklogData` | `BacklogItem` |
| `/backlog/{modulo}/responsables` | GET | No | `pi_id?` | `ResponsableDisponible[]` |
| `/backlog/{modulo}/{ticketId}/fecha-asignacion` | PATCH | No | `{ fecha_asignacion }` | `{ ok, fecha_finalizacion, fecha_finalizacion_inicial }` |
| `/backlog/{modulo}/{ticketId}/escalamiento` | PATCH | No | `EscalamientoData` | `EscalamientoResponse` |
| `/backlog/{modulo}/{ticketId}/status` | PATCH | No | `{ status }` | `{ ok, status, fecha_entrega }` |
| `/backlog/{modulo}/{ticketId}` | DELETE | No | — | `{ deleted, id }` |
| `/backlog/{modulo}/{ticketId}/planificacion` | PUT | No | `PlanificacionData` | `void` |

> Observación: varias rutas de backlog no usan `authFetch()` desde el cliente. Validar si el backend aplica auth por otro mecanismo (network ACL, cookies, o endpoints públicos).

---

### 9) Uploads / Importación de Excel

| Endpoint | Método | Content-Type | Response |
|---|---|---|---|
| `/upload/analizar-backlog` | POST | `multipart/form-data` | `BacklogAnalisis` |
| `/upload/importar-backlog` | POST | `multipart/form-data` | `BacklogImportResult` |
| `/upload/analizar-incidentes` | POST | `multipart/form-data` | `IncidentesAnalisis` |
| `/upload/importar-incidentes` | POST | `multipart/form-data` | `IncidentesImportResult` |
| `/upload/preview-excel` | POST | `multipart/form-data` | `ExcelPreview` |

---

### 10) Estimación + export Word

| Endpoint | Método | Content-Type | Response |
|---|---|---|---|
| `/estimation/extract-file` | POST | `multipart/form-data` | `{ text, meta }` |
| `/estimation/estimar` | POST | JSON | `EstimacionResult` |
| `/estimation/export-word` | POST | JSON | `Blob` (archivo Word) |

---

## 🔐 Autenticación y mecanismos de seguridad (inferidos)

### Bearer token
- `Authorization: Bearer <token>` se agrega automáticamente leyendo `localStorage['auth-storage']`
- Se valida expiración client-side (`expiresAt`)
- Endpoint de verificación: `/auth/me/any`

### Riesgos / gaps
- Endpoints sensibles consumidos sin authFetch (posible exposición si no hay auth server-side)
- No hay evidencia de rate limiting, CORS policy o CSRF en esta inspección
- No se evidencian scopes/roles más allá de `superuser`/`user`

---

## 🔁 Integraciones asíncronas / jobs

No se detectaron señales de:
- Kafka/RabbitMQ/SQS/ServiceBus
- Cron jobs / schedulers (Quartz, APScheduler, Celery beat)
- Webhooks entrantes/salientes

> Limitación: este agente analizó principalmente el cliente frontend; se recomienda escanear routers/controladores del backend para confirmar.

---

## 📄 Contratos API (OpenAPI/Swagger/AsyncAPI)

**Estado:** ❌ No evidenciados (en el set revisado)

**Recomendaciones:**
1) Exportar OpenAPI desde FastAPI (`/openapi.json`) y versionarlo en repo (`openapi.yaml`).
2) Definir convenciones de versionado (`/api/v1`) y política de breaking changes.
3) Documentar auth (roles, permisos, expiración, refresh si aplica).

---

## ✅ Recomendaciones priorizadas

### P1 — Día 1 / Operación segura
1) Confirmar **autenticación server-side** en endpoints de backlog/config.
2) Publicar un contrato OpenAPI para consumidores (frontend, integraciones futuras).
3) Documentar variables de entorno: `VITE_API_BASE_URL` (frontend) y `BASE_URL` backend.

### P2 — Robustez
4) Estandarizar formato de error (RFC 7807 o esquema propio).
5) Implementar timeouts/retries y trazabilidad (request-id) en cliente.

### P3 — Gobernanza
6) Generar catálogo formal de endpoints (tags: auth, backlog, sla, config, estimation).
7) Definir SLAs por módulo / endpoint crítico.

---

## Limitaciones de evidencia

- El catálogo está basado en rutas consumidas por frontend; el backend puede exponer endpoints adicionales.
- No se revisaron routers/controladores FastAPI directamente.
- No se validó runtime (logs, tráfico real, auth real).

---

*Generado por Agencia de Transición — 2026-05-18*
