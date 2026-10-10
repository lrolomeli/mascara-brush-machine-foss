(* ============================================================================ *)
(* KINCO K5/K6 - KincoBuilder - Maquina Ma1 Cepilladora / Brush Mask            *)
(* Programa principal en IL, traducido de plc/generic_main.st                   *)
(* Comentarios SIEMPRE de una sola linea. Direcciones % directas.               *)
(* Arquitectura 3 capas: %I -> %M (espejo) ; logica en %M ; %M -> %Q (copia)    *)
(* Seguridad: E-stop (%M0.3=0) resetea pasos/Auto y fuerza los actuadores a 0   *)
(* ---------------------------------------------------------------------------- *)
(* MAPA DE MEMORIA (propuesto; verificar contra hardware/Modbus)                *)
(* Botonera/modos: S5_START=%M0.0 S3_STOP=%M0.1 S1_EMERGENCY_STOP=%M0.3        *)
(*   S_MANUAL=%M0.5 S_STEP_BY_STEP=%M0.6 BTN_STEP=%M2.4                         *)
(* Sensores espejo: S8=%M30.0 S9=%M30.1 S10=%M30.2 S11=%M30.3 S12=%M30.4        *)
(*   S13=%M30.5 S14=%M30.6 S15=%M30.7 S16=%M31.0 S17=%M31.1 S18=%M31.2          *)
(*   S19=%M31.3 S20=%M31.4 S21=%M31.5 S22=%M31.6 S23=%M31.7                     *)
(* Sensores fisicos (%I, verificar offset): S8..S15=%I1.0..%I1.7 S16..S23=%I2.0..%I2.7 *)
(* Forzado manual: CMD_Y1=%M12.4 CMD_Y3=%M12.6 CMD_Y6=%M13.1 CMD_Y7=%M13.2      *)
(*   CMD_Y8=%M13.3 CMD_Y9=%M13.4 CMD_Y10=%M13.5 CMD_Y11=%M13.6 CMD_Y12=%M13.7   *)
(*   CMD_Y14=%M14.1 CMD_Y15=%M14.2 CMD_Y16=%M14.3 CMD_Y17=%M14.4 CMD_Y18=%M14.5 *)
(*   CMD_Y24=%M15.3 CMD_M1=%M25.0 CMD_M2=%M25.1 CMD_M3=%M25.2                   *)
(* Auto: Y1=%M40.0 Y3=%M40.1 Y6=%M40.2 Y7=%M40.3 Y8=%M40.4 Y9=%M40.5            *)
(*   Y10=%M40.6 Y11=%M40.7 Y12=%M41.0 Y14=%M41.1 Y15=%M41.2 Y16=%M41.3          *)
(*   Y17=%M41.4 Y18=%M41.5 CATCHER=%M41.6 M1=%M41.7 M2=%M42.0 M3=%M42.1         *)
(* Salidas deseadas: %M50.0..%M52.4 (ver copia a %Q)                            *)
(* Flags: BTN_STEP_Trig=%M60.0 BTN_STEP_Mem=%M60.1                              *)
(* Timers: T20..T26 (100ms). Bits de estado: %M70.0..%M70.6                     *)
(* Pasos: Paso_Alambre=%VW400 Paso_Pinza=%VW402 (direcciones pares)             *)
(* Salidas fisicas %Q: Y1=%Q0.0 Y3=%Q0.1 Y6=%Q0.2 Y7=%Q0.3 Y8=%Q0.4 Y9=%Q0.5    *)
(*   Y10=%Q0.6 Y11=%Q0.7 Y12=%Q1.0 Y14=%Q1.1 Y15=%Q1.2 Y16=%Q1.3 Y17=%Q1.4      *)
(*   Y18=%Q1.5 Y24=%Q1.6 M1=%Q2.0 M2=%Q2.1 M3=%Q2.2 H8=%Q2.3 H3=%Q2.4          *)
(* ============================================================================ *)


(* NETWORK 1: Espejo de entradas fisicas %I -> %M *)
LD %I1.0
ST %M30.0
LD %I1.1
ST %M30.1
LD %I1.2
ST %M30.2
LD %I1.3
ST %M30.3
LD %I1.4
ST %M30.4
LD %I1.5
ST %M30.5
LD %I1.6
ST %M30.6
LD %I1.7
ST %M30.7
LD %I2.0
ST %M31.0
LD %I2.1
ST %M31.1
LD %I2.2
ST %M31.2
LD %I2.3
ST %M31.3
LD %I2.4
ST %M31.4
LD %I2.5
ST %M31.5
LD %I2.6
ST %M31.6
LD %I2.7
ST %M31.7


