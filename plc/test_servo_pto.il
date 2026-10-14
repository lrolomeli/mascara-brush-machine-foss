(* ============================================================================ *)
(* KINCO K615S-16DT - TEST SERVO: TREN DE PULSOS CONTINUO, FRECUENCIA VARIABLE  *)
(* ---------------------------------------------------------------------------- *)
(* %Q0.0 = tren de pulsos continuo (generador alta velocidad PWM0, base 1 us).  *)
(* %Q0.3 = servo ON (enable), DO normal.                                        *)
(* La frecuencia barre en triangulo entre ~1 kHz y ~10 kHz.                     *)
(* Sin HMI: programa minimo para cargar al PLC.                                  *)
(* ---------------------------------------------------------------------------- *)
(* %VW100 = ciclo en us (100..1000)  -> frecuencia = 1000000 / ciclo            *)
(* %VW102 = ancho de pulso en us (ciclo/2, duty 50%)                            *)
(* %M0.0  = sentido del barrido: 1 = bajar ciclo (subir freq) ; 0 = subir ciclo *)
(* %M0.4  = flag de base de tiempo de 100 ms (pulso de un ciclo)                *)
(* ============================================================================ *)

(* NETWORK 1: Servo ON (%Q0.3) *)
LD %SM0.0
ST %Q0.3


(* NETWORK 2: Inicializacion (primer ciclo): ciclo inicial y sentido del barrido *)
LD %SM0.1
MOVE 550, %VW100      (* ciclo inicial = 550 us (~1.8 kHz) *)
LD %SM0.1
S %M0.0               (* %M0.0=1 -> bajar ciclo (subir frecuencia) *)


(* NETWORK 3: Base de tiempo de 100 ms, auto-reset (flag de un solo ciclo) *)
LDN %M0.4
TON T20, 1
ST  %M0.4


(* NETWORK 4: Cambio de sentido del barrido en los limites *)
LD %M0.4
EQ %VW100, 1000
S  %M0.0              (* en 1000 us -> empezar a bajar ciclo *)
LD %M0.4
EQ %VW100, 100
R  %M0.0              (* en 100 us -> empezar a subir ciclo *)


(* NETWORK 5: Paso del barrido (10 us cada 100 ms) *)
LD %M0.0
AND %M0.4
SUB 10, %VW100        (* bajar ciclo (subir frecuencia) *)
LDN %M0.0
AND %M0.4
ADD 10, %VW100        (* subir ciclo (bajar frecuencia) *)


(* NETWORK 6: Ancho de pulso = ciclo / 2 (duty 50%) *)
LD %SM0.1
OR %M0.4
MOVE %VW100, %VW102
LD %SM0.1
OR %M0.4
DIV 2, %VW102


(* NETWORK 7: Configurar/actualizar y arrancar PWM0 -> %Q0.0 *)
LD %SM0.1
OR %M0.4
MOVE B#16#D3, %SMB67  (* enable + PWM + base 1us + update ciclo y ancho *)
LD %SM0.1
OR %M0.4
MOVE %VW100, %SMW68   (* ciclo (periodo) en us *)
LD %SM0.1
OR %M0.4
MOVE %VW102, %SMW70   (* ancho de pulso en us *)
LD %SM0.1
OR %M0.4
PLS 0                 (* PWM0 -> %Q0.0 *)
