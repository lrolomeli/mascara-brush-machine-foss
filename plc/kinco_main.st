// =============================================================================
// KINCO K6 - Programa Principal (ST)
// Equivalencias Modbus TCP <-> Direcciones Internas Kinco
// =============================================================================
// Coils (M):         HMI -> PLC   :   CMD_START   -> M0
// Holding Regs (D):  HMI -> PLC   :   SERVO_SPEED -> D0
// Input Regs (D):    PLC -> HMI   :   SERVO_POS   -> D200 (lectura)
//
// NOTA: Kinco K6 usa convencion Modbus 1-based para registros.
// Los addresses en el JSON del perfil deben ajustarse:
//   - Holding Register address 0 en JSON -> D0 en Kinco
//   - El driver pymodbus usa 0-based, el PLC interno usa su propio mapeo.
// =============================================================================
//
// COMPARACION: En Kinco, los coils Modbus mapean directamente a M (bit memory).
// En Delta, tambien mapean a M pero los addresses pueden diferir.
// La ABSTRACCION del HMI oculta esto: solo usa "CMD_START", "VALVE_1", etc.
// =============================================================================

PROGRAM MAIN
VAR
    // --- Entradas desde HMI (Coils Modbus -> M) ---
    CMD_START       AT %M0  : BOOL;
    CMD_CYCLE_STOP  AT %M1  : BOOL;
    CMD_PAUSE       AT %M2  : BOOL;
    CMD_ESTOP       AT %M3  : BOOL;
    MODE_AUTO       AT %M10 : BOOL;
    MODE_MANUAL     AT %M11 : BOOL;
    MODE_STEP       AT %M12 : BOOL;
    MODE_DEBUG      AT %M13 : BOOL;

    // --- Valvulas (Coils Modbus -> M) ---
    // En Kinco K6: M100-M109 mapeados via Modbus coils 100-109
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

    // --- Sensores (Discrete Inputs) ---
    // En Kinco: X0, X1 son entradas fisicas. Si se mapean via Modbus,
    // los discrete inputs del JSON apuntan a estas.
    SENSOR_1        AT %X0   : BOOL;
    SENSOR_2        AT %X1   : BOOL;

    // --- Holding Registers (HMI -> PLC) ---
    SERVO_SPEED     AT %D0   : INT;
    SERVO_POS_TARGET AT %D1  : INT;
    STEP_NUMBER     AT %D2   : INT;
    MACHINE_STATE   AT %D3   : INT;

    // --- Input Registers (PLC -> HMI, solo lectura) ---
    SERVO_POS_ACTUAL    AT %D200 : INT;
    SERVO_ACTUAL_SPEED  AT %D201 : INT;
    SERVO_TORQUE        AT %D202 : INT;

    // --- Internos ---
    iStep           : INT := 0;
    bCycleRunning   : BOOL := FALSE;
    bPaused         : BOOL := FALSE;
END_VAR

// =============================================================================
// Logica Principal
// =============================================================================

// --- E-Stop ---
IF CMD_ESTOP THEN
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
        CASE iStep OF
            0:
                VALVE_1 := TRUE;
                iStep := 1;
            1:
                IF SENSOR_1 THEN
                    VALVE_1 := FALSE;
                    VALVE_2 := TRUE;
                    iStep := 2;
                END_IF;
            2:
                IF SENSOR_2 THEN
                    VALVE_2 := FALSE;
                    iStep := 0;
                END_IF;
        END_CASE;
    END_IF;

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

STEP_NUMBER := iStep;
