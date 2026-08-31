// =============================================================================
// DELTA DVP - Programa Principal (ST)
// Equivalencias Modbus TCP <-> Direcciones Internas Delta
// =============================================================================
// Coils (M):         HMI -> PLC   :   CMD_START   -> M100
// Holding Regs (D):  HMI -> PLC   :   SERVO_SPEED -> D100
// Input Regs (D):    PLC -> HMI   :   SERVO_POS   -> D200 (lectura)
//
// IMPORTANTE: En Delta DVP los coils Modbus se mapean a registros M (auxiliares)
// Los holding registers se mapean a registros D (datos)
// =============================================================================

PROGRAM MAIN
VAR
    // --- Entradas desde HMI (Coils Modbus -> M) ---
    CMD_START       AT %M0  : BOOL;   // Boton Inicio
    CMD_CYCLE_STOP  AT %M1  : BOOL;   // Paro fin de ciclo
    CMD_PAUSE       AT %M2  : BOOL;   // Pausa
    CMD_ESTOP       AT %M3  : BOOL;   // Paro de emergencia
    MODE_AUTO       AT %M10 : BOOL;   // Modo automatico
    MODE_MANUAL     AT %M11 : BOOL;   // Modo manual
    MODE_STEP       AT %M12 : BOOL;   // Modo paso a paso
    MODE_DEBUG      AT %M13 : BOOL;   // Modo depuracion

    // --- Valvulas (Coils Modbus -> M) ---
    VALVE_1         AT %M100 : BOOL;
    VALVE_2         AT %M101 : BOOL;
    VALVE_3         AT %M102 : BOOL;
    VALVE_4         AT %M103 : BOOL;
    VALVE_5         AT %M104 : BOOL;
    VALVE_6         AT %M105 : BOOL;
    VALVE_7         AT %M106 : BOOL;
    VALVE_8         AT %M107 : BOOL;
    VALVE_9         AT %M108 : BOOL;
    VALVE_10        AT %M109 : BOOL;

    // --- Servo (Coils Modbus -> M) ---
    SERVO_JOG_FWD   AT %M200 : BOOL;
    SERVO_JOG_REV   AT %M201 : BOOL;

    // --- Sensores (Discrete Inputs -> X) ---
    SENSOR_1        AT %X0   : BOOL;   // Sensor inductivo/optico 1
    SENSOR_2        AT %X1   : BOOL;   // Sensor inductivo/optico 2

    // --- Holding Registers (HMI -> PLC -> D) ---
    SERVO_SPEED     AT %D100 : INT;    // Velocidad objetivo
    SERVO_POS_TARGET AT %D101 : INT;   // Posicion objetivo
    STEP_NUMBER     AT %D102 : INT;    // Paso actual
    MACHINE_STATE   AT %D103 : INT;    // Estado maquina

    // --- Input Registers (PLC -> HMI <- D, solo lectura) ---
    SERVO_POS_ACTUAL    AT %D200 : INT;   // Posicion actual
    SERVO_ACTUAL_SPEED  AT %D201 : INT;   // Velocidad actual
    SERVO_TORQUE        AT %D202 : INT;   // Torque actual

    // --- Internos ---
    iStep           : INT := 0;
    bCycleRunning   : BOOL := FALSE;
    bPaused         : BOOL := FALSE;
END_VAR

// =============================================================================
// Logica Principal
// =============================================================================

// --- E-Stop: Prioridad maxima ---
IF CMD_ESTOP THEN
    // Apagar todas las valvulas
    VALVE_1  := FALSE;
    VALVE_2  := FALSE;
    VALVE_3  := FALSE;
    VALVE_4  := FALSE;
    VALVE_5  := FALSE;
    VALVE_6  := FALSE;
    VALVE_7  := FALSE;
    VALVE_8  := FALSE;
    VALVE_9  := FALSE;
    VALVE_10 := FALSE;
    SERVO_JOG_FWD := FALSE;
    SERVO_JOG_REV := FALSE;
    bCycleRunning := FALSE;
    MACHINE_STATE := 0;
    RETURN;
END_IF;

// --- Seleccion de Modo ---
IF MODE_AUTO THEN
    MACHINE_STATE := 1;
ELSIF MODE_MANUAL THEN
    MACHINE_STATE := 2;
ELSIF MODE_STEP THEN
    MACHINE_STATE := 3;
ELSIF MODE_DEBUG THEN
    MACHINE_STATE := 4;
END_IF;

// --- Modo Automatico ---
IF MACHINE_STATE = 1 AND bCycleRunning THEN
    IF CMD_PAUSE THEN
        bPaused := TRUE;
    ELSIF NOT CMD_PAUSE THEN
        bPaused := FALSE;
    END_IF;

    IF NOT bPaused THEN
        // TODO: Insertar logica del ciclo de produccion aqui
        // Ejemplo secuencial basico:
        CASE iStep OF
            0:  // Paso inicial
                VALVE_1 := TRUE;
                iStep := 1;
            1:  // Esperar sensor
                IF SENSOR_1 THEN
                    VALVE_1 := FALSE;
                    VALVE_2 := TRUE;
                    iStep := 2;
                END_IF;
            2:  // Siguiente paso
                IF SENSOR_2 THEN
                    VALVE_2 := FALSE;
                    iStep := 0;
                END_IF;
        END_CASE;
    END_IF;

    // Cycle Stop: completar paso actual y detener
    IF CMD_CYCLE_STOP AND NOT bPaused THEN
        bCycleRunning := FALSE;
        iStep := 0;
    END_IF;
END_IF;

// --- Inicio ---
IF CMD_START AND NOT bCycleRunning AND NOT CMD_ESTOP THEN
    bCycleRunning := TRUE;
    iStep := 0;
END_IF;

// --- Reportar paso al HMI ---
STEP_NUMBER := iStep;
