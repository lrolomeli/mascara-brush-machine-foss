# Simulador Modbus TCP para Ma1

Servidor Modbus TCP que simula la **planta física** (actuadores → sensores con
tiempos de carrera) y la **rutina del PLC** (dos máquinas de estado paralelas
portadas de `plc/generic_main.st`). Permite probar el HMI completo — ciclo
AUTO, paso a paso y forzado manual — sin PLC físico.

---

## 1. Uso Rápido

### Arrancar el Simulador

```bash
.venv/bin/python tests/run_simulator.py [ip] [puerto] [perfil]

# Ejemplo:
.venv/bin/python tests/run_simulator.py 127.0.0.1 5020 generic_kinco
```

Por defecto escucha en `0.0.0.0:5020` con el perfil `generic_kinco`.

### Comandos Interactivos

Mientras el simulador está corriendo, escribe:

| Comando | Descripción |
|---------|-------------|
| `h3` | Toggle alarma H3 (falta nylon) |
| `h8` | Toggle alarma H8 (baja presión) |
| `e`  | Toggle paro de emergencia (S1) |
| `s`  | Mostrar estado actual (pasos, actuadores, sensores, alarmas) |
| `q`  | Salir |

### Configurar el HMI

Edita temporalmente `config/app_config.json`:

```json
{
  "host": "127.0.0.1",
  "port": 5020,
  ...
}
```

**Importante:** Restaura la IP real después de probar.

### Probar la Rutina Automática

1. Arranca el simulador y el HMI.
2. En el HMI selecciona **modo Automático** (no Manual).
3. Pulsa **INICIO**. La rama alambre comienza: `Paso_Alambre` 0→10→…→80→0
   y la rama pinza 0→10→…→90→0, sincronizadas (la rama alambre espera en el
   paso 50 a `S16` y `S20`).
4. El ciclo completo tarda **~14 segundos**; en `Paso_Alambre=80`/ciclo
   terminado puede pulsar INICIO de nuevo, o usar modo continuo.

Para **paso a paso**: activa `MODE_STEP` (tag `S_STEP_BY_STEP`, ver
Sección 7) y pulsa `BTN_STEP` para avanzar de paso en paso.

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│  SimulatedPLC (tests/run_simulator.py)                     │
│                                                             │
│  Rutina PLC (scan cada 100ms):                             │
│    - Paso_Alambre / Paso_Pinza  (CASE del ST)             │
│    - TON del ST (T_2T5, T_1T3, ... con PT reales)         │
│    - Multiplexor  Yn = SEL(S_MANUAL, Auto_Yn, CMD_Yn)     │
│                                                             │
│  Planta fisica:                                            │
│    - _act_pos / _discrete / _active_timers                │
│    - TRAVEL (tiempos), PLANT (sensores por posicion)      │
│    - Y9 3 posiciones (S14/S10/S16)                        │
│  _coil_written / _coil_values (escrituras del HMI)        │
│  plc_action_callback()  → intercepta Modbus (fc 1/2/3/4)  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    action callback
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  SimDevice (pymodbus)                                     │
│  Bloque discrete inputs : addr 0-1999                      │
│  Bloque coils           : addr 0-1999                      │
│  Bloque holding regs    : addr 0-1999                      │
│  action = plc.plc_action_callback                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  StartTcpServer (pymodbus)                                │
│  Servidor Modbus TCP en ip:puerto                         │
│  HMI conecta y hace polling cada 100ms                    │
└─────────────────────────────────────────────────────────────┘
```

### Escrituras Interceptadas

El simulador intercepta las escrituras de la HMI (fc 5, 15, 6, 16) y las
interpreta según el tag:

- **Botones momentáneos** (se consumen): `CMD_START`/`S5_START` (addr 0),
  `CMD_CYCLE_STOP`/`S3_STOP` (addr 1), `BTN_STEP` (addr 20).
  `CMD_START` se refleja vía `_start_latch`: el botón se lee hasta que el ciclo
  arranca.
- **Modos**: `MODE_MANUAL` (addr 5), `MODE_STEP` (addr 6), `S4_CONTINUOUS`
  (addr 8). Permanecen.
- **Forzado manual**: `CMD_*` de cada actuador.

### Flujo de Datos

```
HMI → read_discrete_inputs(14, count=1)
    → SimDevice recibe request
    → SimDevice.call(action)
    → plc_action_callback(fc=2, addr=14, registers=[...])
    → _update_di() consulta _discrete[14] = True
    → modifica registers para poner bit 14 en 1
    → SimDevice devuelve respuesta
    → HMI recibe S14 = ON
