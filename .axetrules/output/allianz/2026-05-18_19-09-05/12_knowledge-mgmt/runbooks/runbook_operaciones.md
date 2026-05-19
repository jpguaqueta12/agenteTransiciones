# 🧰 Runbook Operativo — allianz (operación Día 1)

**Proyecto:** allianz  
**Fase:** Knowledge Management  
**Fecha:** 2026-05-18  
**RUN_DIR:** `.axetrules/output/allianz/2026-05-18_19-09-05/`  

---

## 📌 Propósito

Guía práctica para operar y diagnosticar los flujos críticos del sistema de planificación (`front-planificacion` + `back-planificacion`) desde el Día 1, basada en evidencia estática (endpoints consumidos por frontend) y dependencias detectadas.

> **Limitación:** no hay evidencia de runtime/observabilidad. Completar este runbook con URLs reales, dashboards y owners en KT.

---

## 🧩 Mapa rápido (qué rompe qué)

| Componente | Si falla… | Impacto negocio | Señales probables |
|---|---|---:|---|
| Backend `back-planificacion` (FastAPI) | No hay API / 5xx | 🔴 Bloquea backlog/capacidad/PI | Errores 502/504, timeouts, CORS |
| Frontend `front-planificacion` (SPA) | No carga UI o no conecta | 🔴 Degrada operación | Página en blanco, errores consola |
| PostgreSQL | datos core PI/backlog/capacidad | 🔴 Caída total | 500 en endpoints, errores DB |
| SQL Server / Azure SQL | datos auxiliares o integración | 🔴/🟠 según uso real | errores pyodbc, timeouts |
| Redis | cache/sesión/estado (inferido) | 🟠 Degradación severa | errores redis, latencia |
| LLM Provider | chat/estimación | 🟠/🟡 | costos/rate limits/429 |

---

## 🔐 Runbook 0 — Autenticación / Token (F-01)

### Síntomas
- No permite login (credenciales incorrectas)
- Login ok, pero UI no habilita permisos admin
- Errores 401/403 en rutas protegidas

### Diagnóstico (paso a paso)
1) Validar `POST /api/v1/auth/login`
   - Esperado: `200` con `access_token` y `token_type`
2) Confirmar almacenamiento en cliente:
   - `localStorage['auth-storage']` existe y `expiresAt` no está vencido
3) Validar rol:
   - `GET /api/v1/auth/me/any` con header `Authorization: Bearer <token>`
   - Esperado: `{ role: "superuser" | "user" }`

### Causas comunes (inferidas)
- Usuario/password incorrectos (backend devuelve `{detail}`)
- Token expirado (cliente lo invalida)
- Backend no valida roles consistentemente (gap)

### Acciones de remediación
- Forzar logout (borrar `auth-storage`) y re-login
- Verificar clocks (expiración client-side depende de hora local)
- Confirmar enforcement server-side por endpoint crítico (ver riesgo `RISK-AUTH-INCONSISTENT`)

### Escalación
- Si el token funciona en `/auth/me/any` pero backlog/config falla → escalar a backend (AuthZ inconsistente)

---

## 🗓️ Runbook 1 — PI (Program Increment) (F-02/F-03)

### Síntomas
- No lista PIs / no crea PI / no activa PI
- Dashboards/backlog no muestran datos por falta de PI activo

### Endpoints relevantes
- `GET /api/v1/config/pis`
- `POST /api/v1/config/pis` (auth)
- `POST /api/v1/config/pis/{piId}/activar` (auth)
- Festivos:
  - `GET /api/v1/config/pis/{piId}/festivos`
  - `POST /api/v1/config/pis/{piId}/festivos` (auth)

### Diagnóstico
1) Confirmar que existe al menos 1 PI: `GET /config/pis`
2) Si no existe, crear uno (admin): `POST /config/pis`
3) Activar: `POST /config/pis/{piId}/activar`
   - Esperado: PI + contadores `personas_copiadas` / `proyectos_copiados` (inferido)

### Riesgos
- `DELETE /config/pis/{piId}` es destructivo → evitar en producción sin plan

---

## 👥 Runbook 2 — Capacidad (personas + sincronización) (F-04/F-05)

### Síntomas
- No permite crear/editar personas de capacidad
- Sincronización falla o genera datos inconsistentes
- Planning/backlog no refleja disponibilidad

### Endpoints relevantes
- `POST /api/v1/config/pis/{piId}/capacidad/nueva-persona` (auth)
- `PATCH /api/v1/config/pis/{piId}/capacidad/personas/{personaId}` (auth)
- `POST /api/v1/config/pis/{piId}/capacidad/sincronizar` (auth)
- Novedades:
  - `GET /api/v1/config/pis/{piId}/novedades`
  - `POST /api/v1/config/pis/{piId}/novedades` (auth)

### Diagnóstico
1) Validar PI activo (Runbook 1)
2) Crear persona mínima y reintentar sincronización
3) Revisar payloads (horas/capacidad/reservas)

### Remediación
- Reintentar sincronización tras corregir datos inválidos
- Validar reglas de negocio en KT (reservas, seniority, etc.)

---

