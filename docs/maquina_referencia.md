# Referencia de la Máquina Ma1 (Cepilladora / Brush Mask)

Este documento consolida, en un solo lugar, la información de diseño y depuración
de los antiguos archivos `docs/ma1st.st`, `docs/ma1-rutina-debug.st`,
`docs/activacion-manual-valvula.st` y `docs/inoutmem.csv`, que fueron retirados
del repositorio.

> **Fuente canónica de producción:** `plc/generic_main.st` — rutina ST de trabajo
> actual (2 ramas paralelas + multiplexor Auto/Manual). Este documento es una
> **referencia de diseño y de depuración**; no debe considerarse el código vivo.

---

## 1. Entradas / Salidas reales (de `inoutmem.csv`)

Mapeo físico real de la máquina. La lista completa de direcciones Modbus está en
[`docs/modbus_generic_map.md`](modbus_generic_map.md).

### Entradas (botonera y selectores)

| Símb. | Nombre real                 | Descripción                              |
|-------|-----------------------------|------------------------------------------|
| S5    | START                       | Botón de arranque                        |
| S3    | STOP                        | Botón de paro                            |
| S1    | EMERGENCY_STOP              | Paro de emergencia (NC)                  |
| S4    | MODE_CONTINUOUS             | Selector ciclo continuo                  |
| S2    | MODE_SINGLE                 | Selector ciclo único                     |
| S_MAN | MODE_MANUAL                 | Selector modo manual                     |
| S_PASO| MODE_STEP_BY_STEP           | Selector modo paso a paso                |
| BTN_PASO | BTN_STEP                 | Botón avance único de paso               |

### Entradas (sensores)

| Símb. | Descripción                                   |
|-------|-----------------------------------------------|
| S18   | Sensor cuchilla / dobla alambre               |
| S21   | Sensor peine / fin alambre atrás              |
| S14   | Sensor pinza abajo                            |
| S9    | Sensor orientador / fin de alambre            |
| S19   | Sensor regresa dobla alambre                  |
| S22   | Sensor empuja alambre adelante                |
| S15   | Sensor pinza fuera                            |
| S10   | Sensor pinza posicionada / mitad de camino    |
| S20   | Sensor lengueta final de carrera              |
| S16   | Sensor pinza arriba                           |
| S17   | Sensor pinza adentro                          |
| S11   | Sensor rasurador bajando / posición tijera    |
| S12   | Sensor tijera arriba / cierre                 |
| S13   | Sensor cepillo cortado                        |
| S8    | Sensor de cerda                               |
| S23   | Sensor presión neumática                      |

### Salidas

| Símb.   | Descripción                                    |
|---------|------------------------------------------------|
| M1      | Motor giro principal / retorcido               |
| M2      | Motor rasurado                                 |
| M3      | Motor aspirado / succión                       |
| Y24     | Actuador peine / dobladora / cachador adelante |
| **Y25** | **Cachador atrás** (no mapeado en el perfil)   |
| Y1      | Válvula orientadores                           |
| Y17     | Válvula cizalla / alambre                      |
| Y3      | Abrir / cerrar chucks                          |
| Y18     | Empujar alambre adelante                       |
| Y10     | Abre / cierra pinza                            |
| Y11     | Centrar pinza / orientación                    |
| Y16     | Válvula lengueta                               |
| Y15     | Peine y dobladora de alambre                   |
| Y9      | Subir / bajar pinza                            |
| Y14     | Baja pinza a posición / rasador                |
| Y6      | Sube pinza / cabezal rasurado                  |
| Y12     | Sube cachador / meter o sacar pinza            |
| Y7      | Sube / baja tijera                             |
| Y8      | Abre / cierra tijera                           |
| Y_CUCH  | Y_CuchillaAlambre (cuchilla de alambre directa)|
| H8      | Alarma baja presión                            |
| H3      | Alarma nylon                                   |

### Temporizadores (TON)

| Símb. | Tiempo | Función                                        |
|-------|--------|------------------------------------------------|
| T27   | 2.5 s  | Arranque y orientación                         |
| T114  | 1.5 s  | Agarre y apertura pinza                        |
| T4    | 1.0 s  | Salida pinza                                   |
| T1    | 3.0 s  | Rasurado motor M2                              |
| T5    | 2.0 s  | Corte tijera / final                           |

---

## 2. Diseño original — dos ramas paralelas (de `ma1st.st`)

Estructura implementada en `plc/generic_main.st` (la versión de producción,
con las correcciones anotadas abajo). `Paso_Alambre` (izquierda, alambre/cerda)
y `Paso_Pinza` (derecha, pinza/giro) avanzan en paralelo y se sincronizan.

### Rama Alambre (`Paso_Alambre`)