```

---

## 3. Rutina del PLC (port de `generic_main.st`)

Son **dos máquinas de estado paralelas** dentro del mismo bloque automático
(`IF NOT S_MANUAL THEN ...`):

### Rama Alambre

```
Paso_Alambre
  0  : espera START latch y S14 (pinza abajo)
  10 : Y15, Y14, Y9 ON  → espera S18 (pasa previa)
  20 : Y17 ON           → espera S21
  30 : Y17, Y15 OFF     → espera S19 (previa regresó)
  40 : Y18 ON           → espera S22 (pelador)
  50 : Y16 ON           → espera S20 Y S16  (sincronización con pinza)
  60 : Y18 OFF, Y12 ON  → espera S17 (pinza adelante)
  70 : Y14 OFF, Y10 ON, Y16 OFF → espera T_1T5 (1.5s)
  80 : Y12 OFF, Y9 OFF  → vuelve a 0 (reinicia en continuo)
```

### Rama Pinza

```
Paso_Pinza
  0  : espera Paso_Alambre >= 10 y T_2T5 (2.5s)
  10 : Y3 ON, Y10 OFF  → espera T_1T3 (1.5s)  (cierre chucks)
  20 : Y11, Y12 OFF    → espera S15
  30 : M1 ON, Y9 OFF   → espera S10 O T_2T4 (giro M1); T_2T4 apaga M1
  40 : M2, Y6, Y11 ON ; catcher OFF → espera T_1T1 (3.0s, rasurado)
  50 : M2, Y6 OFF      → espera S11 (rasurado listo)
  60 : Y7 ON           → espera S12 (tijera arriba)
  70 : Y8 ON           → espera T_2T7 (2.0s, tiempo tijera)
  80 : Y8 OFF          → espera T_2T6 (1.5s, cierre tijera)
  90 : Y7 OFF, catcher ON → espera S13 (cepillado cortado) → Y3/catcher OFF → 0
