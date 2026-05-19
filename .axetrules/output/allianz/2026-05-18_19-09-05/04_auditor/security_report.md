# 🔐 Auditor — Seguridad

**Proyecto:** allianz  
**Fase:** Auditor  
**Fecha:** 2026-05-18 19:09:07  
**URL:** https://github.com/jpguaqueta12/allianz.git  

---

## Veredicto: ⚠️ RIESGO DETECTADO

## Secretos Expuestos (3)

| Tipo | Archivo | Línea | Severidad | Fragmento |
|---|---|---|---|---|
| generic_password | `back-planificacion/app/db/connection.py` | 35 | CRITICAL | pass************************** |
| generic_password | `back-planificacion/scripts/seed_azure_sql.py` | 46 | CRITICAL | pass***********************rn  |
| generic_password | `back-planificacion/scripts/test_sql_connection.py` | 40 | CRITICAL | pass******************rn " |

### Recomendaciones

- **generic_password:** Usar variables de entorno o gestor de secretos

## Vulnerabilidades de Dependencias

> No se ejecutó análisis de CVEs o no se encontraron manifiestos.

---

*Generado por Agencia de Transición — 2026-05-18 19:09:07*