| Paso | Acción / salidas                        | Condición para avanzar       |
|------|-----------------------------------------|------------------------------|
| 0    | Espera de inicio                        | `S5_START AND S14`           |
| 10   | Y15, Y14, Y9 ON                         | Sensor `S18`                 |
| 20   | Y17 ON (cizalla)                        | Sensor `S21`                 |
| 30   | Y17, Y15 OFF                            | Sensor `S19`                 |
| 40   | Y18 ON (empuja alambre)                 | Sensor `S22`                 |
| 50   | Y16 ON (lengueta) — **sincronización**  | `S20 (lengueta) AND S16 (pinza arriba)` |
| 60   | Y18 OFF, Y12 ON                         | Sensor `S17`                 |
| 70   | Y14 OFF, Y10 ON, Y16 OFF                | Timer `T_1T5`                |
| 80   | Y12 OFF — fin de ciclo alambre          | → 0                          |

### Rama Pinza (`Paso_Pinza`)

| Paso | Acción / salidas                        | Condición para avanzar       |
|------|-----------------------------------------|------------------------------|
| 0    | Espera de orientación                   | `Paso_Alambre >= 10 AND T_2T5.Q` |
| 10   | Y3 ON, Y10 OFF                          | Timer `T_1T3`                |
| 20   | Y11, Y12 OFF                            | Sensor `S15`                 |
| 30   | M1 ON, Y9 OFF                           | Sensor `S10` (M1 para con `T_2T4.Q`) |
| 40   | M2, Y6, Y11 ON; CATCHER OFF             | Timer `T_1T1` (rasurado)     |
| 50   | M2, Y6 OFF                              | Sensor `S11`                 |
| 60   | Y7 ON                                   | Sensor `S12` (tijera arriba) |
| 70   | Y8 ON (abre/cierra tijera)              | Timer `T_2T7`                |
| 80   | Y8 OFF                                  | Timer `T_2T6`                |
| 90   | Y7 OFF, CATCHER ON — **fin de ciclo**   | `S13` (cepillado cortado)    |

### Correcciones aplicadas en producción (`plc/generic_main.st`)

1. **Paso 90 de `Paso_Pinza`**: en el diseño original el paso quedaba colgado
   porque dependía del temporizador `T_NEW`, consultado en un paso distinto al
   que lo activaba. Se corrigió cerrando el ciclo con el sensor **`S13`**
   (cepillado cortado).
2. Se añadió **`M3` (aspirado)** al multiplexor (solo forzable manual).
3. Se añadieron las alarmas **`H8 := NOT S23`** (baja presión) y **`H3 := S8`**
   (nylon), y se mapeó la salida física real **`Y24` (CACHADOR)** en el mux.

---

## 3. Secuencia de depuración — máquina única (de `ma1-rutina-debug.st`)

Variante **secuencial (una sola máquina de estados)** `Paso` 0–100, pensada para
depurar el ciclo de forma lineal. Es **distinta** de la lógica de 2 ramas de
producción; sirve como referencia simplificada.

| Paso | Acción / salidas                        | Condición para avanzar       |
|------|-----------------------------------------|------------------------------|
| 0    | Espera de inicio                        | `START AND EMERGENCY_STOP`   |
| 10   | Y14, Y24 ON (arranque)                  | Timer `T27` (2.5 s)          |
| 20   | Y11 ON (orientación)                    | Sensor `S14`                 |
| 30   | Y3 ON (chucks)                          | Timer `T114` (1.5 s)         |
| 40   | Y10 ON (apertura pinza)                 | Timer `T4` (1.0 s)           |
| 50   | Y5 ON (salida pinza)                    | Sensor `S15`                 |
| 60   | M1, Y6 ON (giro y subida)               | Sensor `S10`                 |
| 70   | M2 ON (rasurado)                        | Timer `T1` (3.0 s)           |
| 80   | (preparación tijera)                    | Sensor `S11`                 |
| 90   | Y7, Y8 ON (corte tijera)                | Timer `T5` (2.0 s)           |
| 100  | Y12 ON (disparo final)                  | Sensor `S9` → `MODE_CONTINUOUS ? 10 : 0` |

Indicador de retención: `Falla_Bloqueante := (Paso > 0) AND NOT CondicionSiguiente`.

---

## 4. Forzado manual de cada salida (de `activacion-manual-valvula.st`)

Programa de diagnóstico para **activar cada salida una a una** desde el HMI.
La pestaña **"Depar. Salidas"** del HMI materializa este modo. Requiere
`MODE_MANUAL` (o `S_MANUAL`) ON y usa el multiplexor:

    Yn := SEL(MODE_MANUAL, Auto_YN, CMD_YN)