```

### Temporizadores TON (PT reales del ST)

| Timer | IN (condición) | PT | Paso que espera |
|-------|----------------|-----|-----------------|
| T_2T5 | Paso_Alambre = 10 | 2.5s | Pinza 0→10 |
| T_1T3 | Paso_Pinza = 10  | 1.5s | Pinza 10→20 |
| T_2T4 | Paso_Pinza = 30  | 2.0s | apaga M1 |
| T_1T1 | Paso_Pinza = 40  | 3.0s | Pinza 40→50 |
| T_1T5 | Paso_Alambre = 70 | 1.5s | Alambre 70→80 |
| T_2T7 | Paso_Pinza = 60* | 2.0s | Pinza 70→80 |
| T_2T6 | Paso_Pinza = 80  | 1.5s | Pinza 80→90 |

\* Desviación documentada: el ST de producción gatea `T_2T7` con
`Paso_Pinza = 60` pero lo consume en el paso 70; al salir de 60 el TON se
reinicia y `Q` queda FALSO (cuelga). En el simulador se gatea en el paso que lo
espera (70), igual que `T_2T6`.

### Desviaciones y Notas vs. ST de producción

- `Auto_M3`: en AUTO el ST lo deja OFF (la secuencia no lo enciende); en manual
  se fuerza con `CMD_M3`. (Documentación antigua decía "M3 siempre ON".)
- Al terminar el ciclo de alambre (paso 80) el simulador retrae `Y9`. El ST no
  lo hace explícito y, sin esta retracción, `S14` nunca vuelve y el reinicio
  (continuo o un nuevo INICIO) queda colgado.
- Botones INICIO/PARO/RESET/STEP son pulsos (se consumen por la rutina).
- El operador de paso: cada transición requiere `(NOT S_STEP_BY_STEP OR flanco
  BTN_STEP)`.

---

## 4. Comportamiento de Actuadores (planta)

### Sensores por Posición (config `PLANT`)

La planta refleja los sensores según la posición de cada actuador:

| Actuador | Fwd (ON) | Home (OFF) | Notas |
|----------|----------|-----------|-------|
| Y1  | S9 | — | orientador (fuera del bloque auto) |
| Y5  | S15 | — | comparte sensor con Y11 |
| Y6  | — (S11 OFF) | **S11** | rasurado: baja y regresa |
| Y7  | **S12**, S13 OFF | S13 | tijera: S12 arriba / S13 cepillado cortado |
| Y11 | S15 OFF | **S15** | púa pinza |
| Y12 | **S17** | — | pinza adelante |
| Y15 | **S18**, **S21**, S19 OFF | **S19** | pasa previa |
| Y16 | **S20** | — | lengüeta |
| Y18 | **S22** | — | pelador |
| Y8, Y10, Y14, Y17, Y24, M1, M2, M3 | sin sensor | — | timer puro / motor |

Los sensores que gobierna un actuador aparecen en **ambas** posiciones (el
valor de la posición contraria se aplica al cambiar de posición).

### Lógica de Y9 (3 Posiciones)

Y9 controla el cilindro múltiple de la pinza con sensor en cada posición:

```
Estado inicial: S14=ON (pinza ABAJO, home)

Y9=ON (subiendo):
  0.0s → S14=OFF, S10=OFF, S16=OFF
  0.5s → S10=ON, S16=OFF        (posición intermedia)
  1.0s → S10=OFF, S16=ON        (ARRIBA)

Y9=OFF (bajando):
  0.0s → S16=OFF
  2.2s → S10=ON                 (intermedia, después de T_2T4 = apaga M1)
  2.8s → S10=OFF, S14=ON        (ABAJO = home)
