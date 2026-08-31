PROGRAM Secuencia_MA1_Debugging
VAR
    // -------------------------------------------------------------------------
    // 1. ENTRADAS Y SENSORES
    // -------------------------------------------------------------------------
    START              : BOOL; // Botón Arranque / Inicio
    STOP               : BOOL; // Botón Paro
    EMERGENCY_STOP     : BOOL; // Paro de Emergencia (NC)
    MODE_SINGLE        : BOOL; // Ciclo Único
    MODE_CONTINUOUS    : BOOL; // Ciclo Continuo
    
    // --- CONTROLES DE DEPURA / DIAGNÓSTICO ---
    MODE_STEP_BY_STEP  : BOOL; // Interruptor: TRUE = Modo Paso a Paso Activo
    BTN_STEP           : BOOL; // Botón Físico / HMI: Avanza 1 paso en la secuencia
    
    // Sensores Físicos
    S9, S10, S11, S12, S13, S14, S15, S16, S17 : BOOL;
    S18, S19, S20, S21, S22                    : BOOL;

    // -------------------------------------------------------------------------
    // 2. TEMPORIZADORES (TON)
    // -------------------------------------------------------------------------
    T27  : TON; // 2.5s - Orientación
    T114 : TON; // 1.5s - Apertura Pinza
    T4   : TON; // 1.0s - Salida Pinza
    T1   : TON; // 3.0s - Rasurado
    T5   : TON; // 2.0s - Corte Tijera

    // -------------------------------------------------------------------------
    // 3. CONTROL DE SECUENCIA Y DIAGNÓSTICO
    // -------------------------------------------------------------------------
    Paso               : INT := 0;
    CondicionSiguiente : BOOL; // Flag interno: ¿El paso actual ya cumplió su condición?
    
    // --- VARIABLES DE DIAGNÓSTICO DE FALLAS ---
    Falla_Bloqueante   : BOOL; // TRUE = La máquina está retenida por un sensor/timer
    Sensor_Esperado    : STRING[30]; // Indica qué entrada/timer estamos esperando
    
    // Flanco de subida para el botón de avance manual
    BTN_STEP_Trig      : BOOL;
    BTN_STEP_Mem       : BOOL;

    // -------------------------------------------------------------------------
    // 4. SALIDAS (ACTUADORES Y MOTORES)
    // -------------------------------------------------------------------------
    Y1, Y3, Y5, Y6, Y7, Y8, Y10, Y11, Y12, Y14, Y15, Y16, Y17, Y18, Y24 : BOOL;
    Y_CuchillaAlambre : BOOL;
    M1, M2            : BOOL;
END_VAR

// =============================================================================
// LÓGICA DE CONTROL Y DEPURACIÓN
// =============================================================================

// Paro de Emergencia o Paro Físico
IF NOT EMERGENCY_STOP OR STOP THEN
    Paso := 0;
END_IF;

// Detección de Flanco de Subida para BTN_STEP (Para avanzar solo 1 paso por pulsación)
BTN_STEP_Trig := BTN_STEP AND NOT BTN_STEP_Mem;
BTN_STEP_Mem  := BTN_STEP;

// -----------------------------------------------------------------------------
// SUBPROCESO DE ALAMBRE (Evaluación continua)
// -----------------------------------------------------------------------------
Y15 := NOT S21;
Y17 := NOT S21;
Y18 := S19;
Y16 := S22;

IF S18 THEN
    Y_CuchillaAlambre := TRUE;
ELSIF S20 THEN
    Y_CuchillaAlambre := FALSE;
END_IF;


