# 🏢 Agencia de Transición de Software

> Este archivo es el punto de entrada de la agencia. Funciona como el
> `.github/copilot-instructions.md` — Kiro lo lee y sabe cómo operar todo el sistema.

---

## ¿Qué es esta agencia?

Un sistema multi-agente que analiza repositorios de software y genera planes de modernización.
Opera íntegramente desde archivos `.md`. El código Python en `core/` es la capa de ejecución.

---

## Estructura

```
.axetrules/
├── AGENCY.md                          ← ESTÁS AQUÍ — manifiesto raíz
│
├── credentials/
│   └── .env                           ← credenciales Git (editar antes de usar)
│
├── agentes/
│   ├── recepcion/SKILL.md             ← gateway de entrada
│   ├── director/SKILL.md              ← orquestador maestro
│   ├── detector/SKILL.md              ← detección automática de plataforma
│   ├── scout/SKILL.md                 ← descubrimiento de proyectos
│   ├── analyst/SKILL.md               ← stack + calidad
│   ├── architect/SKILL.md             ← arquitectura + diagramas
│   ├── auditor/SKILL.md               ← seguridad + CVEs
│   ├── strategist/SKILL.md            ← roadmap de transición
│   │
│   ├── ── ALCANCE ──────────────────────────────────────────────────────────
│   ├── access-readiness/SKILL.md      ← verificación de accesos Día 1
│   ├── app-inventory/SKILL.md         ← inventario real vs contractual
│   │
│   ├── ── TÉCNICA ──────────────────────────────────────────────────────────
│   ├── dependency-mapping/SKILL.md    ← mapa de dependencias + SPOFs
│   ├── api-integration/SKILL.md       ← catálogo de APIs e integraciones
│   │
│   ├── ── NEGOCIO ──────────────────────────────────────────────────────────
│   ├── business-capability/SKILL.md   ← capacidades de negocio
│   ├── functional-flow/SKILL.md       ← flujos funcionales + excepciones
│   ├── kt-capture/SKILL.md            ← captura de sesiones KT
│   │
│   ├── ── CONTROL ──────────────────────────────────────────────────────────
│   ├── knowledge-mgmt/SKILL.md        ← base de conocimiento + runbooks
│   └── report-generator/SKILL.md      ← consolida markdown → Word (.docx)
│   │
│   ├── ── TMO (Transition Management Office) ──────────────────────────────
│   ├── exit-criteria/SKILL.md         ← criterios de salida + gates
│   └── command-control/SKILL.md       ← RAID + decisiones ejecutivas
│
├── core/
│   ├── orchestrator.py                ← cerebro de coordinación
│   ├── local_analyzer_compat.py       ← wrapper de análisis local
│   ├── drivers/
│   │   ├── env_loader.py              ← 🔑 carga credentials/.env
│   │   ├── detect_platform.py         ← 🔎 detección automática de plataforma
│   │   ├── output_writer.py           ← 📁 escritura centralizada de outputs
│   │   ├── run_full_pipeline.py       ← 🚀 pipeline completo (comando principal)
│   │   ├── platform_client.py         ← cliente Git unificado
│   │   ├── discover_projects.py       ← discovery de repos
│   │   ├── run_quality_analysis.py    ← driver de calidad (fase individual)
│   │   ├── run_architecture_analysis.py ← driver de arquitectura (fase individual)
│   │   ├── run_dependency_analysis.py ← driver de dependencias + CVEs
│   │   ├── osv_client.py              ← cliente Google OSV
│   │   ├── markdown_reporter.py       ← generador de reportes .md
│   │   ├── generate_report.py         ← 📑 consolida markdown → Word (.docx)
│   │   └── check_prerequisites.py     ← validador de entorno
│   ├── engines/
│   │   ├── stack_engine.py            ← detección de stack
│   │   ├── quality_engine.py          ← score de calidad
│   │   ├── security_engine.py         ← detección de secretos
│   │   ├── arch_engine.py             ← análisis arquitectónico
│   │   └── volumetry_analyzer.py      ← LOC, complejidad, hotspots
│   └── models/
│       └── models.py                  ← dataclasses compartidos
│
├── memory/
│   ├── .repo_intel_projects.txt       ← proyecto seleccionado por Scout
│   ├── agency_state.json              ← estado de fases completadas
│   └── TRANSITION_ROADMAP.md          ← copia rápida del roadmap final
│
├── output/                            ← 📁 TODOS LOS OUTPUTS AQUÍ
│   └── <nombre-proyecto>/
│       └── <YYYY-MM-DD_HH-MM>/
│           ├── INDEX.md               ← índice con links a todos los archivos
│           ├── manifest.json          ← metadatos del run
│           ├── 00_deteccion/
│           │   └── platform_detection.md
│           ├── 01_scout/
│           │   └── projects_discovered.md
│           ├── 02_analyst/
│           │   └── stack_quality_report.md
│           ├── 03_architect/
│           │   └── architecture_report.md
│           ├── 04_auditor/
│           │   └── security_report.md
│           ├── 05_strategist/
│           │   └── TRANSITION_ROADMAP.md
│           ├── 06_access-readiness/
│           │   └── access_readiness_report.md
│           ├── 07_app-inventory/
│           │   └── application_inventory_report.md
│           ├── 08_dependency-mapping/
│           │   └── dependency_map.md
│           ├── 09_api-integration/
│           │   └── api_integration_catalog.md
│           ├── 10_business-capability/
│           │   └── business_capability_report.md
│           ├── 11_functional-flow/
│           │   └── functional_flow_report.md
│           ├── 12_knowledge-mgmt/
│           │   ├── knowledge_graph.md
│           │   ├── onboarding_guide.md
│           │   └── runbooks/
│           ├── 13_kt-capture/
│           │   ├── kt_session_<n>_acta.md
│           │   └── open_questions.md
│           ├── 14_exit-criteria/
│           │   └── deliverables_matrix.md
│           ├── 15_command-control/
│           │   ├── raid_register.md
│           │   └── executive_dashboard.md
│           └── 00_summary/
│               └── FULL_REPORT.md
│
└── references/
    ├── analysis-components.md         ← mapeo de análisis a scripts
    └── platform-adapters.md           ← referencia técnica de APIs Git
```

