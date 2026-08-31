PROGRAM Secuencia_Mascara_Brush_Machine
VAR
    // -------------------------------------------------------------------------
    // 1. ENTRADAS (SENSORES Y BOTONERA)
    // -------------------------------------------------------------------------
    S5_START           : BOOL; // START
    S3_STOP            : BOOL; // STOP
    S1_EMERGENCY_STOP  : BOOL; // PARO EMERGENCIA (NC)
    S4_CONTINUOUS      : BOOL; // CONTINUO
    S2_SINGLE          : BOOL; // UNICO
    
    S_MANUAL           : BOOL; // Selector Modo Manual
    S_STEP_BY_STEP     : BOOL; // Selector Paso a Paso
    BTN_STEP           : BOOL; // Botón Avance de Paso
    
    // Sensores Físicos
    S8, S9, S10, S11, S12, S13, S14, S15, S16, S17 : BOOL;
    S18, S19, S20, S21, S22, S23                   : BOOL;

    // -------------------------------------------------------------------------
    // 2. COMANDOS MANUALES (FORZADO INDIVIDUAL)
    // -------------------------------------------------------------------------
    CMD_Y1, CMD_Y3, CMD_Y6, CMD_Y7, CMD_Y8, CMD_Y9, CMD_Y10 : BOOL;
    CMD_Y11, CMD_Y12, CMD_Y14, CMD_Y15, CMD_Y16, CMD_Y17, CMD_Y18, CMD_Y24 : BOOL;
    CMD_M1, CMD_M2, CMD_M3 : BOOL;

    // -------------------------------------------------------------------------
    // 3. TEMPORIZADORES (TON)
    // -------------------------------------------------------------------------
    T_2T5 : TON; // Retardo orientación Chuck
    T_1T3 : TON; // Tiempo agarre Chucks a apertura pinza
    T_1T4 : TON; // Recorrido pinza atrás
    T_2T4 : TON; // Tiempo M1 encendido
    T_NEW : TON; // Tiempo antes de apagar Y3
    T_1T1 : TON; // Tiempo de Rasurado (M2, Y6)
    T_1T5 : TON; // Tiempo al posicionar alambre/pinza
    T_2T7 : TON; // Tiempo Tijera Arriba
    T_2T6 : TON; // Tiempo Cierre Tijera

    // -------------------------------------------------------------------------
    // 4. MÁQUINAS DE ESTADOS PARALELAS Y DEPURA
    // -------------------------------------------------------------------------
    Paso_Alambre       : INT := 0; // Rama Izquierda (Alambre/Cerda)
    Paso_Pinza         : INT := 0; // Rama Derecha (Pinza/Giro)
    
    Sensor_Esperado    : STRING[40];
    Condicion_Siguiente: BOOL;
    BTN_STEP_Trig      : BOOL;
    BTN_STEP_Mem       : BOOL;

    // Salidas Internas Automáticas
    Auto_Y1, Auto_Y3, Auto_Y6, Auto_Y7, Auto_Y8, Auto_Y9, Auto_Y10 : BOOL;
    Auto_Y11, Auto_Y12, Auto_Y14, Auto_Y15, Auto_Y16, Auto_Y17, Auto_Y18, Auto_Y24 : BOOL;
    Auto_M1, Auto_M2, Auto_M3, Auto_Catcher : BOOL;

    // Salidas Físicas Reales
    Y1, Y3, Y6, Y7, Y8, Y9, Y10, Y11, Y12, Y14, Y15, Y16, Y17, Y18, Y24 : BOOL;
    M1, M2, M3, CATCHER : BOOL;
END_VAR

// =============================================================================
// LÓGICA DE CONTROL
// =============================================================================

IF NOT S1_EMERGENCY_STOP OR S3_STOP OR S_MANUAL THEN
    Paso_Alambre := 0;
    Paso_Pinza   := 0;
END_IF;

BTN_STEP_Trig := BTN_STEP AND NOT BTN_STEP_Mem;
BTN_STEP_Mem  := BTN_STEP;

// Subproceso Orientador (S1 / Y1 / S9)
IF S14 THEN
    Auto_Y1 := TRUE;
END_IF;
IF S9 THEN
    Auto_Y1 := FALSE;
END_IF;