// -----------------------------------------------------------------------------
// MÁQUINA DE ESTADOS SECUENCIAL CON DEPURA
// -----------------------------------------------------------------------------
CASE Paso OF

    0: // ESPERA DE INICIO
        Sensor_Esperado := 'Esperando Boton START';
        CondicionSiguiente := START AND EMERGENCY_STOP;
        
        IF CondicionSiguiente THEN
            Paso := 10;
        END_IF;

    10: // ARRANQUE (Y14, Y24) -> TIMER T27
        Sensor_Esperado := 'Timer T27 (2.5s)';
        CondicionSiguiente := T27.Q;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 20;
        END_IF;

    20: // ORIENTACIÓN (Y11) -> SENSOR S14
        Sensor_Esperado := 'Sensor S14 (Pinza Abajo)';
        CondicionSiguiente := S14;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 30;
        END_IF;

    30: // AGARRE CHUCKS (Y3) -> TIMER T114
        Sensor_Esperado := 'Timer T114 (1.5s)';
        CondicionSiguiente := T114.Q;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 40;
        END_IF;

    40: // APERTURA PINZA (Y10) -> TIMER T4
        Sensor_Esperado := 'Timer T4 (1.0s)';
        CondicionSiguiente := T4.Q;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 50;
        END_IF;

    50: // SALIDA PINZA (Y5) -> SENSOR S15
        Sensor_Esperado := 'Sensor S15 (Pinza Fuera)';
        CondicionSiguiente := S15;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 60;
        END_IF;

    60: // GIRO M1 Y SUBIDA Y6 -> SENSOR S10
        Sensor_Esperado := 'Sensor S10 (Posicionamiento)';
        CondicionSiguiente := S10;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 70;
        END_IF;

    70: // RASURADO M2 -> TIMER T1
        Sensor_Esperado := 'Timer T1 (3.0s Rasurado)';
        CondicionSiguiente := T1.Q;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 80;
        END_IF;

    80: // TIJERA PREPARACIÓN -> SENSOR S11
        Sensor_Esperado := 'Sensor S11 (Posicion Tijera)';
        CondicionSiguiente := S11;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 90;
        END_IF;

    90: // CORTE TIJERA (Y7, Y8) -> TIMER T5
        Sensor_Esperado := 'Timer T5 (2.0s Corte)';
        CondicionSiguiente := T5.Q;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            Paso := 100;
        END_IF;

    100: // DISPARO SIMULTÁNEO FINAL -> SENSOR S9
        Sensor_Esperado := 'Sensor S9 (Fin Alambre)';
        CondicionSiguiente := S9;
        
        IF CondicionSiguiente AND (NOT MODE_STEP_BY_STEP OR BTN_STEP_Trig) THEN
            IF MODE_CONTINUOUS THEN
                Paso := 10;
            ELSE
                Paso := 0;
            END_IF;
        END_IF;

END_CASE;

// INDICADOR DE FALLA / RETENCIÓN
// Si estamos en un paso activo pero la condición NO se cumple, se marca retención
Falla_Bloqueante := (Paso > 0) AND NOT CondicionSiguiente;


// -----------------------------------------------------------------------------
// ACTUALIZACIÓN DE TEMPORIZADORES (TON)
// -----------------------------------------------------------------------------
T27(IN  := (Paso = 10), PT := T#2.5S);
T114(IN := (Paso = 30), PT := T#1.5S);
T4(IN   := (Paso = 40), PT := T#1.0S);
T1(IN   := (Paso = 70), PT := T#3.0S);
T5(IN   := (Paso = 90), PT := T#2.0S);


// -----------------------------------------------------------------------------
// MAPEO DE SALIDAS FÍSICAS
// -----------------------------------------------------------------------------
Y14 := (Paso >= 10 AND Paso <= 100);
Y24 := (Paso >= 10 AND Paso <= 100);
Y11 := (Paso >= 20 AND Paso <= 100);

Y3  := (Paso >= 30 AND Paso <= 100);
Y10 := (Paso = 40 OR Paso = 50) AND NOT (S16 AND S17);
Y5  := (Paso >= 50 AND Paso < 100);

M1  := (Paso >= 60 AND Paso < 100);
Y6  := (Paso = 60 OR Paso = 70);
M2  := (Paso = 70);

Y7  := (Paso = 80 OR Paso = 90);
Y8  := (Paso = 90);
Y12 := (Paso = 100);