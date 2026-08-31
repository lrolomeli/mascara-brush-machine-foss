// =============================================================================
// KINCO (GENERICO, K5s/K615S 16DT) - Programa Principal Maquina Ma1
// =============================================================================
// Portado y CORREGIDO a partir de docs/ma1st.st
//
// DISENO:
//   - Dos maquinas de estado paralelas:
//       * Paso_Alambre  : preparacion de alambre/cerda (rama izquierda)
//       * Paso_Pinza    : pinza, chucks, giro, rasurado, tijera (rama derecha)
//   - Punto de sincronizacion: la rama de alambre se detiene en Paso_Alambre=50
//     esperando S16 (pinza arriba) y S20 (lengueta adelante).
//   - Diagnostico conservado: S_MANUAL (fuerza salidas con CMD_Yx/CMD_Mx),
//     S_STEP_BY_STEP (congela el avance) y BTN_STEP (avance manual de paso).
//
// CORRECCIONES RESPECTO A ma1st.st:
//   [1] Paso 90 de Paso_Pinza ya no usa T_NEW (quedaba colgado). Ahora cierra
//       el ciclo con el sensor S13 (cepillado cortado).
//   [2] Se anade M3 (aspirado) al multiplexor, solo forzable manual.
//   [3] Se anaden alarmas H8 (baja presion = NOT S23) y H3 (nylon = S8),
//       y se mapea la salida fisica real Y24 (CACHADOR) en el multiplexor.
//
// EQUIVALENCIAS DE DIRECCIONAMIENTO KINCO (Modbus TCP):
//   - Coils de comando   (HMI->PLC):  S5_START, S3_STOP, S1_EMERGENCY_STOP,
//                                      S_MANUAL, S_STEP_BY_STEP, BTN_STEP ...
//   - Coils forzado CMD  (HMI->PLC):  CMD_Y1..Y18, CMD_Y24, CMD_M1..M3
//   - Discrete inputs    (PLC->HMI):  S8..S23 (sensores fisicos)
//   - Coils salidas fisicas (PLC->HW):Y1..Y18, Y24, M1, M2, M3, H8, H3
//   - Holding registers  (PLC->HMI):  Paso_Alambre, Paso_Pinza
// =============================================================================

PROGRAM Secuencia_Mascara_Brush_Machine