(* NETWORK 2: Reset por paro de emergencia / STOP / manual (con seguridad) *)
(* Antes en ST: IF NOT S1_EMERGENCY_STOP OR S3_STOP OR S_MANUAL THEN reset    *)
LDN %M0.3
OR  %M0.1
OR  %M0.5
MOVE 0, %VW400
MOVE 0, %VW402
R   %M40.0
R   %M40.1
R   %M40.2
R   %M40.3
R   %M40.4
R   %M40.5
R   %M40.6
R   %M40.7
R   %M41.0
R   %M41.1
R   %M41.2
R   %M41.3
R   %M41.4
R   %M41.5
R   %M41.6
R   %M41.7
R   %M42.0
R   %M42.1


(* NETWORK 3: Flanco de subida del boton de avance manual BTN_STEP *)
LD   %M2.4
ANDN %M60.1
ST   %M60.0

LD   %M2.4
ST   %M60.1


(* NETWORK 4: Subproceso orientador (Y1 / S9) *)
LD %M30.6
S  %M40.0

LD %M30.1
R  %M40.0


(* NETWORK 5: Si esta en manual, saltar las secuencias automaticas *)
LD   %M0.5
JMPC PZ_END


(* NETWORK 6: Despacho CASE Paso_Alambre *)
LD %SM0.0
EQ %VW400, 0
JMPC AL_0

LD %SM0.0
EQ %VW400, 10
JMPC AL_10

LD %SM0.0
EQ %VW400, 20
JMPC AL_20

LD %SM0.0
EQ %VW400, 30
JMPC AL_30

LD %SM0.0
EQ %VW400, 40
JMPC AL_40

LD %SM0.0
EQ %VW400, 50
JMPC AL_50

LD %SM0.0
EQ %VW400, 60
JMPC AL_60

LD %SM0.0
EQ %VW400, 70
JMPC AL_70

LD %SM0.0
EQ %VW400, 80
JMPC AL_80
JMP AL_END


(* NETWORK 7: Rama Alambre - Paso 0: espera inicio S5_START y S14 *)
AL_0:
LD   %M0.0
AND  %M30.6
MOVE 10, %VW400
JMP  AL_END


(* NETWORK 8: Paso 10 - S14 -> Y15/Y14/Y9 ON ; espera S18 *)
AL_10:
LD  %SM0.0
S   %M41.2
S   %M41.1
S   %M40.5

LDN %M0.6
OR  %M60.0
AND %M31.2
MOVE 20, %VW400
JMP AL_END


(* NETWORK 9: Paso 20 - S18 -> Y17 ON ; espera S21 *)
AL_20:
LD  %SM0.0
S   %M41.4

LDN %M0.6
OR  %M60.0
AND %M31.5
MOVE 30, %VW400
JMP AL_END


(* NETWORK 10: Paso 30 - S21 -> Y17 OFF, Y15 OFF ; espera S19 *)
AL_30:
LD  %SM0.0
R   %M41.4
R   %M41.2

LDN %M0.6
OR  %M60.0
AND %M31.3
MOVE 40, %VW400
JMP AL_END


(* NETWORK 11: Paso 40 - S19 -> Y18 ON ; espera S22 *)
AL_40:
LD  %SM0.0
S   %M41.5

LDN %M0.6
OR  %M60.0
AND %M31.6
MOVE 50, %VW400
JMP AL_END


(* NETWORK 12: Paso 50 - S22 -> Y16 ON ; sincronizacion S20 y S16 *)
AL_50:
LD  %SM0.0
S   %M41.3

LDN %M0.6
OR  %M60.0
AND %M31.4
AND %M31.0
MOVE 60, %VW400
JMP AL_END


(* NETWORK 13: Paso 60 - S20 y S16 -> Y18 OFF, Y12 ON ; espera S17 *)
AL_60:
LD  %SM0.0
R   %M41.5
S   %M41.0

LDN %M0.6
OR  %M60.0
AND %M31.1
MOVE 70, %VW400
JMP AL_END


(* NETWORK 14: Paso 70 - S17 -> Y14 OFF, Y10 ON, Y16 OFF ; espera timer 1T5 *)
AL_70:
LD  %SM0.0
R   %M41.1
S   %M40.6
R   %M41.3

LDN %M0.6
OR  %M60.0
AND %M70.4
MOVE 80, %VW400
JMP AL_END


(* NETWORK 15: Paso 80 - fin 1T5 -> Y12 OFF ; termina ciclo de alambre *)
AL_80:
LD  %SM0.0
R   %M41.0
MOVE 0, %VW400
JMP AL_END


(* NETWORK 16: Despacho CASE Paso_Pinza *)
AL_END:
LD %SM0.0
EQ %VW402, 0
JMPC PZ_0

LD %SM0.0
EQ %VW402, 10
JMPC PZ_10

