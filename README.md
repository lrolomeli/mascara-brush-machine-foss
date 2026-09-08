# HMI Industrial — Máquina Ma1 (Cepilladora / Brush Mask)

> **Para agentes de desarrollo (vibe coding):** lee primero [`VCG.md`](VCG.md) —
> contiene la guía del proyecto con qué archivo modificar según la tarea.

HMI industrial **PLC-agnóstico** (Python + PySide6 + pymodbus) para la reprogramación
y control de una cepilladora/máscara brush ("Ma1"). Se comunica con el PLC por
**Modbus TCP** y el mapeo de variables es totalmente configurable por perfil JSON,
de modo que **cambiar de PLC no requiere tocar el código**.

El PLC ejecuta una rutina en **Structured Text** (ST) con dos máquinas de estado
paralelas (rama Alambre y rama Pinza), sincronizadas y con multiplexor
Auto/Manual para forzar salidas desde el HMI.

---

## Características

- **HMI PLC-agnóstico**: perfiles de direccionamiento cargados desde JSON.
  Perfil actual: `generic_kinco` (Kinco K5s / **K615S 16DT**).
- **Comunicación Modbus TCP** con polling configurable (100 ms por defecto),
  reconexión automática y worker en hilo (`QThread`).
- **5 pestañas de operación** (ver [Interfaz](#interfaz-hmi)).
- **Fuerza manual individual** de cada salida física (~19 salidas) con panel de
  sensores en vivo para depuración.
- **Alarmas dinámicas** con timestamp en barra superior central.
- **Selector de modo** MANUAL/AUTOMATIC en panel de controles.
- **Rutina ST** de la máquina real portada y corregida en `plc/generic_main.st`.
- Tema oscuro industrial, pantalla completa 1920×1080.

---

## Arquitectura

```
┌────────────────────────────  HMI (Python/Qt)  ────────────────────────────┐
│  hmi/main.py        → entrada, carga config, arranca QApplication          │
│  hmi/ui/main_window.py → ventana principal + AlarmBar + pestañas            │
│  hmi/ui/views/*     → ManualView, ServoView, OutputsDebugView,             │
│                       SensorsView, DebugView, SettingsView                   │
│  hmi/ui/widgets.py  → ModeToggle, ValveToggle, IndustrialButton,            │
│                       ServoPositionDisplay, AlarmCard, SimpleLED             │
│  hmi/comms/plc_adapter.py → capa Modbus TCP + PLCProfile (lee perfil JSON) │
│  hmi/comms/modbus_worker.py → hilo de polling y cola de lecturas/escritas   │
└────────────────────────────────────────────────────────────────────────────┘
                                  │  Modbus TCP
┌─────────────────────────────────▼──────────────────────────────────────────┐
│  PLC Kinco (K5s / K615S 16DT)  —  Structured Text                          │
│  plc/generic_main.st → 2 ramas paralelas + multiplexor SEL(AUTO, CMD)      │
└────────────────────────────────────────────────────────────────────────────┘
```

**Flujo de datos:**
1. El HMI referencia **nombres simbólicos** (`S5_START`, `CMD_Y3`, `Paso_Pinza`, …).
2. El archivo de perfil (`config/plc_profiles/*.json`) define la **dirección física**
   Modbus de cada nombre.
3. El `ModbusWorker` hace polling de las entradas y encola las escrituras.
4. El PLC calcula cada salida como un multiplexor `SEL(S_MANUAL, Auto_Yn, CMD_Yn)`:
   automático (secuencia) o forzado manual (desde el HMI).

---

## Requisitos

- Python **3.10+**
- OS: Linux (se desarrolla contra pantalla táctil 1920×1080)
- PLC con soporte Modbus TCP y Structured Text

### Dependencias (`requirements.txt`)

```
PySide6 >= 6.6
pymodbus >= 3.6
```

---

## Instalación

```bash
git clone git@github.com:lrolomeli/mascara-brush-machine-foss.git
cd mascara-brush-machine-foss
# Crea el venv e instala dependencias (lo hace también run_hmi.sh)
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

---

## Uso

### 1. Simulador (sin PLC físico)

Para probar el HMI sin PLC, inicia un servidor Modbus simulado con datos de demo:

```bash
./run_simulator.sh 0.0.0.0 5020 generic_kinco
```

El simulador responde con sensores de demo activos (S8, S14, S15, S23) y algunas
salidas (Y14, Y24, M1).

### 2. HMI

```bash
./run_hmi.sh
```

> Por defecto lee `config/app_config.json`, que apunta al PLC real
> (`192.168.1.10:502`). Para probar contra el simulador, cambia la IP/puerto a
> `127.0.0.1:5020` en la pestaña **Configuración**, o edita temporalmente el JSON.

---

## Interfaz HMI

### Layout Principal

```
┌────────────────────────────────────────────────────────┐
│ SIDEBAR │            ALARM BAR (cuando hay alarmas)    │ CONTROLS │
│  (NAV)  │──────────────────────────────────────────────│  PANEL   │
│         │                                               │          │
│         │              PESTANA ACTIVA                  │          │
│         │              (MAIN CONTENT)                   │          │
│         │                                               │          │
└─────────┴───────────────────────────────────────────────┴──────────┘
```

### Pestañas de Navegación

| Pestaña              | Descripción                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| **Depuracion por pasos** | Displays de paso (Alambre/Pinza) + botón PASO SIGUIENTE                   |
| **Servo**            | Control de velocidad, posición y modo Jog del servomotor (reservado).        |
| **Sensores**         | Vista en vivo de todos los sensores con LEDs indicadores y nombres completos.|
| **Actuadores**       | Forzado individual de cada salida (Y*/M*) + warning si no está en Manual.   |
| **Depuracion**       | Lectura/escritura directa de cualquier tag + log de operaciones.             |
| **Configuracion**    | Selección de perfil de PLC, IP/puerto y test de conexión.                    |

### Panel de Controles (lado derecho)

```
┌─────────────────────┐
│     CONTROLES        │
│  ─────────────────── │
│  [MODE: MANUAL|AUTO] │  ← Toggle selector de modo
│  ─────────────────── │
│       RESET          │  ← 100px altura, gris
│       PARO           │  ← 100px altura, ROJO
│       INICIO         │  ← 100px altura, verde (solo en AUTOMATIC)
│  ─────────────────── │
│  [ ] CONTINUO        │  ← solo en AUTOMATIC
│  [ ] DEBUG           │  ← solo en MANUAL
└─────────────────────┘
```

**Lógica del ModeToggle:**
- Solo habilitable cuando la máquina está en RESET (`Paso_Alambre == 0` y `Paso_Pinza == 0`)
- En modo AUTOMATIC: muestra INICIO y CONTINUO, oculta DEBUG
- En modo MANUAL: muestra DEBUG, oculta INICIO y CONTINUO
- DEBUG checkbox deshabilitado si CONTINUO está activo

### AlarmBar (barra superior central)

- **Visible**: solo cuando hay alarmas activas
- **Oculta**: cuando no hay alarmas
- **Botón "Limpiar"**: borra visualmente las alarmas (reaparecen si la condición física sigue activa)
- **Formato**: `⚠ Nombre Alarma HH:MM:SS`
- **Alarma configurable**: H3 (Falta Nylon), H8 (Presión Baja)

---

## Perfil de PLC (JSON)

Cada perfil en `config/plc_profiles/` define el mapeo simbólico → dirección Modbus:

```json
{
  "name": "Kinco (Genérico ST)",
  "tags": {
    "CMD_START":  { "type": "coil", "address": 0, "description": "Boton Arranque" },
    "S13":        { "type": "discrete_input", "address": 13, "description": "Sensor cepillo cortado" },
    "CMD_Y3":     { "type": "coil", "address": 102, "description": "Forzado manual Y3 chucks" },
    "Paso_Pinza": { "type": "holding_register", "address": 401, "description": "Estado rama pinza" }
  }
}
```

Perfiles incluidos:
- `generic_kinco.json` — **activo**. Kinco genérico (K5s / K615S 16DT), 95 tags.
- `generic_modbus.json` — perfil genérico de referencia.
- `delta_dvp.json` — ejemplo Delta DVP.

Selecciona el perfil activo en `config/app_config.json` o en la pestaña Configuración.

---

## Coils de Control (Modo)

| Tag | Address | Descripción |
|-----|---------|-------------|
| `MODE_AUTO` | 4 | Activar modo automático |
| `MODE_MANUAL` | 5 | Activar modo manual |
| `MODE_STEP` | 6 | Modo paso a paso |
| `MODE_DEBUG` | 7 | Flag de debug |
| `S4_CONTINUOUS` | - | Ciclo continuo |
| `CMD_PAUSE` | - | Reset/Pause |
| `CMD_START` | - | Inicio de ciclo |
| `CMD_CYCLE_STOP` | - | Paro de ciclo |
| `BTN_STEP` | - | Botón paso siguiente |

---

## Documentación

- [`docs/modbus_generic_map.md`](docs/modbus_generic_map.md) — mapa detallado de
  variables, direcciones y secuencia de la máquina.
- [`docs/requirements.md`](docs/requirements.md) — requisitos de hardware y modos.
- [`plc/generic_main.st`](plc/generic_main.st) — rutina ST de trabajo del PLC
  (portada y corregida; 2 ramas paralelas + multiplexor Auto/Manual).
- [`docs/maquina_referencia.md`](docs/maquina_referencia.md) — referencia de
  diseño y depuración de la máquina: I/O real, tablas de pasos (rama paralela y
  secuencia de depuración) y forzado manual de salidas.

---

## Test

```bash
# Levanta un simulador interno y valida escritura/lectura del adapter
.venv/bin/python tests/test_adapter.py
```

---

## Seguridad

- **E-Stop** debe detener todos los actuadores de forma inmediata.
- El PLC valida que E-Stop esté desactivado antes de permitir el arranque.
- El estado de la máquina se reporta al HMI en cada ciclo de polling.
- Trabajar siempre en modo manual con las protecciones de la máquina activas
  al forzar salidas.
- El toggle de modo (MANUAL/AUTOMATIC) solo está habilitado cuando la máquina
  está en estado de RESET.

---

## Estado del Proyecto (Septiembre 2026)

### Completado
- [x] Interfaz HMI con tema oscuro industrial
- [x] Comunicación Modbus TCP con polling
- [x] Vista de Sensores con LEDs y nombres completos
- [x] Vista de Actuadores con toggles para forzar salidas
- [x] Vista Depuracion por pasos (Paso Alambre, Paso Pinza, botón PASO SIGUIENTE)
- [x] AlarmBar dinámica con timestamps y botón limpiar
- [x] ModeToggle MANUAL/AUTOMATIC con lógica de visibilidad
- [x] Panel de controles con RESET, PARO (rojo), INICIO, CONTINUO, DEBUG
- [x] Conexión desconexión visual en sidebar
- [x] Perfil generic_kinco con mapeo completo de tags

### En Progreso
- [ ] Pruebas de integración con PLC físico
- [ ] Ajuste fino de tiempos de polling

### Pendiente
- [ ] Vista Servo (reservada para future implementation)
- [ ] Validación de seguridad E-Stop en HMI
- [ ] Historial de alarmas (persistencia)
