# Pendientes a ejecutar

Estado: `plc/generic_main.il` compila en KincoBuilder con **0 errores** (commit `2cb50ed`).
Quedan tareas de **verificacion e integracion** (no de compilacion del IL).

## 1. Cuadrar mapa HMI <-> Modbus <-> PLC (prioridad alta)

- [ ] `Paso_Pinza` se movio a **`%VW402`** porque `%VW401` (impar) es invalido en Kinco
      (`Error 041`). Hoy el HMI lee el registro Modbus **401**.
      Definir: perfil `config/plc_profiles/generic_kinco.json` -> `Paso_Pinza` a la direccion
      par correspondiente (p. ej. 402) o ajustar el mapeo `%VW` del esclavo Modbus.
- [ ] `MACHINE_STATE` esta en `402`; si `Paso_Pinza` pasa a 402, desplazar `MACHINE_STATE`
      (p. ej. 404) para evitar colision.
- [ ] Confirmar el mapeo **Modbus coil -> `%M`** usado por el IL (byte.bit):
      `%M0.0..%M0.7`, `%M1.0`, `%M1.1`, `%M2.4` (BTN_STEP), `%M12.x..%M25.x` (CMD), etc.
      Ver `docs/modbus_generic_map.md` y `config/plc_profiles/generic_kinco.json`.
- [ ] Confirmar el mapeo **discrete input Modbus -> `%I`** para los sensores S8..S23
      (hoy propuesto: S8..S15=`%I1.0..%I1.7`, S16..S23=`%I2.0..%I2.7`).

## 2. Hardware

- [ ] Verificar el **offset real de `%I`** de cada sensor fisico S8..S23 segun cableado.
- [ ] Verificar la **asignacion de `%Q.x`** de las salidas fisicas segun plano electrico
      (Y1..Y24, M1..M3, H8, H3).
- [ ] Confirmar que el **E-stop** se refleja en `%M0.3` con la polaridad esperada
      (`%M0.3=0` = emergencia activa), idealmente tambien por hardware.

## 3. Pruebas en KincoBuilder (simulador / Online Monitor F6)

- [ ] Secuencia Alambre `AL_0..80` y Pinza `PZ_0..90`.
- [ ] Sincronizacion: `AL_50` espera `S20` y `S16`; cierre de ciclo con `S13` (`PZ_90`).
- [ ] Modo paso a paso: `S_STEP_BY_STEP` congela el avance; `BTN_STEP` avanza un paso.
- [ ] Modo manual: `S_MANUAL` fuerza salidas via `CMD_*` y limpia `Auto_*`.
- [ ] E-stop: `%M0.3=0` apaga **todos** los `%Q` (actuadores) y resetea `Auto_*`/pasos.
- [ ] Alarmas: `H8=NOT S23`, `H3=S8` (`%M52.3`/`%M52.4` -> `%Q2.3`/`%Q2.4`).

## 4. Documentacion (decision)

- [ ] `docs/documentationkincoIL.txt` esta **sin trackear** (264 KB, manual Kinco convertido
      a texto). Decidir si se versiona, se mueve a otro repo/carpeta o se ignora.

## Referencia

- Codigo IL: `plc/generic_main.il` (720 lineas, CRLF).
- Origen ST: `plc/generic_main.st`.
- Mapa Modbus: `docs/modbus_generic_map.md`.
- Perfil PLC: `config/plc_profiles/generic_kinco.json`.
- `.gitattributes`: fuerza CRLF en `*.il` (KincoBuilder no acepta LF).
