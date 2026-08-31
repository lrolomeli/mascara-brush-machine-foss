# Mapa Modbus Generico - Variables Logicas

Todas las vistas del HMI referencian estas variables por **nombre simbolico**.
El archivo de perfil del PLC (JSON) define la direccion fisica real para cada una.

## Coils (Lectura/Escritura Digital)

| Nombre Symbolico | Uso                         | Valores |
|------------------|-----------------------------|---------|
| CMD_START        | Boton Inicio                | 0/1     |
| CMD_CYCLE_STOP   | Paro fin de ciclo           | 0/1     |
| CMD_PAUSE        | Pausa                       | 0/1     |
| CMD_ESTOP        | Paro de emergencia          | 0/1     |
| MODE_AUTO        | Seleccion modo automatico   | 0/1     |
| MODE_MANUAL      | Seleccion modo manual       | 0/1     |
| MODE_STEP        | Seleccion modo paso a paso  | 0/1     |
| MODE_DEBUG       | Seleccion modo depuracion   | 0/1     |
| VALVE_1          | Valvula neumatica 1         | 0/1     |
| VALVE_2          | Valvula neumatica 2         | 0/1     |
| VALVE_3          | Valvula neumatica 3         | 0/1     |
| VALVE_4          | Valvula neumatica 4         | 0/1     |
| VALVE_5          | Valvula neumatica 5         | 0/1     |
| VALVE_6          | Valvula neumatica 6         | 0/1     |
| VALVE_7          | Valvula neumatica 7         | 0/1     |
| VALVE_8          | Valvula neumatica 8         | 0/1     |
| VALVE_9          | Valvula neumatica 9         | 0/1     |
| VALVE_10         | Valvula neumatica 10        | 0/1     |
| SERVO_JOG_FWD    | Servo jog adelante          | 0/1     |
| SERVO_JOG_REV    | Servo jog reversa           | 0/1     |

## Discrete Inputs (Lectura Digital)

| Nombre Symbolico | Uso                         | Valores |
|------------------|-----------------------------|---------|
| SENSOR_1         | Sensor inductivo/optico 1   | 0/1     |
| SENSOR_2         | Sensor inductivo/optico 2   | 0/1     |

## Holding Registers (Lectura/Escritura Analogica)

| Nombre Symbolico  | Uso                                    | Rango      |
|-------------------|----------------------------------------|------------|
| SERVO_SPEED       | Velocidad objetivo servo (RPM)         | 0-3000     |
| SERVO_POS_TARGET  | Posicion objetivo servo (unidades)     | 0-65535    |
| STEP_NUMBER       | Numero de paso actual (modo Paso)      | 0-999      |
| MACHINE_STATE     | Estado maquina (enum)                  | 0-4        |

### MACHINE_STATE - Codificacion

| Valor | Estado    |
|-------|-----------|
| 0     | Off       |
| 1     | Automatico|
| 2     | Manual    |
| 3     | Paso      |
| 4     | Depuracion|

## Input Registers (Lectura Analogica)

| Nombre Symbolico    | Uso                                  | Rango      |
|---------------------|--------------------------------------|------------|
| SERVO_POS_ACTUAL    | Posicion actual servo (unidades)     | 0-65535    |
| SERVO_ACTUAL_SPEED  | Velocidad actual servo (RPM)         | 0-3000     |
| SERVO_TORQUE        | Torque actual servo (%)              | 0-100      |
