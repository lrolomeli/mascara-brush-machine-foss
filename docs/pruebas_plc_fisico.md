# Pruebas con PLC fisico (Kinco K615S-16DT)

Guia paso a paso para comprobar, con el PLC real, que:

1. **HMI -> PLC**: un boton virtual del display llega al PLC y activa una salida.
2. **PLC -> HMI**: un boton fisico del PLC se refleja en el display.

Objetivo de la primera fase: **solo comunicacion**, sin la maquina conectada.
Programa de prueba: [`plc/test_io.il`](../plc/test_io.il).
Script de prueba: [`tests/test_io_hardware.py`](../tests/test_io_hardware.py).

> **Seguridad**: usar una fuente de 24 VDC pequena y aislada. No conectar la
> maquina ni actuadores reales en esta fase.

---

## 0. Material y esquema de red

- PLC **K615S-16DT** (8 DI / 8 DO onboard).
- Fuente **24 VDC** para el PLC.
- Cable **Ethernet** (el puerto hace auto-negociacion; sirve directo o cruzado).
- Un **boton/pulsador** (o switch) para `%I0.0`.
- Los **LEDs onboard** de las salidas `%Q0.0/%Q0.1/%Q0.2` (no hace falta cablear LED).
- PC **Windows** con **KincoBuilder** (para programar).
- PC **Linux** con este repo (para el HMI).

Red (misma subred, ultimo octeto distinto):

| Equipo | IP | Mascara |
|--------|----|---------|
| PLC K615S | `192.168.0.252` (fabrica) | `255.255.255.0` |
| PC Windows (KincoBuilder) | `192.168.0.10` | `255.255.255.0` |
| PC Linux (HMI) | `192.168.0.20` | `255.255.255.0` |

---

## 1. Conexiones fisicas simples

1. Alimentar el PLC con 24 VDC (respetar polaridad).
2. Cable Ethernet: PC Windows <-> PLC (para programar). Mas tarde se cambia al PC Linux.
3. Boton fisico entre el **COM** de las DI y `%I0.0`.
   - K615S soporta **PNP/NPN**; revisar el comun (0V para PNP, +24V para NPN).
4. Salidas: usar los **LEDs onboard** de `%Q0.0`, `%Q0.1`, `%Q0.2`.

---

## 2. Configurar el PLC en KincoBuilder (PC Windows)

1. **Red del PC**: fijar `192.168.0.10/24`.
2. Abrir KincoBuilder y conectar por Ethernet:
   - `Tools -> TCP/IP parameter configuration -> Read` para leer la IP del PLC.
   - Fijar la IP del PLC en **`192.168.0.252`** y pulsar `Write`.
   - `PC Communication Settings` -> usar **TCP/IP** con la IP del PLC.
3. **Habilitar Modbus TCP Server**:
   - Abrir `PLC Hardware Configuration` -> CPU -> pagina de comunicacion/ethernet.
   - Asegurar que el **Modbus TCP Server (esclavo)** esta habilitado y anotar el
     **unit/slave id** (normalmente 1) y el puerto (**502**).
4. **Obtener el mapa Modbus real** (clave):
   - En la ayuda de KincoBuilder, abrir el **Apendice A - Modbus Register Number**.
   - Copiar la tabla de rangos por area (`Q`, `M`, `I`, `VW`/`V`, `AIW`/`AQW`).
   - Esta tabla es la que debe cuadrar el perfil JSON (ver Seccion 5).

---

## 3. Descargar el programa de prueba

1. KincoBuilder -> **Nuevo proyecto** -> CPU **K615S-16DT** (+ modulos de expansion
   si la maquina los usa; para esta prueba no hacen falta).
2. Crear el programa principal y pegar el contenido de `plc/test_io.il`
   (esta en **CRLF**, como exige KincoBuilder).
3. **Compilar** (0 errores) y **Descargar** al PLC.
4. Poner el PLC en **RUN**.

Logica del programa:

```
LD %Q0.0   ; coil 0 escrito por el HMI (boton virtual)
ST %Q0.1   ; espejo -> el HMI lee coil 1
LD %I0.0   ; boton fisico
ST %Q0.2   ; espejo -> el HMI lee coil 2
```

---

## 4. Pasar al PC Linux

1. Desconectar el PC Windows del PLC.
2. Conectar el PC Linux al PLC y fijar `192.168.0.20/24`.
3. Comprobar red:

```bash
ping -c 3 192.168.0.252
```

---

