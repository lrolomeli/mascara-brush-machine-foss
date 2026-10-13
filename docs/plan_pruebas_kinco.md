# Plan de pruebas en KincoBuilder - Maquina Ma1

Protocolo de verificacion de `plc/generic_main.il` en KincoBuilder
(simulador / Online Monitor F6). Los numeros de `NETWORK` se refieren al IL.

> Antes de empezar: verificar el mapa `%I/%Q` y el E-stop segun
> [`verificacion_hardware.md`](verificacion_hardware.md).

## 0. Preparacion

- [ ] Cargar `plc/generic_main.il` en KincoBuilder y compilar (0 errores).
- [ ] Descargar al PLC (o abrir el simulador).
- [ ] Abrir **Online Monitor (F6)** y vigilar: `%VW400`, `%VW402`, `%M40.*`,
      `%M41.*`, `%M42.*`, `%M50.*`, `%M51.*`, `%M52.*`, `%Q*`, `%M70.*`.

## 1. Secuencias Alambre `AL_0..80` y Pinza `PZ_0..90`

- [ ] `S_MANUAL=0`, `S_STEP_BY_STEP=0`, `S1_EMERGENCY_STOP` (o `%M0.3`) = 1.
- [ ] Dar `S5_START` con `S14` (pinza abajo) activo.
- [ ] **Esperado**: `Paso_Alambre` recorre `0→10→20→30→40→50→60→70→80→0`
      y `Paso_Pinza` recorre `0→10→...→90→0` en paralelo.
- [ ] Verificar salidas por paso (ver tabla en
      [`maquina_referencia.md`](maquina_referencia.md) seccion 2).

## 2. Sincronizacion `AL_50` y cierre de ciclo `PZ_90`

- [ ] En `AL_50` (NETWORK 12): debe **esperar** `S20` (lengueta final) **y**
      `S16` (pinza arriba) antes de pasar a `AL_60`.
- [ ] **Esperado**: `Paso_Alambre` se queda en 50 hasta que ambos sensores
      estan ON.
- [ ] En `PZ_90` (NETWORK 26): cierra el ciclo con `S13` (cepillado cortado);
      al activarse, `Auto_Y3` y `Auto_Catcher` van a 0 y `Paso_Pinza=0`.

## 3. Modo paso a paso

- [ ] `S_STEP_BY_STEP=1` (`%M0.6`).
- [ ] **Esperado**: cada transicion de paso requiere un flanco de `BTN_STEP`
      (`%M2.4`); sin el pulso, el paso se congela.
- [ ] Verificar el flanco en `%M60.0` (disparo) y `%M60.1` (memoria).

## 4. Modo manual

- [ ] `S_MANUAL=1` (`%M0.5`).
- [ ] **Esperado**: `NETWORK 5` salta las secuencias (`JMPC PZ_END`) y
      `NETWORK 2` resetea pasos y `Auto_*`.
- [ ] Forzar salidas con `CMD_Y*`/`CMD_M*` y comprobar que `Y*`/`M*`
      siguen al `CMD` (multiplexor `NETWORK 28`).
- [ ] En manual, las salidas `Auto_*` no deben influir.

## 5. Paro de emergencia

- [ ] Con el ciclo en marcha, poner `%M0.3=0` (emergencia activa).
- [ ] **Esperado**: `NETWORK 2` resetea `Paso_Alambre=0`, `Paso_Pinza=0` y
      todos los `Auto_*`; `NETWORK 30` fuerza **todos** los `%Q` de actuadores
      a 0.
- [ ] Las alarmas `%Q2.3`/`%Q2.4` **no** se enclavan por E-stop (deben seguir
      indicando estado).

## 6. Alarmas

- [ ] `H8 = NOT S23` (NETWORK 29): con `S23=0` (sin presion) → `%M52.3=1`
      → `%Q2.3=1`.
- [ ] `H3 = S8` (NETWORK 29): con `S8=1` (cerda) → `%M52.4=1` → `%Q2.4=1`.
- [ ] Confirmar como llegan a la HMI (ver `verificacion_hardware.md` sec. 4).

## 7. Validacion offline (antes del PLC)

- [ ] `pytest` no aplica; ejecutar los scripts de `tests/`:
      - `python tests/test_io_map_consistency.py`
      - `python tests/test_routine_sim.py`
      - `python tests/test_adapter.py`
      - `python tests/test_sim_server.py`
- [ ] `tests/run_simulator.py` modela la secuencia del ST/IL sobre una planta
      fisica y usa el mapa del perfil (ya alineado a `%VW402`); sirve para
      ensayar el ciclo completo desde el HMI sin PLC.