---

## Inicio Rápido

### 1. Configurar credentials/.env (solo 2 campos)
```
URL=https://github.com/org/repo
TOKEN=tu_token_aqui
```
La agencia detecta automáticamente la plataforma, el project ID, el grupo y la URL de clonado.
**Esto es lo único que el usuario configura. El resto lo resuelve la agencia.**

### 2. Verificar entorno
```bash
python .axetrules/core/drivers/env_loader.py
# → muestra plataforma detectada, project name, group, etc.
```

### 3. Protocolo del orquestador — el script NO usa input()

El orquestador (este agente, leyendo AGENCY.md) es quien pregunta al usuario.
El script recibe todo por argumentos CLI y produce JSON o ejecuta el pipeline.

> ⚠️ **El protocolo completo está en `agentes/director/SKILL.md`.**
> Después de ejecutar el script Python (Paso C abajo), el Director debe continuar
> ejecutando los **agentes EXTENDIDOS (pasos 4-13)** siguiendo ese protocolo.
> El script Python solo cubre el Bloque 1 (CORE). El pipeline NO termina con él.

**Paso A — Descubrir todos los repos**
```bash
python .axetrules/core/drivers/run_full_pipeline.py --discover
# → JSON con todos los repos del usuario/org en credentials/.env
# → El agente muestra la lista y pregunta cuál analizar
```

**Paso B — Listar todas las ramas del repo elegido**
```bash
python .axetrules/core/drivers/run_full_pipeline.py --branches --url <repo_url>
# → JSON con todas las ramas del repo
# → El agente muestra la lista y pregunta cuál analizar
```

**Paso C — Ejecutar el pipeline con la selección del usuario**
```bash
python .axetrules/core/drivers/run_full_pipeline.py --url <repo_url> --branch <rama>
# → Borrón y cuenta nueva, pipeline completo
# → Guarda TODOS los repos y TODAS las ramas en 01_scout/ (aunque el usuario
#   haya elegido solo uno)
```

**Fase individual (el agente ya sabe el repo y la rama)**
```bash
python .axetrules/core/drivers/run_full_pipeline.py \
  --url <repo_url> --branch <rama> --fase analyst
```

**Historial**
```bash
python .axetrules/core/drivers/run_full_pipeline.py --history
```

### 4. Instalar dependencias (una sola vez)
```bash
pip install httpx pydantic gitpython pyyaml rich --break-system-packages
```

---

## Pipeline Completo — 3 Bloques de Ejecución

> **Punto de entrada invariable:** credentials/.env → Detector → pregunta repo → pregunta rama → pipeline.
> Esto ocurre siempre, en cada sesión, sin excepción.

### Bloque 1 — CORE (automático, vía Python)

El Director ejecuta estos pasos con scripts Python. No requieren análisis LLM.

| # | Agente | Script | Output |
|---|--------|--------|--------|
| 0 | Detector | `run_full_pipeline.py --discover` | Detecta plataforma, lista repos |
| 1 | Scout | `run_full_pipeline.py --branches --url <url>` | Lista ramas |
| 2 | Pipeline | `run_full_pipeline.py --url <url> --branch <rama>` | `00_deteccion/` `01_scout/` `02_analyst/` `03_architect/` `04_auditor/` `05_strategist/` |