IF NOT S_MANUAL THEN

    // -------------------------------------------------------------------------
    // RAMA 1: PREPARACIÓN DE ALAMBRE Y CERDA (IZQUIERDA EN DIAGRAMA)
    // -------------------------------------------------------------------------
    CASE Paso_Alambre OF
        0: // ESPERA INICIO
            IF S5_START AND S14 THEN
                Paso_Alambre := 10;
            END_IF;

        10: // S14 DETECTADO -> Y15-ON, Y14-ON, 2T5-START, Y9-ON
            Auto_Y15 := TRUE;
            Auto_Y14 := TRUE;
            Auto_Y9  := TRUE;
            Sensor_Esperado := 'Sensor S18 (Cuchilla Atras)';
            
            IF S18 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 20;
            END_IF;

        20: // S18 DETECTADO -> Y17-ON (CIZALLA)
            Auto_Y17 := TRUE;
            Sensor_Esperado := 'Sensor S21 (Peine Atras)';
            
            IF S21 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 30;
            END_IF;

        30: // S21 DETECTADO -> Y17-OFF, Y15-OFF
            Auto_Y17 := FALSE;
            Auto_Y15 := FALSE;
            Sensor_Esperado := 'Sensor S19 (Cuchilla Adelante)';
            
            IF S19 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 40;
            END_IF;

        40: // S19 DETECTADO -> Y18-ON (EMPUJA ALAMBRE)
            Auto_Y18 := TRUE;
            Sensor_Esperado := 'Sensor S22 (Alambre Adelante)';
            
            IF S22 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 50;
            END_IF;

        50: // S22 DETECTADO -> Y16-ON (LENGUETA)
            Auto_Y16 := TRUE;
            Sensor_Esperado := 'Esperando S20 (Lengueta) AND S16 (Pinza Arriba)';
            
            // Punto de Sincronización con la Pinza
            IF S20 AND S16 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 60;
            END_IF;

        60: // S20 & S16 DETECTADOS -> Y18-OFF, Y12-ON
            Auto_Y18 := FALSE;
            Auto_Y12 := TRUE;
            Sensor_Esperado := 'Sensor S17 (Pinza Adelante)';
            
            IF S17 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 70;
            END_IF;

        70: // S17 DETECTADO -> Y14-OFF, Y10-ON, Y16-OFF, 1T5-START
            Auto_Y14 := FALSE;
            Auto_Y10 := TRUE;
            Auto_Y16 := FALSE;
            Sensor_Esperado := 'Timer 1T5 (Posicionamiento)';
            
            IF T_1T5.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 80;
            END_IF;

        80: // FIN 1T5 -> Y12-OFF
            Auto_Y12 := FALSE;
            Paso_Alambre := 0; // Termina ciclo de alambre
    END_CASE;


    // -------------------------------------------------------------------------
    // RAMA 2: PINZA, CHUCKS Y RASURADO (DERECHA EN DIAGRAMA)
    // -------------------------------------------------------------------------
    CASE Paso_Pinza OF
        0: // ESPERA RETARDO ORIENTACIÓN
            IF Paso_Alambre >= 10 AND T_2T5.Q THEN
                Paso_Pinza := 10;
            END_IF;

        10: // WHEN 2ND TIMER 5 ENDS -> Y3-ON, 1T3-START, Y10-OFF
            Auto_Y3  := TRUE;
            Auto_Y10 := FALSE;
            Sensor_Esperado := 'Timer 1T3 (Cierre Chucks)';
            
            IF T_1T3.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 20;
            END_IF;

        20: // WHEN TIMER 3 HAS OVER -> Y11-OFF, Y12-OFF
            Auto_Y11 := FALSE;
            Auto_Y12 := FALSE;
            Sensor_Esperado := 'Sensor S15 (Pinza Fuera)';
            
            IF S15 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 30;
            END_IF;

        30: // S15 DETECTADO -> M1-START, 2T4-START, Y9-OFF
            Auto_M1 := TRUE;
            Auto_Y9 := FALSE;
            Sensor_Esperado := 'Timer 2T4 (Giro M1) OR Sensor S10';
            
            IF T_2T4.Q THEN
                Auto_M1 := FALSE; // M1 STOPS
            END_IF;

            IF S10 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 40;
            END_IF;

        40: // S10 DETECTADO -> T1-START, M2-START, Y6-ON, Y11-ON, CATCHER-OFF
            Auto_M2      := TRUE;
            Auto_Y6      := TRUE;
            Auto_Y11     := TRUE;
            Auto_Catcher := FALSE;
            Sensor_Esperado := 'Timer 1T1 (Tiempo Rasurado)';
            
            IF T_1T1.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 50;
            END_IF;

        50: // WHEN TIMER 1 HAS OVER -> M2-STOP, Y6-OFF
            Auto_M2 := FALSE;
            Auto_Y6 := FALSE;
            Sensor_Esperado := 'Sensor S11 (Rasurado Listo)';
            
            IF S11 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 60;
            END_IF;

        60: // S11 DETECTADO -> 2T7-START, Y7-ON
            Auto_Y7 := TRUE;
            Sensor_Esperado := 'Sensor S12 (Tijera Arriba)';
            
            IF S12 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 70;
            END_IF;

        70: // S12 DETECTADO -> Y8-ON (ABRE/CIERRA TIJERA)
            Auto_Y8 := TRUE;
            Sensor_Esperado := 'Timer 2T7 (Tiempo Tijera)';
            
            IF T_2T7.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 80;
            END_IF;

        80: // WHEN 2ND TIMER 7 HAS OVER -> 2T6-START, Y8-OFF
            Auto_Y8 := FALSE;
            Sensor_Esperado := 'Timer 2T6 (Cierre Tijera)';
            
            IF T_2T6.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 90;
            END_IF;

        90: // WHEN 2ND TIMER 6 HAS OVER -> Y7-OFF, CATCHER-ON
            Auto_Y7      := FALSE;
            Auto_Catcher := TRUE;
            
            IF T_NEW.Q THEN
                Auto_Y3 := FALSE; // WHEN NEW TIMER ENDS -> Y3-OFF
                Paso_Pinza := 0;  // FIN DE CICLO
            END_IF;
    END_CASE;

