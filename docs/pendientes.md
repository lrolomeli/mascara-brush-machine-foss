# Pendientes a ejecutar

Estado: `plc/generic_main.il` compila en KincoBuilder con **0 errores** (commit
`2cb50ed`). El mapa HMI<->Modbus<->PLC ya esta alineado al IL; quedan tareas de
**verificacion en campo**.

## 1. Cuadrar mapa HMI <-> Modbus <-> PLC (prioridad alta) - HECHO (offline)

- [x] `Paso_Pinza` movido a **`%VW402`**; perfil `config/plc_profiles/generic_kinco.json`
      actualizado: `Paso_Pinza`/`STEP_NUMBER` = 402 y `MACHINE_STATE` = 404
      (para no colisionar con `%VW402`).
- [x] Eliminada la clave duplicada `S1_EMERGENCY_STOP` del JSON.
- [x] `docs/modbus_generic_map.md` regenerado (registros pares, nota E-stop,
      mapa de memoria del IL).
- [x] Test de consistencia `tests/test_io_map_consistency.py` (JSON <-> IL <-> IO-PLC.csv).
- [ ] Confirmar en KincoBuilder el mapeo **Modbus coil -> `%M`** del IL
      (byte.bit): `%M0.x`, `%M2.4` (BTN_STEP), `%M12.x..%M25.x` (CMD), etc.
- [ ] Confirmar la **base de coils de salida** (`1000+` en el perfil) vs `%Qx.y`
      del IL.

## 2. Hardware - DOCUMENTADO, pendiente de campo

- [x] `docs/IO-PLC.csv` alineado al IL (`%I/%Q`), con estado `VERIFICAR` por senal.
- [x] Plano original preservado en `docs/IO-PLC_plano_original.csv`.
- [x] Checklist en `docs/verificacion_hardware.md`.
- [ ] Verificar el **offset real de `%I`** de cada sensor S8..S23 segun cableado
      (el IL espera `%I1.0..%I1.7` = S8..S15 y `%I2.0..%I2.7` = S16..S23).
- [ ] Verificar la **asignacion de `%Q.x`** de las salidas fisicas segun plano
      (Y1..Y24/Y25, M1..M3, H8, H3).
- [ ] Confirmar que el **E-stop** fisico (`%I0.2`, DI 24) se refleja en `%M0.3`
      (`0` = emergencia activa); hoy falta el espejo `%I0.2 -> %M0.3` en el IL.

## 3. Pruebas en KincoBuilder (simulador / Online Monitor F6)

- [x] Protocolo en `docs/plan_pruebas_kinco.md`.
- [x] Tests offline en verde (`test_io_map_consistency`, `test_routine_sim`,
      `test_adapter`, `test_sim_server`).
- [ ] Secuencia Alambre `AL_0..80` y Pinza `PZ_0..90`.
- [ ] Sincronizacion: `AL_50` espera `S20` y `S16`; cierre de ciclo con `S13` (`PZ_90`).
- [ ] Modo paso a paso: `S_STEP_BY_STEP` congela el avance; `BTN_STEP` avanza un paso.
- [ ] Modo manual: `S_MANUAL` fuerza salidas via `CMD_*` y limpia `Auto_*`.
- [ ] E-stop: `%M0.3=0` apaga **todos** los `%Q` (actuadores) y resetea `Auto_*`/pasos.
- [ ] Alarmas: `H8=NOT S23`, `H3=S8` (`%M52.3`/`%M52.4` -> `%Q2.3`/`%Q2.4`).

## 4. Documentacion - HECHO

- [x] `documentationkincoIL.txt` convertido en guia de sintaxis por capitulo en
      [`docs/kinco/`](kinco/README.md) (17 archivos + README).
- [x] Original archivado en `docs/kinco/_fuente/documentationkincoIL.txt`.

## 5. Pruebas con PLC fisico (K615S-16DT) - EN CURSO

- [x] Guia paso a paso: [`docs/pruebas_plc_fisico.md`](pruebas_plc_fisico.md).
- [x] Programa PLC minimo de comunicacion: `plc/test_io.il` (CRLF).
- [x] Programa PLC de servo (pulsos+dir+enable): `plc/test_servo.il` (CRLF).
- [x] Script de comunicacion/descubrimiento: `tests/test_io_hardware.py`.
- [x] Script de servo/descubrimiento: `tests/test_servo_hardware.py`.
- [x] Perfil minimo HMI: `config/plc_profiles/test_kinco.json`.
- [x] Pestana HMI **"Test Servo"** (`hmi/ui/views/servo_test_view.py`).
- [x] **Mapeo Modbus confirmado** en el K615S-16DT:
      `holding = 100 + (byte de VW)/2` (`VW0->100`, `VW200->200`); `Q->coils`
      desde 0; `I->discrete` desde 0; ilegales `64..99`. El area **`%M` NO se
      expone** por Modbus TCP -> los comandos del HMI van en `%V` (holding).
- [x] Prueba de servo por script: ENABLE (`Q0.3`), MOVE absoluto (pulsos + `Q0.2`
      direccion), JOG. Validado en hardware (posicion `SMD212` cambia).
- [ ] Prueba por HMI (pestana "Test Servo").
- [ ] Restaurar `config/app_config.json` (backup `app_config.json.pre_plc_test.bak`).

## Referencia

- Codigo IL: `plc/generic_main.il` (720 lineas, CRLF) - **fuente de verdad**.
- Origen ST: `plc/generic_main.st`.
- Mapa Modbus: `docs/modbus_generic_map.md`.
- Perfil PLC: `config/plc_profiles/generic_kinco.json`.
- Mapa I/O + verificacion: `docs/IO-PLC.csv`, `docs/verificacion_hardware.md`.
- Guia de sintaxis Kinco: `docs/kinco/README.md`.
- `.gitattributes`: fuerza CRLF en `*.il` (KincoBuilder no acepta LF).
