# Verificacion de hardware - Maquina Ma1

Checklist para cuadrar el cableado/plano fisico con el mapa declarado en
`plc/generic_main.il` (fuente de verdad). El detalle por senal esta en
[`IO-PLC.csv`](IO-PLC.csv); el plano original en
[`IO-PLC_plano_original.csv`](IO-PLC_plano_original.csv).

> Estado: **pendiente de verificar en campo**. Las filas marcadas `VERIFICAR`
> en `IO-PLC.csv` son discrepancias entre el plano original y el mapa del IL.

## 1. Entradas fisicas (`%I`) - sensores S8..S23

El IL espeja entradas de forma **secuencial** en `NETWORK 1`:

- `S8..S15` = `%I1.0..%I1.7`
- `S16..S23` = `%I2.0..%I2.7`

El plano original reparte los sensores en `%I0.x/%I1.x/%I2.x` de forma no
secuencial. Hay que **verificar el offset real de cada sensor** y:

- [ ] Medir/confirmar el pin `%I` de cada sensor S8..S23.
- [ ] Si no coincide: re-cablear, o ajustar el mapeo `%I` del esclavo Modbus /
      el espejo `NETWORK 1` del IL (requiere tocar el IL, hoy no se hace).
- [ ] Confirmar que el orden de `%I1.0..%I2.7` corresponde a S8..S23 en ese
      orden exacto.

## 2. Salidas fisicas (`%Q`) - Y*, M*, H*

El IL copia las salidas deseadas `%M50.0..%M52.4` a `%Q` en `NETWORK 30`:

| Salida | IL `%Q` | Modbus (perfil) |
|--------|---------|-----------------|
| Y1 | `%Q0.0` | coil 1000 |
| Y3 | `%Q0.1` | coil 1002 |
| Y6 | `%Q0.2` | coil 1005 |
| Y7 | `%Q0.3` | coil 1006 |
| Y8 | `%Q0.4` | coil 1007 |
| Y9 | `%Q0.5` | coil 1008 |
| Y10 | `%Q0.6` | coil 1009 |
| Y11 | `%Q0.7` | coil 1010 |
| Y12 | `%Q1.0` | coil 1011 |
| Y14 | `%Q1.1` | coil 1013 |
| Y15 | `%Q1.2` | coil 1014 |
| Y16 | `%Q1.3` | coil 1015 |
| Y17 | `%Q1.4` | coil 1016 |
| Y18 | `%Q1.5` | coil 1017 |
| Y24 | `%Q1.6` | coil 1023 |
| M1 | `%Q2.0` | coil 1100 |
| M2 | `%Q2.1` | coil 1101 |
| M3 | `%Q2.2` | coil 1102 |
| H8 | `%Q2.3` | coil 1200 |
| H3 | `%Q2.4` | coil 1201 |

- [ ] Confirmar la asignacion de `%Q.x` de cada actuador segun el plano
      electrico (Y1..Y24/Y25, M1..M3, H8, H3).
- [ ] Confirmar la **base Modbus de los coils de salida** (hoy `1000+` en el
      perfil): como expone KincoBuilder cada `%Qx.y` por Modbus.
- [ ] Verificar que `Y25` (Cachador atras) no se usa en el IL; decidir si se
      mapea o se elimina.

## 3. Paro de emergencia

El IL usa `%M0.3` (`0` = emergencia activa):

- [ ] Confirmar que el E-stop fisico (`%I0.2`, DI 24) se refleja en `%M0.3`
      (hoy **no** hay espejo `%I0.2 -> %M0.3` en el IL; solo lo escribe la HMI
      via `CMD_ESTOP`, coil 3).
- [ ] Confirmar la polaridad (`%M0.3=0` = emergencia) e idealmente enclavar
      tambien por hardware (rele de seguridad).

## 4. Alarmas H8 / H3

El IL calcula `H8 = NOT S23` y `H3 = S8` y las escribe en `%Q2.3/%Q2.4`.
La HMI las lee como **discrete inputs 1200/1201**.

- [ ] Decidir como llegan las alarmas a la HMI (leer `%Q` por coils, o espejar
      `%Q2.3/%Q2.4` a los discrete 1200/1201).
- [ ] Confirmar que la polaridad coincide con lo que espera la HMI.

## 5. Selector continuo (`S4_CONTINUOUS`)

- [ ] El IL **no usa** `S4_CONTINUOUS`. Decidir si se implementa el ciclo
      continuo o se retira del HMI/perfil.
