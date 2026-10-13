(* ============================================================================ *)
(* KINCO K615S-16DT - PROGRAMA MINIMO DE PRUEBA DE COMUNICACION                 *)
(* Objetivo: verificar HMI <-> PLC <-> I/O fisica (ver docs/pruebas_plc_fisico.md)*)
(* ---------------------------------------------------------------------------- *)
(* %Q0.0 : coil 0 escrito por el HMI (boton virtual)                            *)
(* %Q0.1 : espejo de %Q0.0 -> el HMI lo lee (prueba HMI -> PLC -> programa)     *)
(* %I0.0 : boton fisico (entrada onboard)                                       *)
(* %Q0.2 : espejo de %I0.0 -> el HMI lo lee (prueba fisico -> PLC -> HMI)       *)
(* ---------------------------------------------------------------------------- *)
(* NOTA: si Kinco no permite escribir %Q por Modbus, usar la variante con %M    *)
(*       (misma logica, cambiando %Q0.0 por %M0.0 en el primer NETWORK).        *)
(* ============================================================================ *)

LD %Q0.0
ST %Q0.1

LD %I0.0
ST %Q0.2