```

**Nota:** S10 no activa nada directamente; la secuencia lo usa como condición
de avance (Paso_Pinza 30→40). La bajada pasa por S10 **después** de T_2T4
(2.0s) para respetar el apagado de M1 en el ST.

---

## 5. Alarmas

| Alarma | Tag Modbus | Condición Física | Toggle |
|--------|------------|-----------------|--------|
| Baja presión | H8 | `NOT S23` | `h8` |
| Falta nylon | H3 | `S8` | `h3` |

Por defecto están en modo **AUTO** (calculadas desde los sensores). Cuando usas
`h3` o `h8`, pasas a modo **ON/OFF forzado** hasta que simules otra vez.

---

## 6. Sensores Iniciales (al Arrancar)

| Sensor | Valor | Descripción |
|--------|-------|-------------|
| S8  | ON  | Sensor de cerda/nylon |
| S14 | ON  | Pinza abajo (home, Y9 en 0) |
| S15 | ON  | Pinza retraída (home, Y11) |
| S13 | ON  | Tijera abajo / cepillado cortado (home, Y7) |
| S11 | ON  | Rasurado arriba (home, Y6) |
| S19 | ON  | Pasa previa retraída (home, Y15) |
| S23 | ON  | Presencia de presión neumática |
| Discreta 24 | ON  | E-Stop libre (NC: ON = no pulsado) |
| S16, S17, S20, S22, S9, S12 | OFF | (actuadores en reposo) |

---

## 7. Modos de Operación desde el HMI

| Modo | Tag / Coil | Cómo se activa |
|------|-----------|----------------|
| Automático | `MODE_MANUAL` = False | Toggle de Modo en el HMI |
| Manual (forzado) | `MODE_MANUAL` = True | Toggle de Modo; las salidas siguen `CMD_*` |
| Paso a paso | `MODE_STEP` = True | Pestaña **Depuración** del HMI (no hay botón directo); avanzar con `BTN_STEP` |
| Continuo | `S4_CONTINUOUS` = True | Pestaña Depuración; el ciclo se reinicia solo |

Reset general: el ST resetea ambas ramas si `NOT S1_EMERGENCY_STOP` (E-Stop)
o pulsan PARO, o `MODE_MANUAL` = True, o RESET (`CMD_PAUSE`).

---

## 8. Timers (valores actuales)

Los TON del ST conservan los PT reales (ver Sección 3). Los tiempos de carrera
de la planta (`TRAVEL`) están ajustados para que cada condición sea alcanzable
(p. ej. S18 llega después de T_2T5, S10 después de T_2T4, y el alambre pasa por
el paso 50 antes de que la pinza baje S16):

```python
TRAVEL = {
    "Y1": 0.4,  "Y5": 0.4,  "Y6": 0.4,  "Y7": 0.4,  "Y8": 0.4,
    "Y10": 0.4, "Y11": 0.3, "Y12": 0.4, "Y14": 0.4,
    "Y15": {"fwd": 2.6, "home": 0.3},   # direcciones distintas
    "Y16": 0.1, "Y17": 0.4, "Y18": 0.2, "Y24": 0.4,
}
# Y9 (3 posiciones):
Y9_UP_MID   = 0.5
Y9_UP_END   = 1.0   # total
Y9_DOWN_MID = 2.2
Y9_DOWN_END = 2.8   # total
```

El ciclo completo dura aproximadamente **14 segundos**.

Para ajustar los tiempos, edita `TRAVEL`, `PLANT` y `Y9_*` en
`tests/run_simulator.py`.

---

## 9. Probar la Rutina

```bash
.venv/bin/python tests/test_routine_sim.py   # 6 casos: manual, AUTO, paso a paso, E-Stop, continuo, lectura Modbus
.venv/bin/python tests/test_adapter.py       # integración HMI/adapter con el simulador
```

Deberías ver `TEST RUTINA SIMULADOR PASADO CORRECTAMENTE`.

---

## 10. Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `tests/run_simulator.py` | Simulador completo (planta + rutina del PLC) |
| `tests/test_routine_sim.py` | Pruebas de la rutina simulada |
| `plc/generic_main.st` | Rutina Structured Text fuente (autoritativa) |
| `docs/maquina_referencia.md` | Documentación de la máquina y actuadores |
| `config/plc_profiles/generic_kinco.json` | Perfil con mapeo de tags Modbus |

---

## 11. Solución de Problemas

### HMI no conecta al simulador

1. Verifica que el simulador esté corriendo
2. Verifica que la IP/puerto coincida con `config/app_config.json`
3. Intenta hacer ping al servidor: `ping 127.0.0.1`

### La secuencia no avanza

1. Revisa `MODE_MANUAL`: en manual las salidas siguen `CMD_*`, no la rutina.
2. Revisa `MODE_STEP`: si está activo, cada paso espera `BTN_STEP`.
3. Si `E-Stop` está pulsado (`e` en el simulador) o PARO, el reset general
   mantiene los pasos en 0.
4. Revisa con el comando `s` del simulador: pasos, sensores y tiempos.

### Sensores no cambian

1. Verifica que el timer pueda terminar (revisa con comando `s`)
2. Verifica que estés leyendo la dirección correcta del sensor
3. Revisa el log del simulador para errores

### Client disconnected

El servidor Modbus cierra conexiones inactivas. El HMI debe hacer polling
regular para mantener la conexión.