## 🧾 Runbook 3 — Backlog (F-07/F-08/F-09) — CRÍTICO

### Síntomas
- Backlog vacío, no permite crear/actualizar tickets
- Cambios de status o fechas no se reflejan
- Planificación/escalamiento falla

### Endpoints relevantes
- `GET /api/v1/backlog/{modulo}?pi_id=...`
- `POST /api/v1/backlog/{modulo}?pi_id=...`
- `PATCH /api/v1/backlog/{modulo}/{ticketId}/status`
- `PATCH /api/v1/backlog/{modulo}/{ticketId}/fecha-asignacion`
- `PUT /api/v1/backlog/{modulo}/{ticketId}/planificacion`
- `PATCH /api/v1/backlog/{modulo}/{ticketId}/escalamiento`
- `DELETE /api/v1/backlog/{modulo}/{ticketId}` (destructivo)

### Diagnóstico
1) Confirmar PI válido en query param `pi_id`
2) Validar que el backend responde sin timeout/5xx
3) Confirmar permisos:
   - Riesgo: el frontend usa `fetch()` sin token en backlog (ver `RISK-AUTH-INCONSISTENT`)
   - Confirmar si backend exige auth o existe una capa de seguridad (network ACL, API gateway, etc.)
4) Si falla planificación/escalamiento:
   - Revisar payloads `PlanificacionData` / `EscalamientoData`
   - Confirmar reglas de negocio (KT)

### Remediación
- Evitar `DELETE` en producción sin backups/confirmación
- Si hay 401/403 inesperados, alinear cliente para usar `authFetch` o validar backend

---

## 📊 Runbook 4 — Reporting (Dashboards / Alertas / SLA) (F-10)

### Síntomas
- Dashboards no cargan o muestran datos inconsistentes
- Alertas/SLA no devuelven resultados

### Endpoints
- `GET /api/v1/dashboard`
- `GET /api/v1/dashboard/fabrica`
- `GET /api/v1/dashboard/incidentes`
- `GET /api/v1/alertas/{modulo}`
- `GET /api/v1/sla/{modulo}`

### Diagnóstico
1) Verificar PI activo y `pi_id` cuando aplique
2) Revisar performance (estos endpoints pueden ser pesados en DB)
3) Confirmar que los endpoints existen y retornan JSON válido

---

## 📥 Runbook 5 — Upload Excel (F-11)

### Síntomas
- Upload falla (timeout / 413 / 500)
- Preview/import no coincide con el Excel
- Duplicados o validación de columnas

### Endpoints
- `POST /api/v1/upload/analizar-backlog` (multipart/form-data)
- `POST /api/v1/upload/importar-backlog`
- `POST /api/v1/upload/analizar-incidentes`
- `POST /api/v1/upload/importar-incidentes`
- `POST /api/v1/upload/preview-excel`

### Diagnóstico
1) Confirmar tamaño de archivo y límites en servidor/proxy
2) Reintentar con archivo pequeño de prueba
3) Validar que `Content-Type` y boundary de multipart sean correctos

### Remediación
- Aumentar límites de upload en proxy/app (si aplica)
- Validar formato y columnas esperadas (KT)

---

## 🤖 Runbook 6 — Estimación IA + Export Word (F-12)

### Síntomas
- Extracción de texto falla (PDF/Word)
- Estimación tarda demasiado o retorna error
- Export Word retorna archivo corrupto

### Endpoints
- `POST /api/v1/estimation/extract-file` (multipart)
- `POST /api/v1/estimation/estimar` (JSON)
- `POST /api/v1/estimation/export-word` (JSON → blob)

### Diagnóstico
1) Confirmar que el backend tiene acceso a provider LLM (API key/endpoint)
2) Revisar timeouts (LLM puede tardar)
3) Validar el `Content-Disposition`/tipo de respuesta en export

### Remediación
- Implementar timeouts + retries + rate limit handling (futuro)
- Fallback: export manual si falla (capability baja)

---

## 💬 Runbook 7 — Session / Chat (F-13)

### Síntomas
- No crea sesión o no genera `stream_url`
- Costos/latencia alta (LLM)
- Riesgo de endpoint público

### Endpoints
- `POST /api/v1/session`
- `POST /api/v1/chat`

### Diagnóstico
1) Confirmar si requiere auth (cliente no lo envía)
2) Verificar proveedor LLM / streaming endpoint

### Remediación
- Asegurar AuthZ server-side si maneja datos sensibles
- Implementar rate limiting / cuotas

---

## ✅ Checklist “Día 1” (operación segura)

- [ ] Confirmar enforcement de AuthN/AuthZ en backend para endpoints críticos (backlog/config/upload/chat)
- [ ] Confirmar accesos a Postgres / SQL Server / Redis
- [ ] Identificar URLs reales de FE/BE (dev/qa/prod)
- [ ] Identificar herramienta de observabilidad (logs + métricas + alerting)
- [ ] Rotar secretos detectados (3) y remover hardcodes
- [ ] Publicar OpenAPI (`/openapi.json`) y versionarlo

---

*Generado por Agencia de Transición — 2026-05-18*