## 5. Descubrir/confirmar el mapeo Modbus

Antes de dar por buenos los tags, confirmar en que direcciones Modbus aparecen
`%Q`, `%I` y `%M`:

```bash
.venv/bin/python tests/test_io_hardware.py --ip 192.168.0.252 --scan
```

- Escribe el **coil 0** y reporta que coils/discrete/registros cambian.
- Comparar con el **Apendice A** de KincoBuilder.
- Si `coil 0` no corresponde a `%Q0.0` (p. ej. el area `M` empieza en otra
  direccion), **ajustar** `config/plc_profiles/test_kinco.json` y, si aplica,
  el primer `NETWORK` de `plc/test_io.il`.

> Convencion esperada en la familia Kinco: `0x -> Q y M`, `1x -> I y M`,
> `4x -> AQ y V`, `3x -> AI y V`. El offset exacto del area `M` depende del CPU.

---

## 6. Prueba HMI -> PLC (boton virtual)

```bash
.venv/bin/python tests/test_io_hardware.py --ip 192.168.0.252 --hmi-to-plc
```

- Escribe `coil 0` y debe activarse `coil 1` (espejo del programa).
- **Esperado**: `[OK] HMI -> PLC -> programa` y el LED onboard de `%Q0.1` encendido.

Con el **HMI real**:
1. `./run_hmi.sh`.
2. En **Configuracion**: IP `192.168.0.252`, perfil **"Kinco Test I/O"**, `TEST CONEXION`.
3. Cambiar a **AUTOMATIC** y pulsar **INICIO** (escribe `coil 0`).
4. En **Actuadores**, la fila **"Y1 Orientadores"** (`CMD_Y1` -> coil 1) se ilumina.

---

## 7. Prueba PLC -> HMI (boton fisico)

```bash
.venv/bin/python tests/test_io_hardware.py --ip 192.168.0.252 --plc-to-hmi --watch 15
```

- Pulsar el boton de `%I0.0`: `discrete 0` y `coil 2` deben ir a ON.
- **Esperado**: `[OK] boton fisico -> PLC -> HMI`.

Con el **HMI real**: en **Sensores**, el LED de **"S8"** (mapeado a `discrete 0`)
se enciende al pulsar el boton.

---

## 8. Criterios de aceptacion

- [ ] `ping 192.168.0.252` responde.
- [ ] `--scan` identifica las direcciones de `%Q`/`%I` (coinciden con Apendice A).
- [ ] `--hmi-to-plc` -> `[OK]` (coil 0 activa coil 1).
- [ ] `--plc-to-hmi` -> `[OK]` (boton fisico activa discrete 0 y coil 2).
- [ ] HMI real: INICIO ilumina la fila Y1; el boton fisico ilumina S8.

---

## 9. Troubleshooting

| Sintoma | Causa probable | Accion |
|---------|----------------|--------|
| No conecta / timeout | IP o subred distinta; Modbus Server off; firewall | Revisar IPs, habilitar Modbus TCP Server, `ping` |
| Conecta pero `coil 1` no responde | Mapeo distinto (coil 0 != `%Q0.0`) | Correr `--scan`; ajustar perfil/IL |
| El HMI no escribe `%Q` | Kinco no permite escribir `%Q` por Modbus | Usar la **variante `%M`** (Seccion 10) |
| `%I0.0` siempre OFF/ON | Común PNP/NPN mal o cableado | Revisar COM y polaridad |
| unit id incorrecto | Server configurado con otro id | Ajustar `--unit` y el perfil |

---

## 10. Variante con `%M` (si no se puede escribir `%Q` por Modbus)

Cambiar el primer `NETWORK` de `plc/test_io.il` por:

```
LD %M0.0
ST %Q0.1
```

Y en `config/plc_profiles/test_kinco.json`, apuntar `CMD_START` (y demas botones)
a la direccion Modbus del area `M` segun el Apendice A (p. ej. `M0.0` suele estar
en un offset > 0). Confirmar con `--scan`.

---

## 11. Prueba de servo (pulsos + direccion + enable)

Programa: [`plc/test_servo.il`](../plc/test_servo.il). Script:
[`tests/test_servo_hardware.py`](../tests/test_servo_hardware.py). Vista HMI:
pestana **"Test Servo"**.

### 11.1 Senales

