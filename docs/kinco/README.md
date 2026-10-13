# Guia de sintaxis Kinco (K5 / KincoBuilder)

Guia derivada del **Capitulo VI - Kinco-K5 Instruction Set**
(`documentationkincoIL.txt`, archivado en `_fuente/`).
Cubre la sintaxis de las instrucciones en **IL** (y referencias a LD).

> Esta guia **no** cubre el mapeo de memoria `%VW/%I/%Q <-> Modbus`
> (pertenece a los capitulos 2-5 del manual, no incluidos aqui).

## Indice

| Sec. | Tema | Archivo |
|------|------|---------|
| 6.1 | Summary | [6.1-summary.md](6.1-summary.md) |
| 6.2 | Bit Logic Instructions | [6.2-bit-logic-instructions.md](6.2-bit-logic-instructions.md) |
| 6.3 | Move Instructions | [6.3-move-instructions.md](6.3-move-instructions.md) |
| 6.4 | Compare Instructions | [6.4-compare-instructions.md](6.4-compare-instructions.md) |
| 6.5 | Logical Operations | [6.5-logical-operations.md](6.5-logical-operations.md) |
| 6.6 | Shift/Rotate Instructions | [6.6-shift-rotate-instructions.md](6.6-shift-rotate-instructions.md) |
| 6.7 | Convert Instructions | [6.7-convert-instructions.md](6.7-convert-instructions.md) |
| 6.8 | Numeric Instructions | [6.8-numeric-instructions.md](6.8-numeric-instructions.md) |
| 6.9 | Program Control | [6.9-program-control.md](6.9-program-control.md) |
| 6.10 | Interrupt Instructions | [6.10-interrupt-instructions.md](6.10-interrupt-instructions.md) |
| 6.11 | Clock Instructions | [6.11-clock-instructions.md](6.11-clock-instructions.md) |
| 6.12 | Communication Instructions | [6.12-communication-instructions.md](6.12-communication-instructions.md) |
| 6.13 | Counters | [6.13-counters.md](6.13-counters.md) |
| 6.14 | Timers | [6.14-timers.md](6.14-timers.md) |
| 6.15 | PID | [6.15-pid.md](6.15-pid.md) |
| 6.16 | Position Control | [6.16-position-control.md](6.16-position-control.md) |
| 6.17 | Additional Instructions | [6.17-additional-instructions.md](6.17-additional-instructions.md) |

## Convenciones

- `CR`: Current Result (registro que fluye entre sentencias IL).
- `LD/LDN`: contacto normal / normal cerrado. `ST/STN`: bobina / bobina negada.
- `EN/ENO`: habilitacion de bloques (power flow en LD).
- Grupos: `C` contacto, `U` output, `P` funcion/bloque.

## Notas de conversion

- Fuente OCR ISO-8859-1 con finales CRLF/CR mixtos; normalizado a UTF-8/LF.
- Se eliminaron bloques de navegacion repetidos (`Parent Directory:`, `See Also:`).
- Tablas de operandos reconstruidas best-effort; revisar contra el PDF original.