Salidas forzables (`CMD_*`, coils escritos por el HMI):

Y1, Y3, Y5, Y6, Y7, Y8, Y10, Y11, Y12, Y14, Y15, Y16, Y17, Y18, Y24, M1, M2
(y M3 en el perfil de producción).

> Nota: este esquema usa **`CMD_Y5`** (sale pinza); el perfil `generic_kinco.json`
> incluye `CMD_Y5` y `Y5` para soportarlo.

---

## 5. Correspondencia Actuador → Sensor(es) → Timer (simulación)

Documentación completa para el simulador (`tests/run_simulator.py`). Describe el
comportamiento físico de cada actuador, sus sensores de posición y timers.

### 5.1 Posición Inicial y Sensores

Cada actuador tiene una posición inicial (reposo). En esta posición, un sensor
puede estar ACTIVO (ON). Cuando el actuador opera, el sensor se DESACTIVA y un
timer comienza a correr. Cuando el timer termina, el actuador REGRESA a su
posición inicial y el sensor se reactiva.

**Excepción:** Y9 tiene 3 posiciones con sensor en cada una (no regresa
automáticamente, depende de la secuencia).

| Actuador | Posición Inicial | Sensor Pos. Inicial | Sensor Pos. Final | Sensor Intermedio | Timer (s) | Regresa? |
|----------|-----------------|--------------------|--------------------|-------------------|-----------|----------|
| Y1  | Retraído | — | S9 | — | 1.0 | No |
| Y6  | Arriba | S11 | — | — | 2.5 | **Sí** |
| Y7  | Abajo | — | S12 | — | 2.0 | **Sí** |
| Y8  | NC (muelle) | — | — | — | 0.5 | Automático |
| Y9  | Abajo | S14 | S16 | S10 | 0.5 | No (3 pos) |
| Y10 | — | — | — | — | 0.5 | No |
| Y11 | Retraído | S15 | — | — | 1.0 | **Sí** |
| Y12 | Adentro | S17 | — | — | 1.0 | **Sí** |
| Y14 | — | — | — | — | 0.5 | No |
| Y15 | Retraído | S18, S21 | S19 | — | 2.5 | **Sí** |
| Y16 | Retraído | — | S20 | — | 1.5 | **Sí** |
| Y17 | Retraído | — | — | — | 0.3 | **Sí** |
| Y18 | Retraído | — | S22 | — | 1.0 | **Sí** |
| Y24 | — | — | — | — | 1.5 | No |
| Y25 | — | — | — | — | 1.5 | No |
| M1  | OFF | — | — | — | 2.0 | No |
| M2  | OFF | — | — | — | 3.0 | No |
| M3  | **ON** | — | — | — | — | Siempre ON |

### 5.2 Comportamiento Detallado por Actuador

#### Y1 — Orientador
- **Sin sensor de posición inicial**
- Al activarse: va a posición final (extendido)
- Timer corre (1.0s)
- Timer termina: **NO regresa** (se queda extendido)
- Sensor final S9 se activa cuando está en posición final

#### Y6 — Cabezal Rasurado
- **Sensor S11 en posición inicial (arriba)**
- Al activarse: baja, S11 se DESACTIVA
- Timer corre (2.5s)
- Timer termina: **REGRESA arriba**, S11 se reactiva

#### Y7 — Tijera Arriba/Abajo
- **Sensor S12 en posición final (arriba)**
- Al activarse: sube
- Sensor S12 se activa cuando llega arriba
- Timer corre (2.0s)
- Timer termina: **REGRESA abajo**

#### Y8 — Abre/Cierra Tijera (Normally Closed)
- **Sin sensor**
- Es NC con retorno por muelle
- Al activarse: acciona (0.5s)
- Timer termina: **regresa por muelle automáticamente**

#### Y9 — Sube/Baja Pinza (3 Posiciones)
- **3 sensores: S14 (abajo), S10 (intermedio), S16 (arriba)**
- Posición inicial: S14=ON (abajo)

| Acción | Tiempo | Sensores Activos |
|--------|--------|------------------|
| Y9=ON (subiendo) | 0.0s | S14=OFF, S10=OFF, S16=OFF |
| | 0.5s | S14=OFF, S10=ON, S16=OFF (intermedio) |
| | 1.0s | S14=OFF, S10=OFF, S16=ON (arriba) |
| Y9=OFF (bajando) | 0.0s | S16=OFF |
| | deteka S10 | S10=ON momentáneamente |
| | llega abajo | S14=ON (regresa a posición inicial) |

- **S10 es solo lectura** — no activa nada directamente, pero la secuencia
  de la máquina lo usa como condición para avanzar (Paso_Pinza 30→40)