| Senal | PLC | Rol |
|-------|-----|-----|
| In-position ready | `%I0.0` | Entrada del driver (HMI lee) |
| Proximidad / HOME | `%I0.1` | Entrada (HMI lee, referencia de home) |
| Tren de pulsos | `%Q0.0` | AXIS 0 (pulso) |
| Direccion | `%Q0.2` | AXIS 0 (direccion automatica) |
| Servo ON / enable | `%Q0.3` | DO normal |

> El K5/K6 usa **AXIS 0 = `Q0.0` pulso + `Q0.2` direccion** en las instrucciones
> de Position Control (`PHOME`/`PABS`/`PJOG`/`PSTOP`). Frecuencia 125 Hz–200 kHz.

### 11.2 Areas de memoria (por que los comandos van en `%M`)

| Area | Que es | Pin fisico | Uso |
|------|--------|-----------|-----|
| `%I` | Entradas | Si (lectura) | Sensores/botones |
| `%Q` | Salidas | **Si** | Actuadores cableados |
| `%M` | Memorias internas | **No** | **Comandos/flags del HMI** |
| `%V` | Palabras de datos | No | Parametros (holding) |
| `%SM` | Bits de sistema | No | PTO/posicion (`SM201`, `SMD212`) |

**Regla**: los comandos del HMI van en `%M` (no en `%Q`), para no energizar
bornes sin cablear ni ocupar salidas reales. Patron:
`HMI --coil--> %M --programa--> %Q`.

Comandos: `%M0.0` ENABLE, `%M0.1` HOME, `%M0.2` MOVE, `%M0.3` JOG+, `%M0.4` JOG-,
`%M0.5` STOP. Parametros en `%V`: `VW100` MINF, `VW102` TIME, `VD104` MAXF,
`VD108` POS, `VW112` DIRC, `VW114` MODE, `VW120` DIRC de jog (interno). Estado:
`VD116` = posicion actual (copia de `SMD212`).

> **Nota de compilacion**: en `PJOG`, `MAXF` y `DIRC` deben ser **ambos constantes
> o ambos variables**. Por eso el jog usa `DIRC` en `%VW120` (variable), no una
> constante.

### 11.3 Descubrir el mapeo de `%M` y `%V`

El programa deja **marcadores**:
- `%M1.0=1, %M1.2=1, %M1.4=1` (patron `10101`).
- `%VW200 = 0x1234` (4660).

```bash
.venv/bin/python tests/test_servo_hardware.py --ip 192.168.0.252 --scan
```

El script reporta el **offset del area M** (donde aparece el patron) y el
**offset del area V** (donde aparece `0x1234`). Ajustar las direcciones en
`config/plc_profiles/test_kinco.json` y, si cambia la base, en el IL.

### 11.4 Secuencia de prueba

```bash
# Estado (entradas, posicion, salidas)
.venv/bin/python tests/test_servo_hardware.py --ip 192.168.0.252 --status

# Habilitar servo
.venv/bin/python tests/test_servo_hardware.py --ip 192.168.0.252 --enable on

# Home (usa I0.1)
.venv/bin/python tests/test_servo_hardware.py --ip 192.168.0.252 --home

# Mover a 20000 pulsos
.venv/bin/python tests/test_servo_hardware.py --ip 192.168.0.252 --move 20000

# Jog 3 s y parar
.venv/bin/python tests/test_servo_hardware.py --ip 192.168.0.252 --jog fwd --watch 3
```

Con el **HMI**: pestana **Test Servo** -> `ENABLE`, `HOME`, fijar `POS` y `MOVER`,
`JOG +/-`, `STOP`. Los LEDs muestran `IN POSITION`, `HOME`, `DIR`, `ENABLE` y el
display la **posicion actual**.

### 11.5 Criterios de aceptacion (servo)

- [ ] `--scan` identifica offset de `M` y de `V`.
- [ ] `ENABLE` enciende `Q0.3` (LED onboard) y `SERVO_ENABLE`.
- [ ] `HOME` mueve hacia `I0.1` y `SMD212` se acerca a 0.
- [ ] `MOVE` desplaza el numero de pulsos y `SMD212` lo refleja.
- [ ] `DIR` (`Q0.2`) cambia segun el sentido.
- [ ] `STOP` detiene el movimiento.

---

## 12. Restaurar la configuracion

- `config/app_config.json` se ajusto a `192.168.0.252` para esta prueba; al
  terminar, restaurar el backup `config/app_config.json.pre_plc_test.bak` si se
  desea volver al valor anterior.
- El perfil `test_kinco.json` es **solo para pruebas**; en produccion usar
  `generic_kinco`.