VAR
    // ---------------------------------------------------------------------
    // 1. ENTRADAS (SENSORES Y BOTONERA) - mapeadas a coils/discrete del JSON
    // ---------------------------------------------------------------------
    S5_START           : BOOL; // START
    S3_STOP            : BOOL; // STOP
    S1_EMERGENCY_STOP  : BOOL; // PARO EMERGENCIA (NC)
    S4_CONTINUOUS      : BOOL; // CONTINUO
    S2_SINGLE          : BOOL; // UNICO

    S_MANUAL           : BOOL; // Selector Modo Manual
    S_STEP_BY_STEP     : BOOL; // Selector Paso a Paso
    BTN_STEP           : BOOL; // Boton Avance de Paso

    // Sensores Fisicos
    S8, S9, S10, S11, S12, S13, S14, S15, S16, S17 : BOOL;
    S18, S19, S20, S21, S22, S23                   : BOOL;

    // ---------------------------------------------------------------------
    // 2. COMANDOS MANUALES (FORZADO INDIVIDUAL) - HMI escribe a estos coils
    // ---------------------------------------------------------------------
    CMD_Y1, CMD_Y3, CMD_Y6, CMD_Y7, CMD_Y8, CMD_Y9, CMD_Y10 : BOOL;
    CMD_Y11, CMD_Y12, CMD_Y14, CMD_Y15, CMD_Y16, CMD_Y17, CMD_Y18, CMD_Y24 : BOOL;
    CMD_M1, CMD_M2, CMD_M3 : BOOL;

    // ---------------------------------------------------------------------
    // 3. TEMPORIZADORES (TON)
    // ---------------------------------------------------------------------
    T_2T5 : TON; // Retardo orientacion Chuck (2.5s)
    T_1T3 : TON; // Tiempo agarre Chucks a apertura pinza (1.5s)
    T_1T4 : TON; // Recorrido pinza atras (no usado en la secuencia activa)
    T_2T4 : TON; // Tiempo M1 encendido (2.0s)
    T_1T1 : TON; // Tiempo de Rasurado (M2, Y6) (3.0s)
    T_1T5 : TON; // Tiempo al posicionar alambre/pinza (1.5s)
    T_2T7 : TON; // Tiempo Tijera Arriba (2.0s)
    T_2T6 : TON; // Tiempo Cierre Tijera (1.5s)

    // ---------------------------------------------------------------------
    // 4. MAQUINAS DE ESTADOS PARALELAS Y DEPURA
    // ---------------------------------------------------------------------
    Paso_Alambre       : INT := 0; // Rama Izquierda (Alambre/Cerda)
    Paso_Pinza         : INT := 0; // Rama Derecha (Pinza/Giro)

    Sensor_Esperado    : STRING[40];
    Condicion_Siguiente: BOOL;
    BTN_STEP_Trig      : BOOL;
    BTN_STEP_Mem       : BOOL;

    // Salidas Internas Automaticas
    Auto_Y1, Auto_Y3, Auto_Y6, Auto_Y7, Auto_Y8, Auto_Y9, Auto_Y10 : BOOL;
    Auto_Y11, Auto_Y12, Auto_Y14, Auto_Y15, Auto_Y16, Auto_Y17, Auto_Y18 : BOOL;
    Auto_M1, Auto_M2, Auto_M3, Auto_Catcher : BOOL;

    // Salidas Fisicas Reales
    Y1, Y3, Y6, Y7, Y8, Y9, Y10, Y11, Y12, Y14 : BOOL;
    Y15, Y16, Y17, Y18, Y24 : BOOL;
    M1, M2, M3 : BOOL;
    H8, H3 : BOOL; // Alarmas

END_VAR

// =============================================================================
// LOGICA DE CONTROL
// =============================================================================

// --- Paro de emergencia / Stop / Modo manual: reset de secuencias ---
IF NOT S1_EMERGENCY_STOP OR S3_STOP OR S_MANUAL THEN
    Paso_Alambre := 0;
    Paso_Pinza   := 0;
END_IF;

// Deteccion de flanco de subida para el boton de avance manual
BTN_STEP_Trig := BTN_STEP AND NOT BTN_STEP_Mem;
BTN_STEP_Mem  := BTN_STEP;

// --- Subproceso Orientador (Y1 / S9) ---
IF S14 THEN
    Auto_Y1 := TRUE;
END_IF;
IF S9 THEN
    Auto_Y1 := FALSE;
END_IF;

