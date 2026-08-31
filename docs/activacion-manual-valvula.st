PROGRAM Secuencia_MA1_Debugging_Manual
VAR
    // -------------------------------------------------------------------------
    // 1. SELECTORES DE MODO Y BOTONERA
    // -------------------------------------------------------------------------
    START              : BOOL; // Botón Arranque / Inicio
    STOP               : BOOL; // Botón Paro
    EMERGENCY_STOP     : BOOL; // Paro de Emergencia (NC)
    MODE_SINGLE        : BOOL; // Selector Ciclo Único
    MODE_CONTINUOUS    : BOOL; // Selector Ciclo Continuo
    
    // --- SELECCIÓN DE MODO DE DIAGNÓSTICO ---
    MODE_MANUAL        : BOOL; // TRUE = Modo Manual Activo (Fuerza salidas individuales)
    MODE_STEP_BY_STEP  : BOOL; // TRUE = Modo Paso a Paso Activo (Secuencia manual)
    BTN_STEP           : BOOL; // Pulso para avanzar 1 paso en la secuencia
    
    // -------------------------------------------------------------------------
    // 2. COMANDOS MANUALES INDIVIDUALES (FORZADO INDIVIDUAL POR HMI / PLC)
    // -------------------------------------------------------------------------
    CMD_Y1  : BOOL; // Forzado manual Válvula Y1
    CMD_Y3  : BOOL; // Forzado manual Chucks Y3
    CMD_Y5  : BOOL; // Forzado manual Sale Pinza Y5
    CMD_Y6  : BOOL; // Forzado manual Sube Pinza Y6
    CMD_Y7  : BOOL; // Forzado manual Sube Tijera Y7
    CMD_Y8  : BOOL; // Forzado manual Cierra Tijera Y8
    CMD_Y10 : BOOL; // Forzado manual Abre Pinza Y10
    CMD_Y11 : BOOL; // Forzado manual Orienta Y11
    CMD_Y12 : BOOL; // Forzado manual Cachador Y12
    CMD_Y14 : BOOL; // Forzado manual Baja Pinza Y14
    CMD_Y15 : BOOL; // Forzado manual Y15
    CMD_Y16 : BOOL; // Forzado manual Y16
    CMD_Y17 : BOOL; // Forzado manual Y17
    CMD_Y18 : BOOL; // Forzado manual Y18
    CMD_Y24 : BOOL; // Forzado manual Y24
    CMD_M1  : BOOL; // Forzado manual Motor 1
    CMD_M2  : BOOL; // Forzado manual Motor 2

    // -------------------------------------------------------------------------
    // 3. SENSORES Y TEMPORIZADORES
    // -------------------------------------------------------------------------
    S9, S10, S11, S12, S13, S14, S15, S16, S17 : BOOL;
    S18, S19, S20, S21, S22                    : BOOL;

    T27  : TON; // 2.5s
    T114 : TON; // 1.5s
    T4   : TON; // 1.0s
    T1   : TON; // 3.0s
    T5   : TON; // 2.0s

    // -------------------------------------------------------------------------
    // 4. ESTRUCTURA INTERNA Y SALIDAS AUTOMÁTICAS
    // -------------------------------------------------------------------------
    Paso               : INT := 0;
    CondicionSiguiente : BOOL;
    Sensor_Esperado    : STRING[30];
    
    BTN_STEP_Trig      : BOOL;
    BTN_STEP_Mem       : BOOL;

    // Variables internas calculadas por el modo automático
    Auto_Y1, Auto_Y3, Auto_Y5, Auto_Y6, Auto_Y7, Auto_Y8, Auto_Y10 : BOOL;
    Auto_Y11, Auto_Y12, Auto_Y14, Auto_Y15, Auto_Y16, Auto_Y17, Auto_Y18, Auto_Y24 : BOOL;
    Auto_M1, Auto_M2 : BOOL;

    // Salidas físicas reales conectadas a los módulos de E/S del PLC
    Y1, Y3, Y5, Y6, Y7, Y8, Y10, Y11, Y12, Y14, Y15, Y16, Y17, Y18, Y24 : BOOL;
    Y_CuchillaAlambre : BOOL;
    M1, M2            : BOOL;
END_VAR

// =============================================================================
// LÓGICA DE CONTROL
// =============================================================================

// Paro de Emergencia o activar Modo Manual resetea la secuencia automática a 0
IF NOT EMERGENCY_STOP OR STOP OR MODE_MANUAL THEN
    Paso := 0;
END_IF;

// Flanco de subida para avance de paso
BTN_STEP_Trig := BTN_STEP AND NOT BTN_STEP_Mem;
BTN_STEP_Mem  := BTN_STEP;

// -----------------------------------------------------------------------------
// SUBPROCESO DE ALAMBRE (Cálculo Automático)
// -----------------------------------------------------------------------------
Auto_Y15 := NOT S21;
Auto_Y17 := NOT S21;
Auto_Y18 := S19;
Auto_Y16 := S22;

IF S18 THEN
    Y_CuchillaAlambre := TRUE;
ELSIF S20 THEN
    Y_CuchillaAlambre := FALSE;
END_IF;