### Bloque 2 — EXTENDIDO (análisis generativo LLM, ejecutado por el Director)

**Estos agentes NO tienen script Python. El Director los ejecuta él mismo:**
1. Lee el `SKILL.md` del agente indicado
2. Lee los outputs CORE relevantes de `output/<proyecto>/<run>/`
3. Aplica el protocolo del SKILL.md y produce el contenido
4. Escribe el archivo directamente en la carpeta de output del run activo

| # | Agente | Lee de | Escribe en |
|---|--------|--------|------------|
| 5 | Access Readiness | `agentes/access-readiness/SKILL.md` + outputs CORE | `06_access-readiness/access_readiness_report.md` |
| 6 | App Inventory | `agentes/app-inventory/SKILL.md` + `02_analyst/` `03_architect/` | `07_app-inventory/application_inventory_report.md` |
| 7 | Dependency Mapping | `agentes/dependency-mapping/SKILL.md` + outputs CORE | `08_dependency-mapping/dependency_map.md` |
| 8 | API Integration | `agentes/api-integration/SKILL.md` + `03_architect/` | `09_api-integration/api_integration_catalog.md` |
| 9 | Business Capability | `agentes/business-capability/SKILL.md` + `02_analyst/` | `10_business-capability/business_capability_report.md` |
| 10 | Functional Flow | `agentes/functional-flow/SKILL.md` + `07_` `08_` `09_` | `11_functional-flow/functional_flow_report.md` |
| 11 | Knowledge Mgmt | `agentes/knowledge-mgmt/SKILL.md` + todos los outputs | `12_knowledge-mgmt/` |
| 12 | KT Capture | `agentes/kt-capture/SKILL.md` + notas KT del usuario | `13_kt-capture/` |
| 13 | Exit Criteria | `agentes/exit-criteria/SKILL.md` + todos los outputs | `14_exit-criteria/` |
| 14 | Command & Control | `agentes/command-control/SKILL.md` + todos los outputs | `15_command-control/` |

### Bloque 3 — INFORME FINAL (SIEMPRE obligatorio, automático al terminar)

**Este paso se ejecuta SIEMPRE al final, sin excepción, aunque no se pida explícitamente.**

```bash
python .axetrules/core/drivers/generate_report.py
```

Consolida todos los `.md` del run → `00_summary/CONSOLIDATED_REPORT.md`
Exporta a Word → `00_summary/INFORME_TRANSICION_<PROYECTO>.docx`
Copia a `~/Downloads/` solo si la carpeta existe (o si se definió `AGENCIA_DOWNLOADS_DIR`).
Si la copia no se realiza, el pipeline continúa y el resultado se reporta en `downloads.status = skipped`.

---

## Reglas de la Agencia

1. **`credentials/.env` solo contiene `URL` y `TOKEN`, siempre** — la agencia nunca escribe otros campos en ese archivo. Los datos derivados viajan a través de `memory/agency_state.json`.
2. **Borrón y cuenta nueva en cada sesión** — al arrancar, el `SessionManager` archiva el estado anterior y limpia `memory/`. Cada sesión parte de cero sin excepción.
3. **Flujo de entrada obligatorio: credentials → detección → pregunta repo → pregunta rama** — este flujo no se puede omitir ni cortocircuitar.
4. **Los agentes CORE se ejecutan vía Python.** Los agentes EXTENDIDOS (ALCANCE / TÉCNICA / NEGOCIO / CONTROL / TMO) los ejecuta el Director leyendo su SKILL.md, analizando los outputs disponibles y escribiendo el resultado directamente en la carpeta de output del run.
5. **El core Python es la capa de ejecución** — los agentes lo invocan, no lo modifican.
6. **Un agente activo a la vez** — el Director informa al usuario qué agente está activo y qué acaba de producir.
7. **Todo output va a `output/<proyecto>/<run_id>/`** — la exploración completa (todos los repos y todas las ramas) se guarda siempre en `01_scout/`.
8. **Soporte multi-repo** — en una misma sesión se pueden analizar N repositorios.
9. **El informe Word se genera SIEMPRE al final** — después de completar todos los agentes (CORE + EXTENDIDOS), el Director ejecuta `generate_report.py` sin que el usuario tenga que pedirlo. Este paso es obligatorio y no opcional.

---

## Referencias Técnicas

- Plataformas Git soportadas → `references/platform-adapters.md`
- Componentes de análisis → `references/analysis-components.md`