LD %SM0.0
EQ %VW402, 20
JMPC PZ_20

LD %SM0.0
EQ %VW402, 30
JMPC PZ_30

LD %SM0.0
EQ %VW402, 40
JMPC PZ_40

LD %SM0.0
EQ %VW402, 50
JMPC PZ_50

LD %SM0.0
EQ %VW402, 60
JMPC PZ_60

LD %SM0.0
EQ %VW402, 70
JMPC PZ_70

LD %SM0.0
EQ %VW402, 80
JMPC PZ_80

LD %SM0.0
EQ %VW402, 90
JMPC PZ_90
JMP PZ_END


(* NETWORK 17: Rama Pinza - Paso 0: espera Paso_Alambre >= 10 y timer 2T5 *)
PZ_0:
LD  %SM0.0
GE  %VW400, 10
AND %M70.0
MOVE 10, %VW402
JMP PZ_END


(* NETWORK 18: Paso 10 - 2T5 -> Y3 ON, Y10 OFF ; espera timer 1T3 *)
PZ_10:
LD  %SM0.0
S   %M40.1
R   %M40.6

LDN %M0.6
OR  %M60.0
AND %M70.1
MOVE 20, %VW402
JMP PZ_END


(* NETWORK 19: Paso 20 - 1T3 -> Y11 OFF, Y12 OFF ; espera S15 *)
PZ_20:
LD  %SM0.0
R   %M40.7
R   %M41.0

LDN %M0.6
OR  %M60.0
AND %M30.7
MOVE 30, %VW402
JMP PZ_END


(* NETWORK 20: Paso 30 - S15 -> M1 ON, Y9 OFF ; espera S10 *)
PZ_30:
LD  %SM0.0
S   %M41.7
R   %M40.5

LD  %M70.2
R   %M41.7

LDN %M0.6
OR  %M60.0
AND %M30.2
MOVE 40, %VW402
JMP PZ_END


(* NETWORK 21: Paso 40 - S10 -> M2/Y6/Y11 ON, Catcher OFF ; espera timer 1T1 *)
PZ_40:
LD  %SM0.0
S   %M42.0
S   %M40.2
S   %M40.7
R   %M41.6

LDN %M0.6
OR  %M60.0
AND %M70.3
MOVE 50, %VW402
JMP PZ_END


(* NETWORK 22: Paso 50 - 1T1 -> M2 OFF, Y6 OFF ; espera S11 *)
PZ_50:
LD  %SM0.0
R   %M42.0
R   %M40.2

LDN %M0.6
OR  %M60.0
AND %M30.3
MOVE 60, %VW402
JMP PZ_END


(* NETWORK 23: Paso 60 - S11 -> Y7 ON ; espera S12 *)
PZ_60:
LD  %SM0.0
S   %M40.3

LDN %M0.6
OR  %M60.0
AND %M30.4
MOVE 70, %VW402
JMP PZ_END


(* NETWORK 24: Paso 70 - S12 -> Y8 ON ; espera timer 2T7 *)
PZ_70:
LD  %SM0.0
S   %M40.4

LDN %M0.6
OR  %M60.0
AND %M70.5
MOVE 80, %VW402
JMP PZ_END


(* NETWORK 25: Paso 80 - 2T7 -> Y8 OFF ; espera timer 2T6 *)
PZ_80:
LD  %SM0.0
R   %M40.4

LDN %M0.6
OR  %M60.0
AND %M70.6
MOVE 90, %VW402
JMP PZ_END


(* NETWORK 26: Paso 90 - 2T6 -> Y7 OFF, Catcher ON ; cierra ciclo con S13 *)
PZ_90:
LD  %SM0.0
R   %M40.3
S   %M41.6

LDN %M0.6
OR  %M60.0
AND %M30.5
JMPC PZ_FIN
JMP  PZ_END

PZ_FIN:
LD  %SM0.0
R   %M40.1
R   %M41.6
MOVE 0, %VW402
JMP PZ_END


(* NETWORK 27: Temporizadores TON (base 100ms) *)
PZ_END:
LD  %SM0.0
EQ  %VW400, 10
TON T20, 25
ST  %M70.0

LD  %SM0.0
EQ  %VW402, 10
TON T21, 15
ST  %M70.1

LD  %SM0.0
EQ  %VW402, 30
TON T22, 20
ST  %M70.2

LD  %SM0.0
EQ  %VW402, 40
TON T23, 30
ST  %M70.3

LD  %SM0.0
EQ  %VW400, 70
TON T24, 15
ST  %M70.4

LD  %SM0.0
EQ  %VW402, 60
TON T25, 20
ST  %M70.5

LD  %SM0.0
EQ  %VW402, 80
TON T26, 15
ST  %M70.6