// -----------------------------------------------------------------------------
// MÁQUINA DE ESTADOS SECUENCIAL (Sólo se ejecuta si NO estamos en Manual)
// -----------------------------------------------------------------------------
IF NOT MODE_MANUAL THEN
    CASE Paso OF

        0: // ESPERA DE INICIO
            Sensor_Esperado := 'Esperando Boton START';
            CondicionSiguiente := START AND EMERGENCY_STOP;
            IF CondicionSiguiente THEN Paso := 10; END_IF;

        10: // ARRANQUE (Y14, Y24) -> TIMER T27
            Sensor_Esperado := 'Timer T27 (2.5s)';
            CondicionSiguiente := T27.Q;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 20; END_IF;

        20: // ORIENTACIÓN (Y11) -> SENSOR S14
            Sensor_Esperado := 'Sensor S14 (Pinza Abajo)';
            CondicionSiguiente := S14;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 30; END_IF;

        30: // AGARRE CHUCKS (Y3) -> TIMER T114
            Sensor_Esperado := 'Timer T114 (1.5s)';
            CondicionSiguiente := T114.Q;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 40; END_IF;

        40: // APERTURA PINZA (Y10) -> TIMER T4
            Sensor_Esperado := 'Timer T4 (1.0s)';
            CondicionSiguiente := T4.Q;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 50; END_IF;

        50: // SALIDA PINZA (Y5) -> SENSOR S15
            Sensor_Esperado := 'Sensor S15 (Pinza Fuera)';
            CondicionSiguiente := S15;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 60; END_IF;

        60: // GIRO M1 Y SUBIDA Y6 -> SENSOR S10
            Sensor_Esperado := 'Sensor S10 (Posicionamiento)';
            CondicionSiguiente := S10;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 70; END_IF;

        70: // RASURADO M2 -> TIMER T1
            Sensor_Esperado := 'Timer T1 (3.0s Rasurado)';
            CondicionSiguiente := T1.Q;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 80; END_IF;

        80: // TIJERA PREPARACIÓN -> SENSOR S11
            Sensor_Esperado := 'Sensor S11 (Posicion Tijera)';
            CondicionSiguiente := S11;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 90; END_IF;

        90: // CORTE TIJERA (Y7, Y8) -> TIMER T5
            Sensor_Esperado := 'Timer T5 (2.0s Corte)';
            CondicionSiguiente := T5.Q;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN Paso := 100; END_IF;

        100: // DISPARO SIMULTÁNEO FINAL -> SENSOR S9
            Sensor_Esperado := 'Sensor S9 (Fin Alambre)';
            CondicionSiguiente := S9;
            IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                IF MODE_CONTINUOUS THEN Paso := 10; ELSE Paso := 0; END_IF;
            END_IF;

    END_CASE;
END_IF;


// -----------------------------------------------------------------------------
// ACTUALIZACIÓN DE TEMPORIZADORES (TON)
// -----------------------------------------------------------------------------
T27(IN  := (Paso = 10), PT := T#2.5S);
T114(IN := (Paso = 30), PT := T#1.5S);
T4(IN   := (Paso = 40), PT := T#1.0S);
T1(IN   := (Paso = 70), PT := T#3.0S);
T5(IN   := (Paso = 90), PT := T#2.0S);


// -----------------------------------------------------------------------------
// CÁLCULO DE SALIDAS EN MODO AUTOMÁTICO
// -----------------------------------------------------------------------------
Auto_Y14 := (Paso >= 10 AND Paso <= 100);
Auto_Y24 := (Paso >= 10 AND Paso <= 100);
Auto_Y11 := (Paso >= 20 AND Paso <= 100);

Auto_Y3  := (Paso >= 30 AND Paso <= 100);
Auto_Y10 := (Paso = 40 OR Paso = 50) AND NOT (S16 AND S17);
Auto_Y5  := (Paso >= 50 AND Paso < 100);

Auto_M1  := (Paso >= 60 AND Paso < 100);
Auto_Y6  := (Paso = 60 OR Paso = 70);
Auto_M2  := (Paso = 70);

Auto_Y7  := (Paso = 80 OR Paso = 90);
Auto_Y8  := (Paso = 90);
Auto_Y12 := (Paso = 100);


// =============================================================================
// MULTIPLEXOR DE SALIDAS FÍSICAS (AUTOMÁTICO VS MANUAL)
// =============================================================================
// Si MODE_MANUAL está activo, la salida responde al comando CMD_Yx.
// Si MODE_MANUAL es FALSE, responde a la máquina de estados (Auto_Yx).

Y1  := SEL(MODE_MANUAL, Auto_Y1,  CMD_Y1);
Y3  := SEL(MODE_MANUAL, Auto_Y3,  CMD_Y3);
Y5  := SEL(MODE_MANUAL, Auto_Y5,  CMD_Y5);
Y6  := SEL(MODE_MANUAL, Auto_Y6,  CMD_Y6);
Y7  := SEL(MODE_MANUAL, Auto_Y7,  CMD_Y7);
Y8  := SEL(MODE_MANUAL, Auto_Y8,  CMD_Y8);
Y10 := SEL(MODE_MANUAL, Auto_Y10, CMD_Y10);
Y11 := SEL(MODE_MANUAL, Auto_Y11, CMD_Y11);
Y12 := SEL(MODE_MANUAL, Auto_Y12, CMD_Y12);
Y14 := SEL(MODE_MANUAL, Auto_Y14, CMD_Y14);
Y15 := SEL(MODE_MANUAL, Auto_Y15, CMD_Y15);
Y16 := SEL(MODE_MANUAL, Auto_Y16, CMD_Y16);
Y17 := SEL(MODE_MANUAL, Auto_Y17, CMD_Y17);
Y18 := SEL(MODE_MANUAL, Auto_Y18, CMD_Y18);
Y24 := SEL(MODE_MANUAL, Auto_Y24, CMD_Y24);

M1  := SEL(MODE_MANUAL, Auto_M1,  CMD_M1);
M2  := SEL(MODE_MANUAL, Auto_M2,  CMD_M2);