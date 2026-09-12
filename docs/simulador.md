# Simulador Modbus TCP para Ma1

Servidor Modbus TCP que simula el comportamiento de la máquina Ma1 con sensores
dinámicos y timers. Permite probar el HMI sin PLC físico.

---

## 1. Uso Rápido

### Arrancar el Simulador

```bash
.venv/bin/python tests/run_simulator.py [ip] [puerto] [perfil]

# Ejemplo:
.venv/bin/python tests/run_simulator.py 127.0.0.1 5020 generic_kinco
```

### Comandos Interactivos

Mientras el simulador está corriendo, escribe:

| Comando | Descripción |
|---------|-------------|
| `h3` | Toggle alarma H3 (falta nylon) |
| `h8` | Toggle alarma H8 (baja presión) |
| `s` | Mostrar estado actual |
| `q` | Salir |

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

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│  SimulatedPLC (tests/run_simulator.py)                     │
│                                                             │
│  _actuator_states : dict[str, bool]  Y6=ON, Y9=OFF...   │
│  _discrete_inputs  : dict[int, bool]   S8=ON, S14=ON... │
│  _active_timers   : dict[str, float]  Y6_return=1.2s   │
│  _y9_position      : int  (0=abajo, 1=int, 2=arriba)     │
│                                                             │
│  activate_actuator("Y6")  → inicia timer → sensor cambia │
│  tick() cada 100ms  → decrementa timers                 │
│  plc_action_callback()  → intercepta lecturas Modbus       │
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

### Flujo de Datos

```
HMI → read_discrete_inputs(14, count=1)
    → SimDevice recibe request
    → SimDevice.call(action)
    → plc_action_callback(fc=2, addr=14, registers=[...])
    → _update_di() consulta _discrete_inputs[14] = True
    → modifica registers para poner bit 14 en 1
    → SimDevice devuelve respuesta
    → HMI recibe S14 = ON
```

---

## 3. Comportamiento de Actuadores

### Tabla de Actuadores, Sensores y Timers

| Actuador | Posición Inicial | Sensor Inicial | Sensor Final | Sensor Intermedio | Timer (s) | Regresa? |
|----------|-----------------|---------------|--------------|-------------------|-----------|----------|
| Y1  | Retraído | — | S9 | — | 1.0 | No |
| Y6  | Arriba | **S11** | — | — | 2.5 | **Sí** |
| Y7  | Abajo | — | S12 | — | 2.0 | **Sí** |
| Y8  | NC (muelle) | — | — | — | 0.5 | Automático |
| Y9  | Abajo | **S14** | **S16** | **S10** | 0.5 | No (3 pos) |
| Y10 | — | — | — | — | 0.5 | No |
| Y11 | Retraído | **S15** | — | — | 1.0 | **Sí** |
| Y12 | Adentro | **S17** | — | — | 1.0 | **Sí** |
| Y14 | — | — | — | — | 0.5 | No |
| Y15 | Retraído | **S18, S21** | S19 | — | 2.5 | **Sí** |
| Y16 | Retraído | — | S20 | — | 1.5 | **Sí** |
| Y17 | Retraído | — | — | — | 0.3 | **Sí** |
| Y18 | Retraído | — | S22 | — | 1.0 | **Sí** |
| Y24 | — | — | — | — | 1.5 | No |
| Y25 | — | — | — | — | 1.5 | No |
| M1  | OFF | — | — | — | 2.0 | No |
| M2  | OFF | — | — | — | 3.0 | No |
| M3  | **ON** | — | — | — | — | Siempre ON |

### Lógica de Actuadores con Retorno por Timer

```
Ejemplo: Y6 (Rasurado)

Posición INICIAL: Arriba
  → Sensor S11 = ON

Cuando se activa Y6 (Y6=ON):
  1. Y6 baja
  2. Sensor S11 = OFF (sale de posición inicial)
  3. Timer corre (2.5s)
  4. Timer termina → Y6 regresa arriba
  5. Sensor S11 = ON (llegó a posición inicial)
```

Esto aplica para: **Y6, Y7, Y11, Y12, Y15, Y16, Y17, Y18**

### Lógica de Y9 (3 Posiciones)

Y9 controla el cilindro múltiple de la pinza con sensor en cada posición:

```
Estado inicial: S14=ON (pinza ABAJO, home)

Y9=ON (subiendo):
  0.0s → S14=OFF, S10=OFF, S16=OFF
  0.5s → S14=OFF, S10=ON,  S16=OFF   (posición intermedia)
  1.0s → S14=OFF, S10=OFF, S16=ON   (ARRIBA)

Y9=OFF (bajando):
  0.0s → S16=OFF
  0.3s → S16=OFF, S10=ON   (intermedia)
  0.6s → S16=OFF, S10=OFF, S14=ON   (ABAJO = home)
```

**Nota:** S10 es solo lectura, no activa nada directamente. La secuencia de la
máquina lo usa como condición para avanzar (Paso_Pinza 30→40).

### Actuadores Sin Sensor (Timer Puro)

**Y8, Y10, Y14, Y17** — Estos no tienen ningún sensor. Cuando se activan,
el timer corre y cuando termina, simplemente se apagan (o regresan si tienen
retorno por muelle).

---

## 4. Alarmas

| Alarma | Tag Modbus | Condición Física | Toggle |
|--------|------------|-----------------|--------|
| Baja presión | H8 | `NOT S23` | `h8` |
| Falta nylon | H3 | `S8` | `h3` |

Por defecto están en modo **AUTO** (calculadas desde los sensores).
Cuando usas `h3` o `h8`, pasas a modo **ON/OFF forzado**.

---

## 5. Sensores Iniciales (al Arrancar)

| Sensor | Valor | Descripción |
|--------|-------|-------------|
| S8  | ON | Sensor de cerda/nylon |
| S14 | ON | Pinza abajo (home) |
| S15 | ON | Pinza retraída (home) |
| S23 | ON | Presencia de presión neumática |

---

## 6. Timers (valores actuales)

```python
TIMERS = {
    "Y1":  1.0,
    "Y6":  2.5,
    "Y7":  2.0,
    "Y8":  0.5,
    "Y9":  0.5,
    "Y10": 0.5,
    "Y11": 1.0,
    "Y12": 1.0,
    "Y14": 0.5,
    "Y15": 2.5,
    "Y16": 1.5,
    "Y17": 0.3,
    "Y18": 1.0,
    "Y24": 1.5,
    "Y25": 1.5,
    "M1":  2.0,
    "M2":  3.0,
}
```

El ciclo completo dura aproximadamente **6 segundos**.

Para ajustar los timers, edita `tests/run_simulator.py` línea ~37.

---

## 7. Próximos Ajustes

### A. Tiempos de Timers

Cuando tengas los valores reales, edita el diccionario `TIMERS` en
`tests/run_simulator.py`:

```python
TIMERS = {
    "Y6":  2.5,  # ← ajustar aquí
    ...
}
```

### B. Agregar Más Sensores

Edita `ACTUATOR_CONFIG` en `tests/run_simulator.py`:

```python
ACTUATOR_CONFIG = {
    "Y6": {"initial": "S11", "final": None, "returns": True},
    ...
}
```

### C. Secuencia Automática

Actualmente los actuadores se activan manualmente. Para simular la rutina
completa, necesitarías agregar la lógica de la máquina de estados que activa
actuadores automáticamente basándose en los pasos (`Paso_Alambre`, `Paso_Pinza`).

---

## 8. Archivos Relacionados

| Archivo | Descripción |
|---------|-------------|
| `tests/run_simulator.py` | Servidor simulado completo |
| `docs/maquina_referencia.md` | Documentación de la máquina y actuadores |
| `config/plc_profiles/generic_kinco.json` | Perfil con mapeo de tags Modbus |

---

## 9. Solución de Problemas

### HMI no conecta al simulador

1. Verifica que el simulador esté corriendo
2. Verifica que la IP/puerto coincida con `config/app_config.json`
3. Intenta hacer ping al servidor: `ping 127.0.0.1`

### Sensores no cambian

1. Verifica que el timer haya terminado (revisa con comando `s`)
2. Verifica que estés leyendo la dirección correcta del sensor
3. Revisa el log del simulador para errores

### Client disconnected

El servidor Modbus cierra conexiones inactivas. El HMI debe hacer polling
regular para mantener la conexión.