END_IF;

// -----------------------------------------------------------------------------
// TEMPORIZADORES (TON)
// -----------------------------------------------------------------------------
T_2T5(IN := (Paso_Alambre = 10), PT := T#2.5S);
T_1T3(IN := (Paso_Pinza = 10),   PT := T#1.5S);
T_2T4(IN := (Paso_Pinza = 30),   PT := T#2.0S);
T_NEW(IN := (Paso_Pinza = 30 AND NOT T_2T4.Q), PT := T#1.0S);
T_1T1(IN := (Paso_Pinza = 40),   PT := T#3.0S);
T_1T5(IN := (Paso_Alambre = 70), PT := T#1.5S);
T_2T7(IN := (Paso_Pinza = 60),   PT := T#2.0S);
T_2T6(IN := (Paso_Pinza = 80),   PT := T#1.5S);

// -----------------------------------------------------------------------------
// MULTIPLEXOR AUTOMÁTICO / MANUAL (ENTRADAS DE DEPURA)
// -----------------------------------------------------------------------------
Y1  := SEL(S_MANUAL, Auto_Y1,  CMD_Y1);
Y3  := SEL(S_MANUAL, Auto_Y3,  CMD_Y3);
Y6  := SEL(S_MANUAL, Auto_Y6,  CMD_Y6);
Y7  := SEL(S_MANUAL, Auto_Y7,  CMD_Y7);
Y8  := SEL(S_MANUAL, Auto_Y8,  CMD_Y8);
Y9  := SEL(S_MANUAL, Auto_Y9,  CMD_Y9);
Y10 := SEL(S_MANUAL, Auto_Y10, CMD_Y10);
Y11 := SEL(S_MANUAL, Auto_Y11, CMD_Y11);
Y12 := SEL(S_MANUAL, Auto_Y12, CMD_Y12);
Y14 := SEL(S_MANUAL, Auto_Y14, CMD_Y14);
Y15 := SEL(S_MANUAL, Auto_Y15, CMD_Y15);
Y16 := SEL(S_MANUAL, Auto_Y16, CMD_Y16);
Y17 := SEL(S_MANUAL, Auto_Y17, CMD_Y17);
Y18 := SEL(S_MANUAL, Auto_Y18, CMD_Y18);

M1  := SEL(S_MANUAL, Auto_M1,  CMD_M1);
M2  := SEL(S_MANUAL, Auto_M2,  CMD_M2);
CATCHER := SEL(S_MANUAL, Auto_Catcher, CMD_Y24);