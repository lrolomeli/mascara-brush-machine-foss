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

| Nombre HMI (abstracto) | Nombre real (Kinco) | Tipo   | Descripcion                       |
|------------------------|---------------------|--------|-----------------------------------|
| CMD_START              | S5_START            | coil   | Boton Arranque                    |
| CMD_CYCLE_STOP         | S3_STOP             | coil   | Boton Paro                        |
| CMD_ESTOP              | S1_EMERGENCY_STOP   | coil   | Paro de emergencia (NC)           |
| -                      | S4_CONTINUOUS       | coil   | Selector ciclo continuo           |
| -                      | S2_SINGLE           | coil   | Selector ciclo unico              |
| MODE_MANUAL            | S_MANUAL            | coil   | Selector modo manual              |
| MODE_STEP              | S_STEP_BY_STEP      | coil   | Selector modo paso a paso         |
| -                      | BTN_STEP            | coil   | Boton avance de paso              |

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

| Tag          | Tipo            | Descripcion            |
|--------------|-----------------|------------------------|
| Paso_Alambre | holding reg 400 | Estado rama alambre    |
| Paso_Pinza   | holding reg 401 | Estado rama pinza      |
| MACHINE_STATE| holding reg 402 | Estado de maquina (HMI)|
| SERVO_SPEED  | holding reg 410 | Velocidad servo (reservado) |
| SERVO_POS_TARGET | holding 411 | Posicion target (reservado) |
| SERVO_POS_ACTUAL  | input reg 400 | Posicion actual (reservado) |
| SERVO_ACTUAL_SPEED| input reg 401 | Velocidad actual (reservado)|
| SERVO_TORQUE      | input reg 402 | Torque actual (reservado)  |

## Secuencia de la maquina (2 ramas paralelas)

1. **Rama Alambre** (`Paso_Alambre`): prepara alambre/cerda.
2. **Rama Pinza** (`Paso_Pinza`): pinza, chucks, giro, rasurado, tijera.
3. **Sincronizacion**: la rama alambre espera en `Paso_Alambre=50` a que
   `S16` (pinza arriba) y `S20` (lengueta) esten activos.
4. **Fin de ciclo**: `Paso_Pinza=90` cierra el ciclo con `S13` (cepillado
   cortado).
