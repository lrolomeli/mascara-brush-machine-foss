(* ============================================================================ *)
(* KINCO K615S-16DT - PRUEBA DE SERVO (tren de pulsos + direccion + enable)     *)
(* ---------------------------------------------------------------------------- *)
(* AXIS 0 (Position Control): Q0.0 = PULSOS, Q0.2 = DIRECCION (automatica).      *)
(* Q0.3 = servo ON (enable), DO normal.                                          *)
(* Entradas: I0.0 = in-position ready, I0.1 = sensor de proximidad (HOME).       *)
(* Comandos del HMI en %M (memorias internas, NO ocupan salidas fisicas).        *)
(* Parametros en %V (holding registers).                                         *)
(* Ver docs/pruebas_plc_fisico.md                                              *)
(* ---------------------------------------------------------------------------- *)
(* MAPA DE MEMORIA (ajustar segun Apendice A de KincoBuilder / --scan)          *)
(* Comandos:  %M0.0=ENABLE %M0.1=HOME %M0.2=MOVE %M0.3=JOG+ %M0.4=JOG- %M0.5=STOP*)
(* Patron M (descubrir offset area M): %M1.0=1 %M1.2=1 %M1.4=1                  *)
(* Parametros: %VW100=MINF %VW102=TIME %VD104=MAXF %VD108=POS                  *)
(*             %VW112=DIRC %VW114=MODE                                          *)
(* Estado:     %VD116=POS_ACT (copia de %SMD212)  %VW200=0x1234 (marcador V)    *)
(* Salidas fisicas: %Q0.0 pulso  %Q0.2 dir  %Q0.3 enable                        *)
(* ============================================================================ *)

(* NETWORK 1: ENABLE -> servo ON (%Q0.3) y reset del flag E-stop de posicion *)
LD %M0.0
ST %Q0.3

LD %M0.0
R  %SM201.7


(* NETWORK 2: HOME (PHOME AXIS 0; MODE=1 usa solo HOME=I0.1) *)
LD %SM0.0
PHOME 0, %M0.1, %I0.1, %M9.0, %VW114, %VW112, %VW100, %VD104, %VW102, %M2.0, %M2.1, %MB3


(* NETWORK 3: MOVE absoluto (PABS AXIS 0, POS=%VD108) *)
LD %SM0.0
PABS 0, %M0.2, %VW100, %VD104, %VW102, %VD108, %M2.2, %M2.3, %MB4


(* NETWORK 4: JOG adelante (PJOG AXIS 0, DIRC=0) *)
LD %SM0.0
PJOG 0, %M0.3, %VD104, 0, %M2.4, %M2.5, %MB5


(* NETWORK 5: JOG atras (PJOG AXIS 0, DIRC=1) *)
LD %SM0.0
PJOG 0, %M0.4, %VD104, 1, %M2.6, %M2.7, %MB6


(* NETWORK 6: STOP (PSTOP AXIS 0) *)
LD %SM0.0
PSTOP 0, %M0.5, %M3.0, %MB7


(* NETWORK 7: Copia de la posicion actual (%SMD212 -> %VD116 para el HMI) *)
LD %SM0.0
MOVE %SMD212, %VD116


(* NETWORK 8: Patron conocido para descubrir el offset Modbus del area M *)
LD %SM0.0
S %M1.0
S %M1.2
S %M1.4


(* NETWORK 9: Marcador para descubrir el offset Modbus del area V (0x1234) *)
LD %SM0.0
MOVE 4660, %VW200