#### Y10 — Abre/Cierra Pinza
- **Sin sensor**
- Al activarse: acciona
- Timer corre (0.5s)
- Timer termina: **NO regresa** (se queda en la posición)

#### Y11 — Centrar Pinza
- **Sensor S15 en posición inicial (retraído)**
- Al activarse: extiende, S15 se DESACTIVA
- Timer corre (1.0s)
- Timer termina: **REGRESA a retraído**, S15 se reactiva

#### Y12 — Meter/Sacar Pinza
- **Sensor S17 en posición inicial (adentro)**
- Al activarse: sale, S17 se DESACTIVA
- Timer corre (1.0s)
- Timer termina: **REGRESA adentro**, S17 se reactiva

#### Y14 — Rasurado
- **Sin sensor**
- Al activarse: acciona
- Timer corre (0.5s)
- Timer termina: **NO regresa**

#### Y15 — Dobladora + Peine
- **Sensores S18 y S21 en posición inicial (retraído)**
- Al activarse: extiende hacia S19
- S18 y S21 se DESACTIVAN
- Timer corre (2.5s)
- Timer termina: **REGRESA a retraído**, S18 y S21 se reactivan

#### Y16 — Mecanismo Lengüeta
- **Sensor S20 en posición final (extendido)**
- Al activarse: extiende
- Sensor S20 se activa cuando llega
- Timer corre (1.5s)
- Timer termina: **REGRESA a retraído**

#### Y17 — Cizalla Alambre
- **Sin sensor**
- Al activarse: cizalla (corte rápido)
- Timer corre (0.3s)
- Timer termina: **REGRESA a posición inicial**

#### Y18 — Empujar Alambre
- **Sensor S22 en posición final (extendido)**
- Al activarse: empuja hacia adelante
- Sensor S22 se activa cuando llega
- Timer corre (1.0s)
- Timer termina: **REGRESA a retraído**

#### Y24 — Chucks/Cachador
- **Sin sensor**
- Al activarse: acciona
- Timer corre (1.5s)
- Timer termina: **NO regresa**

#### Y25 — Cachador Atrás
- **Sin sensor**
- Al activarse: acciona
- Timer corre (1.5s)
- Timer termina: **NO regresa**

#### M1 — Motor Giro (Retorcido)
- **Sin sensor**
- Al activarse: gira
- Timer corre (2.0s)
- Timer termina: **PARA** (no regresa a posición, simplemente se apaga)

#### M2 — Motor Rasurado
- **Sin sensor**
- Al activarse: gira
- Timer corre (3.0s)
- Timer termina: **PARA**

#### M3 — Motor Aspirado
- **Siempre ON** — no tiene timer, funciona mientras la máquina está activa

### 5.3 Tiempos de Timer (estimados para ciclo de ~6s)

| Timer | Duración (s) | Ubicación en Rutina |
|-------|---------------|---------------------|
| T_2T5 | 0.3 | Inicio orientación (Y15, Y14, Y9) |
| T_1T3 | 0.4 | Cierre chucks (Y3) |
| T_2T4 | 0.3 | Giro motor M1 |
| T_1T1 | 0.8 | Rasurado (M2, Y6) |
| T_1T5 | 0.3 | Posicionamiento final |
| T_2T7 | 0.4 | Tijera sube (Y7) |
| T_2T6 | 0.3 | Cierre tijera (Y8) |
| **Total** | **~2.8s** | |

El resto del ciclo (~3s) depende de sensores de FC.

### 5.4 Alarmas Configurables por el Simulador

| Alarma | Tag Modbus | Condición Física | Control |
|--------|------------|------------------|---------|
| Baja presión | H8 | `NOT S23` | Toggleable |
| Falta nylon | H3 | `S8` | Toggleable |

### 5.5 Estados Iniciales de Sensores (al arrancar el simulador)

| Sensor | Valor | Descripción |
|--------|-------|-------------|
| S8  | ON  | Sensor de cerda/nylon |
| S14 | ON  | Pinza abajo (home) |
| S15 | ON  | Pinza retraída (home) |
| S23 | ON  | Presencia de presión neumática |

### 5.6 Notas de Implementación para el Simulador

El simulador usa `SimDevice` de pymodbus con un `action callback` que intercepta
todas las lecturas Modbus. Cuando el HMI lee discrete inputs, el callback
consulta el estado actual de `_discrete_inputs` en `SimulatedPLC` y modifica
los registros antes de devolver la respuesta.

Para cambiar un sensor dinámicamente:
```python
# Ejemplo: poner S14 = True
bit_pos = 14 - start_address
reg_idx = bit_pos // 16
bit_idx = bit_pos % 16
current_registers[reg_idx] |= (1 << bit_idx)
```