IF NOT S_MANUAL THEN

    // ---------------------------------------------------------------------
    // RAMA 1: PREPARACION DE ALAMBRE Y CERDA (IZQUIERDA EN DIAGRAMA)
    // ---------------------------------------------------------------------
    CASE Paso_Alambre OF

        0: // ESPERA INICIO
            Condicion_Siguiente := S5_START AND S14;
            Sensor_Esperado := 'S5_START AND S14 (Pinza Abajo)';
            IF S5_START AND S14 THEN
                Paso_Alambre := 10;
            END_IF;

        10: // S14 DETECTADO -> Y15-ON, Y14-ON, 2T5-START, Y9-ON
            Auto_Y15 := TRUE;
            Auto_Y14 := TRUE;
            Auto_Y9  := TRUE;
            Sensor_Esperado := 'Sensor S18 (Cuchilla Atras)';
            Condicion_Siguiente := S18;

            IF S18 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 20;
            END_IF;

        20: // S18 DETECTADO -> Y17-ON (CIZALLA)
            Auto_Y17 := TRUE;
            Sensor_Esperado := 'Sensor S21 (Peine Atras)';
            Condicion_Siguiente := S21;

            IF S21 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 30;
            END_IF;

        30: // S21 DETECTADO -> Y17-OFF, Y15-OFF
            Auto_Y17 := FALSE;
            Auto_Y15 := FALSE;
            Sensor_Esperado := 'Sensor S19 (Cuchilla Adelante)';
            Condicion_Siguiente := S19;

            IF S19 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 40;
            END_IF;

        40: // S19 DETECTADO -> Y18-ON (EMPUJA ALAMBRE)
            Auto_Y18 := TRUE;
            Sensor_Esperado := 'Sensor S22 (Alambre Adelante)';
            Condicion_Siguiente := S22;

            IF S22 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 50;
            END_IF;

        50: // S22 DETECTADO -> Y16-ON (LENGUETA)
            Auto_Y16 := TRUE;
            Sensor_Esperado := 'S20 (Lengueta) AND S16 (Pinza Arriba)';
            Condicion_Siguiente := S20 AND S16;

            // PUNTO DE SINCRONIZACION con la Pinza
            IF S20 AND S16 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 60;
            END_IF;

        60: // S20 & S16 DETECTADOS -> Y18-OFF, Y12-ON
            Auto_Y18 := FALSE;
            Auto_Y12 := TRUE;
            Sensor_Esperado := 'Sensor S17 (Pinza Adelante)';
            Condicion_Siguiente := S17;

            IF S17 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 70;
            END_IF;

        70: // S17 DETECTADO -> Y14-OFF, Y10-ON, Y16-OFF, 1T5-START
            Auto_Y14 := FALSE;
            Auto_Y10 := TRUE;
            Auto_Y16 := FALSE;
            Sensor_Esperado := 'Timer 1T5 (Posicionamiento)';
            Condicion_Siguiente := T_1T5.Q;

            IF T_1T5.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Alambre := 80;
            END_IF;

        80: // FIN 1T5 -> Y12-OFF
            Auto_Y12 := FALSE;
            Paso_Alambre := 0; // Termina ciclo de alambre

    END_CASE;


    // ---------------------------------------------------------------------
    // RAMA 2: PINZA, CHUCKS Y RASURADO (DERECHA EN DIAGRAMA)
    // ---------------------------------------------------------------------
    CASE Paso_Pinza OF

        0: // ESPERA RETARDO ORIENTACION
            IF Paso_Alambre >= 10 AND T_2T5.Q THEN
                Paso_Pinza := 10;
            END_IF;

        10: // WHEN 2ND TIMER 5 ENDS -> Y3-ON, 1T3-START, Y10-OFF
            Auto_Y3  := TRUE;
            Auto_Y10 := FALSE;
            Sensor_Esperado := 'Timer 1T3 (Cierre Chucks)';
            Condicion_Siguiente := T_1T3.Q;

            IF T_1T3.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 20;
            END_IF;

        20: // WHEN TIMER 3 HAS OVER -> Y11-OFF, Y12-OFF
            Auto_Y11 := FALSE;
            Auto_Y12 := FALSE;
            Sensor_Esperado := 'Sensor S15 (Pinza Fuera)';
            Condicion_Siguiente := S15;

            IF S15 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 30;
            END_IF;

        30: // S15 DETECTADO -> M1-START, 2T4-START, Y9-OFF
            Auto_M1 := TRUE;
            Auto_Y9 := FALSE;
            Sensor_Esperado := 'Timer 2T4 (Giro M1) OR Sensor S10';
            Condicion_Siguiente := T_2T4.Q OR S10;

            IF T_2T4.Q THEN
                Auto_M1 := FALSE; // M1 STOPS
            END_IF;

            IF S10 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 40;
            END_IF;

        40: // S10 DETECTADO -> 1T1-START, M2-START, Y6-ON, Y11-ON, CATCHER-OFF
            Auto_M2      := TRUE;
            Auto_Y6      := TRUE;
            Auto_Y11     := TRUE;
            Auto_Catcher := FALSE;
            Sensor_Esperado := 'Timer 1T1 (Tiempo Rasurado)';
            Condicion_Siguiente := T_1T1.Q;

            IF T_1T1.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 50;
            END_IF;

        50: // WHEN TIMER 1 HAS OVER -> M2-STOP, Y6-OFF
            Auto_M2 := FALSE;
            Auto_Y6 := FALSE;
            Sensor_Esperado := 'Sensor S11 (Rasurado Listo)';
            Condicion_Siguiente := S11;

            IF S11 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 60;
            END_IF;

        60: // S11 DETECTADO -> 2T7-START, Y7-ON
            Auto_Y7 := TRUE;
            Sensor_Esperado := 'Sensor S12 (Tijera Arriba)';
            Condicion_Siguiente := S12;

            IF S12 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 70;
            END_IF;

        70: // S12 DETECTADO -> Y8-ON (ABRE/CIERRA TIJERA)
            Auto_Y8 := TRUE;
            Sensor_Esperado := 'Timer 2T7 (Tiempo Tijera)';
            Condicion_Siguiente := T_2T7.Q;

            IF T_2T7.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 80;
            END_IF;

        80: // WHEN 2ND TIMER 7 HAS OVER -> 2T6-START, Y8-OFF
            Auto_Y8 := FALSE;
            Sensor_Esperado := 'Timer 2T6 (Cierre Tijera)';
            Condicion_Siguiente := T_2T6.Q;

            IF T_2T6.Q AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Paso_Pinza := 90;
            END_IF;

        90: // WHEN 2ND TIMER 6 HAS OVER -> Y7-OFF, CATCHER-ON
            // CORRECCION [1]: se espera el sensor S13 (cepillado cortado)
            // en lugar del temporizador T_NEW que quedaba colgado.
            Auto_Y7      := FALSE;
            Auto_Catcher := TRUE;
            Sensor_Esperado := 'Sensor S13 (Cepillado Cortado)';
            Condicion_Siguiente := S13;

            IF S13 AND (NOT S_STEP_BY_STEP OR BTN_STEP_Trig) THEN
                Auto_Y3 := FALSE;  // Y3-OFF al terminar
                Auto_Catcher := FALSE; // Suelta el cachador
                Paso_Pinza := 0;   // FIN DE CICLO
            END_IF;

    END_CASE;

