# VCG.md — Guía del proyecto para agentes de vibe coding

Lee este documento al inicio de la sesión. Contiene todo el contexto necesario
sobre el proyecto HMI industrial y **qué archivo modificar según la tarea**,
para no tener que revisar todo el source.

---

## 1. Qué es este proyecto

HMI industrial **PLC-agnóstico** en Python (PySide6 + pymodbus) para el control
de una **cepilladora / máscara brush ("Ma1")**. Se comunica con el PLC por
**Modbus TCP**; el mapeo de variables es **configurable por perfil JSON**, así
que cambiar de PLC no requiere tocar código.

El PLC ejecuta una rutina en **Structured Text (ST)** con 2 máquinas de estado
paralelas (rama Alambre y rama Pinza), sincronizadas, y un **multiplexor
Auto/Manual** (`SEL(S_MANUAL, Auto_*, CMD_*)`) para forzar salidas desde el HMI.

- PLC objetivo: **Kinco K5s / K615S 16DT** (soportan ST + Modbus TCP).
- Perfil activo: `generic_kinco`.
- Idioma del código/comentarios: **español** (mantener esa convención).
- Python 3.10+, `PySide6>=6.6`, `pymodbus>=3.6` (ver `requirements.txt`).

---

## 2. Mapa de archivos

| Ruta | Responsabilidad |
|------|-----------------|
| `hmi/main.py` | Punto de entrada. Configura tema oscuro, carga `app_config.json`, resuelve el perfil activo, crea `ModbusTCPAdapter` + `ModbusWorker` + `MainWindow`. |
| `hmi/comms/plc_adapter.py` | Capa Modbus. Clases: `TagInfo` (tipo+dirección), `PLCProfile` (lee JSON, método `from_json`), `PLCAdapter` (ABC), `ModbusTCPAdapter` (lectura en batch con `_merge_ranges`, escritura por tag). **NO tocar salvo cambio de protocolo.** |
| `hmi/comms/modbus_worker.py` | `QThread` de polling (100 ms). Señales: `data_ready(dict)`, `connection_status(bool)`, `error_occurred(str)`. Métodos: `enqueue_write(tag, value)`, `configure(...)`, `load_new_profile(path)`, `stop()`. |
| `hmi/ui/main_window.py` | Ventana principal. Crea las 6 pestañas, **conecta las señales de cada view al worker** y llama `update_data(data)` en `_on_data`. |
| `hmi/ui/widgets.py` | Componentes reutilizables: `ValveToggle` (señal `toggled_signal(int, bool)`), `StatusLED`, `SectionFrame`, `IndustrialButton`, `ServoPositionDisplay`. |
| `hmi/ui/views/*.py` | Una clase por pestaña: `auto_view`, `manual_view`, `servo_view`, `outputs_debug_view`, `debug_view`, `settings_view`. |
| `config/app_config.json` | IP/puerto/`unit_id`/`timeout_ms`/`active_profile` + polling + tamaño de pantalla. |
| `config/plc_profiles/generic_kinco.json` | **Perfil ACTIVO** (95 tags): mapeo simbólico→Modbus real. Otros: `generic_modbus.json`, `delta_dvp.json`. |
| `plc/generic_main.st` | Rutina ST de producción (2 ramas + mux Auto/Manual + alarmas). |
| `tests/run_simulator.py` + `run_simulator.sh` | Simulador Modbus TCP con datos de demo (para probar sin PLC físico). |
| `tests/test_adapter.py` | Test de escritura/lectura del adapter contra un simulador interno. |
| `docs/modbus_generic_map.md` | **Mapa completo** de nombres simbólicos ↔ direcciones Modbus + secuencia. |
| `docs/maquina_referencia.md` | Referencia de diseño/depuración: I/O real, tablas de pasos, forzado manual. |
| `docs/requirements.md` | Requisitos de hardware y modos de operación. |
| `run_hmi.sh`, `run_simulator.sh` | Scripts de lanzamiento (crean `.venv` e instalan dependecias si falta). |

---

## 3. Flujo de datos (cómo funciona)

```
[Vista Qt] --señal (tag, valor)-->  worker.enqueue_write(tag, valor)
                                          |
                                          v
[ModbusWorker polling]  ---------->  adapter.read_all_inputs()  (batch)
                                          |
                    data_ready(dict) <----+  dict[tag] = valor
                                          |
                                          v
                MainWindow._on_data(data) -->  cada view.update_data(data)
```

- **Consulta de datos**: el worker emite `data_ready(data)` en cada poll; cada
  vista implementa `update_data(data: dict)` y lee `data.get("mi_tag")`.
- **Escritura**: la vista emite una señal, que en `main_window.py` se conecta
  a `lambda tag, v: self._worker.enqueue_write(tag, v)`.
- **Nombres simbólicos**: el HMI nunca usa direcciones Modbus en duro; hace
  referencia a los nombres del perfil JSON.

---

## 4. Cómo añadir un NUEVO tag / salida / sensor

Ejemplo: añadir la salida física `Y25` (cachador atrás) o un sensor nuevo.
Hay que tocar archivos en este orden:

1. **`config/plc_profiles/generic_kinco.json`** — dentro de `"tags"` añade:
   ```json
   "Y25": { "type": "coil", "address": <libre>, "description": "Cachador atras" }
   ```
   Tipos válidos: `coil` (salidas/forzados/botones), `discrete_input` (sensores),
   `holding_register` (estados como `Paso_Alambre`), `input_register` (solo lectura).

2. **Si es salida física forzable manualmente**: añade también su memoria de
   forzado, p. ej. `"CMD_Y25": { "type": "coil", "address": <libre>, "description": "Forzado manual Y25" }`.

3. **Si debe verse en una pestaña**: añade la entrada a la lista correspondiente
   de la vista, p. ej. `DEBUG_OUTPUTS` en `hmi/ui/views/outputs_debug_view.py`
   (formato `("CMD_Yx", "Yx Etiqueta")`) o `MANUAL_OUTPUTS` en `manual_view.py`.

4. **Documenta**: añade la fila en `docs/modbus_generic_map.md` (tabla de salidas
   o sensores).

5. **Si aplica al PLC**: declara la variable en `plc/generic_main.st` (bloque
   `VAR`) y, si es salida forzable, agrega al multiplexor:
   `Yx := SEL(S_MANUAL, Auto_Yx, CMD_Yx);`

> **Regla de direcciones**: usa direcciones libres. Los `CMD_Y*` están ~100–123
> (memorias de forzado), las salidas físicas `Y*` ~1000–1023, motores `M*` ~200/1100,
> alarmas `H*` ~1200. Verifica en el JSON qué direcciones ya están ocupadas.

---

## 5. Cómo añadir una NUEVA pestaña / vista

Pasos exactos (modelo: `outputs_debug_view.py`, la última vista añadida):

1. Crea `hmi/ui/views/<nombre>_view.py` con una clase `QWidget` de estilo
   consistente (usa `SectionFrame`, `ValveToggle`, `StatusLED` de `widgets.py`).
   - Define señales propias para acciones del usuario (p. ej. `Signal(str, bool)`).
   - Implementa `update_data(self, data: dict)`.
2. En `hmi/ui/main_window.py`:
   - Importa la clase nueva.
   - Instánciala (`self._mi_view = MiView()`) donde están las demás vistas.
   - Añádela: `self._tabs.addTab(self._mi_view, "Nombre Pestaña")`.
   - Conecta sus señales de escritura al worker.
   - Llama `self._mi_view.update_data(data)` dentro de `_on_data`.
3. Actualiza la tabla de pestañas en `README.md` si quieres.

---

## 6. Convenciones importantes

- **Nombres simbólicos, nunca direcciones hardcodeadas.**
- Salidas se fuerzan escribiendo coils `CMD_*`; el PLC combina con
  `SEL(S_MANUAL, Auto_*, CMD_*)`.
- Sensores reales: `S8`–`S23` (discrete inputs). Botonera: `S5_START`, `S3_STOP`,
  `S1_EMERGENCY_STOP`, `S_MANUAL`, `S_STEP_BY_STEP`, `BTN_STEP`.
- Registros de estado: `Paso_Alambre`, `Paso_Pinza` (holding registers).
- ST: memorias automáticas `Auto_*`, forzado manual `CMD_*`, salidas físicas `Y*`/`M*`,
  alarmas `H8`, `H3`.
- `CMD_Y5` (depuración, "sale pinza") y `CMD_Y9` (producción, "sube/baja pinza")
  **coexisten** en el perfil — no los confundas.
- Comentarios en código **en español**.
- `plc/generic_main.st` es la **fuente de producción**; `docs/maquina_referencia.md`
  es solo referencia (contiene las tablas de pasos retiradas).

---

## 7. Comandos útiles

```bash
# Probar el adapter (levantar simulador interno + validar R/W)
.venv/bin/python tests/test_adapter.py

# Simulador local (sin PLC físico)
./run_simulator.sh 0.0.0.0 5020 generic_kinco

# HMI (lee config/app_config.json)
./run_hmi.sh
```

**IMPORTANTE al hacer pruebas locales:**
- La config por defecto apunta al **PLC real** (`192.168.1.10:502`). Para probar
  sin PLC, apunta al simulador: o bien edita temporalmente `config/app_config.json`
  a `127.0.0.1:5020`, o cambia IP/puerto en la pestaña **Configuración** del HMI.
- **Siempre restaura** `config/app_config.json` a la IP real después de probar
  (haz backup antes con `cp config/app_config.json /tmp/...`).

---

## 8. Gotchas / qué evitar

- No tocar `config/app_config.json` sin backup, ni commitearlo con IP del simulador.
- No hardcodear direcciones Modbus en el HMI; todo debe pasar por el perfil JSON.
- Al forzar salidas (modo manual) recuerda que se requiere `S_MANUAL = ON` en el PLC.
- No edites `hmi/comms/plc_adapter.py` salvo que cambies el protocolo de comunicación.
- Al añadir tags, verifica que las direcciones no colisionen con las existentes.
- El simulador reporta avisos de deprecación de pymodbus en el log: son inofensivos.
