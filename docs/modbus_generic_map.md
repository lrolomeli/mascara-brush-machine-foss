# Mapa Modbus - Maquina Ma1 (Cepilladora / Brush Mask)

Este documento describe el mapeo de variables logicas (nombres simbolicos)
utilizadas por el HMI, y su correspondencia con las variables reales del
PLC Kinco (generico: K5s / K615S 16DT) via el perfil `config/plc_profiles/generic_kinco.json`.

El HMI referencia **nombres simbolicos**; el archivo de perfil define la
direccion fisica Modbus para cada nombre. Cambiar de PLC = cambiar de perfil,
sin tocar el codigo del HMI.

## Esquema de control de salidas (multiplexor Auto/Manual)

El PLC calcula cada salida fisica con un multiplexor:

    Yn := SEL(S_MANUAL, Auto_YN, CMD_YN)

- `S_MANUAL = 0` (automatico): la salida sigue la secuencia (`Auto_YN`).
- `S_MANUAL = 1` (manual): la salida se fuerza desde el HMI (`CMD_YN`).

Las memorias `CMD_*` son coils que el HMI escribe para forzar salidas.
Las memorias `Auto_*` son calculadas por la logica ST del PLC.

## Entradas de control (Botonera / Selectores)

| Nombre HMI | Tipo   | Direccion | Descripcion                       |
|------------|--------|-----------|-----------------------------------|
| CMD_START  | coil   | 0         | Boton Arranque                    |
| CMD_PAUSE  | coil   | 1         | Reset/Pause                       |
| CMD_CYCLE_STOP | coil | 2         | Boton Paro                        |
| MODE_AUTO  | coil   | 4         | Selector modo automatico          |
| MODE_MANUAL | coil  | 5         | Selector modo manual              |
| MODE_STEP  | coil   | 6         | Selector modo paso a paso         |
| MODE_DEBUG | coil   | 7         | Flag modo debug                   |
| S4_CONTINUOUS | coil | -         | Selector ciclo continuo           |
| BTN_STEP   | coil   | -         | Boton avance de paso              |

> **Nota E-stop**: el IL usa **`%M0.3`** como condicion de emergencia (`0` = activa).
> En Modbus eso es el **coil 3** (`CMD_ESTOP`). El paro fisico es `%I0.2`
> (`S1_EMERGENCY_STOP`, discrete input 24) y **aun no se espeja** a `%M0.3`
> (pendiente de hardware, ver `docs/pendientes.md`).

## Sensores (Discrete Inputs)

| Tag real | Direccion | Descripcion                            |
|----------|-----------|----------------------------------------|
| S8       | 8         | Sensor de cerda/nylon                  |
| S9       | 9         | Sensor orientador/fin de alambre       |
| S10      | 10        | Sensor pinza posicionada               |
| S11      | 11        | Sensor rasurador listo                 |
| S12      | 12        | Sensor tijera arriba                   |
| S13      | 13        | Sensor cepillo cortado (fin de ciclo)  |
| S14      | 14        | Sensor pinza abajo                     |
| S15      | 15        | Sensor pinza fuera                     |
| S16      | 16        | Sensor pinza arriba                    |
| S17      | 17        | Sensor pinza adentro                   |
| S18      | 18        | Sensor cuchilla/dobla alambre          |
| S19      | 19        | Sensor regresa dobla alambre           |
| S20      | 20        | Sensor lengueta final carrera          |
| S21      | 21        | Sensor peine/fin alambre atras         |
| S22      | 22        | Sensor empuja alambre adelante         |
| S23      | 23        | Sensor presion neumatica               |

## Forzado manual de salidas (CMD, coils)

El HMI escribe a estas memorias para forzar salidas en modo manual.

| Tag      | Direccion | Salida que fuerza |
|----------|-----------|-------------------|
| CMD_Y1   | 100       | Y1 orientadores   |
| CMD_Y3   | 102       | Y3 chucks         |
| CMD_Y6   | 105       | Y6 cabezal rasurado |
| CMD_Y7   | 106       | Y7 tijera         |
| CMD_Y8   | 107       | Y8 abre/cierra tijera |
| CMD_Y9   | 108       | Y9 sube/baja pinza|
| CMD_Y10  | 109       | Y10 abre/cierra pinza |
| CMD_Y11  | 110       | Y11 centrar pinza |
| CMD_Y12  | 111       | Y12 meter/sacar pinza |
| CMD_Y14  | 113       | Y14 rasador       |
| CMD_Y15  | 114       | Y15 peine/dobladora |
| CMD_Y16  | 115       | Y16 lengueta      |
| CMD_Y17  | 116       | Y17 cizalla alambre |
| CMD_Y18  | 117       | Y18 empujar alambre |
| CMD_Y24  | 123       | Y24/CACHADOR      |
| CMD_M1   | 200       | M1 retorcido      |
| CMD_M2   | 201       | M2 rasurado       |
| CMD_M3   | 202       | M3 aspirado       |