(* NETWORK 28: Multiplexor Auto/Manual  Y = (S_MANUAL AND CMD) OR (NOT S_MANUAL AND Auto) *)
LD  %M0.5
AND %M12.4
OR(
LDN %M0.5
AND %M40.0
)
ST  %M50.0

LD  %M0.5
AND %M12.6
OR(
LDN %M0.5
AND %M40.1
)
ST  %M50.1

LD  %M0.5
AND %M13.1
OR(
LDN %M0.5
AND %M40.2
)
ST  %M50.2

LD  %M0.5
AND %M13.2
OR(
LDN %M0.5
AND %M40.3
)
ST  %M50.3

LD  %M0.5
AND %M13.3
OR(
LDN %M0.5
AND %M40.4
)
ST  %M50.4

LD  %M0.5
AND %M13.4
OR(
LDN %M0.5
AND %M40.5
)
ST  %M50.5

LD  %M0.5
AND %M13.5
OR(
LDN %M0.5
AND %M40.6
)
ST  %M50.6

LD  %M0.5
AND %M13.6
OR(
LDN %M0.5
AND %M40.7
)
ST  %M50.7

LD  %M0.5
AND %M13.7
OR(
LDN %M0.5
AND %M41.0
)
ST  %M51.0

LD  %M0.5
AND %M14.1
OR(
LDN %M0.5
AND %M41.1
)
ST  %M51.1

LD  %M0.5
AND %M14.2
OR(
LDN %M0.5
AND %M41.2
)
ST  %M51.2

LD  %M0.5
AND %M14.3
OR(
LDN %M0.5
AND %M41.3
)
ST  %M51.3

LD  %M0.5
AND %M14.4
OR(
LDN %M0.5
AND %M41.4
)
ST  %M51.4

LD  %M0.5
AND %M14.5
OR(
LDN %M0.5
AND %M41.5
)
ST  %M51.5

LD  %M0.5
AND %M15.3
OR(
LDN %M0.5
AND %M41.6
)
ST  %M51.6

LD  %M0.5
AND %M25.0
OR(
LDN %M0.5
AND %M41.7
)
ST  %M52.0

LD  %M0.5
AND %M25.1
OR(
LDN %M0.5
AND %M42.0
)
ST  %M52.1

(* M3: solo manual (Auto_M3 siempre FALSE) *)
LD  %M0.5
AND %M25.2
ST  %M52.2


(* NETWORK 29: Alarmas *)
LDN %M31.7
ST  %M52.3

LD  %M30.0
ST  %M52.4


(* NETWORK 30: Copia de salidas %M -> %Q con enclavamiento de seguridad *)
(* Los actuadores se multiplican por S1_EMERGENCY_STOP (1=normal), de modo     *)
(* que si el paro de emergencia esta activo TODOS los actuadores van a 0.      *)
LD  %M50.0
AND %M0.3
ST  %Q0.0

LD  %M50.1
AND %M0.3
ST  %Q0.1

LD  %M50.2
AND %M0.3
ST  %Q0.2

LD  %M50.3
AND %M0.3
ST  %Q0.3

LD  %M50.4
AND %M0.3
ST  %Q0.4

LD  %M50.5
AND %M0.3
ST  %Q0.5

LD  %M50.6
AND %M0.3
ST  %Q0.6

LD  %M50.7
AND %M0.3
ST  %Q0.7

LD  %M51.0
AND %M0.3
ST  %Q1.0

LD  %M51.1
AND %M0.3
ST  %Q1.1

LD  %M51.2
AND %M0.3
ST  %Q1.2

LD  %M51.3
AND %M0.3
ST  %Q1.3

LD  %M51.4
AND %M0.3
ST  %Q1.4

LD  %M51.5
AND %M0.3
ST  %Q1.5

LD  %M51.6
AND %M0.3
ST  %Q1.6

LD  %M52.0
AND %M0.3
ST  %Q2.0

LD  %M52.1
AND %M0.3
ST  %Q2.1

LD  %M52.2
AND %M0.3
ST  %Q2.2

(* Alarmas: no enclavadas por E-stop (deben indicar estado) *)
LD  %M52.3
ST  %Q2.3

LD  %M52.4
ST  %Q2.4


(* ============================================================================ *)
(* VERIFICACION antes de bajar al PLC                                            *)
(* [ ] Offset %I <-> discrete input Modbus (S8..S23)                            *)
(* [ ] Asignacion %Q.x segun plano electrico/cableado                           *)
(* [ ] Mapeo Modbus coil -> %M coincide con la config del esclavo               *)
(* [ ] E-stop (%M0.3=0) apaga TODOS los actuadores y resetea pasos/Auto         *)
(* [ ] Comprobar secuencia y sincronizacion (S20/S16) y cierre con S13          *)
(* ============================================================================ *)
