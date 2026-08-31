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