## Salidas fisicas (Coils, escritas por el PLC)

| Tag | Direccion | Descripcion    |
|-----|-----------|----------------|
| Y1  | 1000      | Orientadores   |
| Y3  | 1002      | Chucks         |
| Y6  | 1005      | Cabezal rasurado |
| Y7  | 1006      | Tijera         |
| Y8  | 1007      | Abre/cierra tijera |
| Y9  | 1008      | Sube/baja pinza|
| Y10 | 1009      | Abre/cierra pinza |
| Y11 | 1010      | Centrar pinza  |
| Y12 | 1011      | Meter/sacar pinza |
| Y14 | 1013      | Rasador        |
| Y15 | 1014      | Peine/dobladora|
| Y16 | 1015      | Lengueta       |
| Y17 | 1016      | Cizalla alambre|
| Y18 | 1017      | Empujar alambre|
| Y24 | 1023      | Cachador       |
| M1  | 1100      | Motor retorcido|
| M2  | 1101      | Motor rasurado |
| M3  | 1102      | Motor aspirado |
| H8  | 1200      | Alarma baja presion (NOT S23) |
| H3  | 1201      | Alarma nylon/cerda (S8) |

## Registros de estado (Holding/Input)

| Tag          | Tipo            | Direccion | Descripcion            |
|--------------|-----------------|-----------|------------------------|
| Paso_Alambre | holding reg 400 | Estado rama alambre    |
| Paso_Pinza   | holding reg 402 | Estado rama pinza (`%VW402`) |
| MACHINE_STATE| holding reg 404 | Estado de maquina (HMI)|
| SERVO_SPEED  | holding reg 410 | Velocidad servo (reservado) |
| SERVO_POS_TARGET | holding 411 | Posicion target (reservado) |
| SERVO_POS_ACTUAL  | input reg 400 | Posicion actual (reservado) |
| SERVO_ACTUAL_SPEED| input reg 401 | Velocidad actual (reservado)|
| SERVO_TORQUE      | input reg 402 | Torque actual (reservado)  |

> **Registros pares**: Kinco no admite `%VW` impares (`Error 041`); por eso
> `Paso_Pinza` esta en `%VW402` (no 401) y `MACHINE_STATE` se desplazo a 404.
> `STEP_NUMBER` es un alias de `Paso_Pinza` (misma direccion 402).

## Secuencia de la maquina (2 ramas paralelas)

1. **Rama Alambre** (`Paso_Alambre`): prepara alambre/cerda.
2. **Rama Pinza** (`Paso_Pinza`): pinza, chucks, giro, rasurado, tijera.
3. **Sincronizacion**: la rama alambre espera en `Paso_Alambre=50` a que
   `S16` (pinza arriba) y `S20` (lengueta) esten activos.
4. **Fin de ciclo**: `Paso_Pinza=90` cierra el ciclo con `S13` (cepillado
   cortado).

## Mapa de memoria del IL (fuente de verdad)

El programa `plc/generic_main.il` es la referencia; el perfil JSON y este
documento se alinean a el. Resumen del mapa propuesto en el propio IL:

| Grupo | Direccion IL | Modbus | Notas |
|-------|--------------|--------|-------|
| Botonera | `S5_START=%M0.0`, `S3_STOP=%M0.1`, `S1_EMERGENCY_STOP=%M0.3`, `S_MANUAL=%M0.5`, `S_STEP_BY_STEP=%M0.6` | coils 0,1,3,5,6 | E-stop en `%M0.3` |
| `BTN_STEP` | `%M2.4` | coil 20 | flanco en `%M60.0/%M60.1` |
| Sensores | `S8..S15=%M30.0..%M30.7`, `S16..S23=%M31.0..%M31.7` | discrete 8..23 | espejo de `%I1.0..%I2.7` |
| Forzado manual | `CMD_Y*=%M12.x..%M15.x`, `CMD_M*=%M25.x` | coils 100..202 | |
| Salidas deseadas | `%M50.0..%M52.4` | — | multiplexor Auto/Manual |
| Salidas fisicas | `Y1=%Q0.0` ... `H3=%Q2.4` | coils 1000+ | **verificar base `%Q`->coil en KincoBuilder** |

> **Pendiente de confirmar**: la correspondencia de `%Q` con coils Modbus
> (el perfil usa base `1000+`). El IL escribe `%Q` directo; hay que validar en
> KincoBuilder como expone el esclavo Modbus cada `%Qx.y`.