END_IF;

// -----------------------------------------------------------------------------
// TEMPORIZADORES (TON)
// -----------------------------------------------------------------------------
T_2T5(IN := (Paso_Alambre = 10), PT := T#2.5S);
T_1T3(IN := (Paso_Pinza = 10),   PT := T#1.5S);
T_2T4(IN := (Paso_Pinza = 30),   PT := T#2.0S);
T_1T1(IN := (Paso_Pinza = 40),   PT := T#3.0S);
T_1T5(IN := (Paso_Alambre = 70), PT := T#1.5S);
T_2T7(IN := (Paso_Pinza = 60),   PT := T#2.0S);
T_2T6(IN := (Paso_Pinza = 80),   PT := T#1.5S);

// -----------------------------------------------------------------------------
// MULTIPLEXOR AUTOMATICO / MANUAL (ENTRADAS DE DEPURA)
//   SALIDA = SEL(S_MANUAL, Auto_*, CMD_*)
//   S_MANUAL=0 -> secuencia automatica ; S_MANUAL=1 -> forzado manual
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
Y24 := SEL(S_MANUAL, Auto_Catcher, CMD_Y24);  // CORRECCION [3]: salida fisica real

M1 := SEL(S_MANUAL, Auto_M1, CMD_M1);
M2 := SEL(S_MANUAL, Auto_M2, CMD_M2);
M3 := SEL(S_MANUAL, Auto_M3, CMD_M3);          // CORRECCION [2]: solo manual (Auto_M3=FALSE)

// -----------------------------------------------------------------------------
// ALARMAS  // CORRECCION [3]
// -----------------------------------------------------------------------------
H8 := NOT S23;  // Alarma baja presion: no hay presion neumatica
H3 := S8;       // Alarma nylon/cerda: sensor de cerda activo

// -----------------------------------------------------------------------------
// INDICADOR DE RETENCION / DIAGNOSTICO
// -----------------------------------------------------------------------------
// Condicion_Siguiente guarda el sensor/timer que se espera en cada paso.
// Falla_Bloqueante (retencion) se puede derivar en el HMI desde Paso_* y
// el valor de los sensores; se conserva Sensor_Esperado para display.

