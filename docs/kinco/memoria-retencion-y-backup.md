# Memoria retentiva y backup (Kinco K5 / K6S)

El PLC Kinco tiene **dos mecanismos distintos** para conservar datos al apagar.
Conviene no confundirlos: uno es **retencion en RAM** (bateria/supercapacitor) y
el otro es **backup permanente en memoria no volatil** (E²PROM/FRAM).

> **Aviso**: los manuales K5 y K6 no describen `VB3648-VB4095` con exactamente la
> misma semantica. Verificar en el **help de KincoBuilder (Apendice)** del modelo
> concreto antes de apoyarse en un rango para datos criticos.

---

## 1. Retencion (RAM + bateria/supercapacitor)

- Mantiene el **estado instantaneo de la RAM** al perder energia.
- Se configuran hasta **4 rangos retentivos** en KincoBuilder:
  `Hardware -> Reten` (p. ej. area `V`, area `C`/contadores).
- Duracion a temperatura normal:
  - **Supercapacitor**: ~**72 h (3 dias)**. Cargar >= 10 min antes de usar.
  - **Bateria de litio**: hasta **~3 anos**.
- Se pierde todo si la bateria/supercap se agota.

## 2. Backup permanente (E²PROM / FRAM)

- Zona del area `V` que se **escribe automaticamente a memoria no volatil**;
  sobrevive apagados largos (no depende de bateria).
- Se habilita en KincoBuilder: `Hardware -> Others`.
- **Rangos por modelo**:

| Modelo | Area de backup | Observacion |
|--------|----------------|-------------|
| K5 (compatibilidad) | `VB3648 - VB4095` | 448 bytes |
| K6 / K6S (compatibilidad) | `VB15360 - VB16383` | solo K6/K6S |
| K3 | `VB3648 - VB3902` | solo K3 |

- En **K615S-16DT (K6S)** estan disponibles `VB3648-VB4095` y
  `VB15360-VB16383` (se pueden habilitar juntas).
- **Limite de escritura**: la E²PROM soporta ~**1 000 000 de escrituras**.
  **No** guardar ahi datos que cambian con frecuencia (usar `V` normal o
  retencion para eso). El FRAM (en algunos K5) tiene escritura practicamente
  ilimitada.

---

## Como elegir

| Necesidad | Mecanismo recomendado |
|-----------|------------------------|
| Parametros/contadores que deben sobrevivir apagados largos | **Backup E²PROM** (`VB3648-VB4095` / `VB15360-VB16383`) |
| Estado que cambia seguido y basta con sobrevivir horas | **Retencion** (RAM + bateria/supercap) |
| Dato volatil de trabajo | `V`/`M` normal (no retentivo) |

## Uso tipico

1. Guardar parametros de la maquina (velocidades, offsets, calibraciones) en la
   zona de **backup** para que no se pierdan al apagar.
2. Escribir esos valores **solo cuando cambian** (no cada scan) para no agotar
   la E²PROM.
3. En el arranque (`%SM0.1`, primer scan), cargar los valores de backup a las
   variables de trabajo.

## Referencias

- K5 Hardware Manual: seccion FRAM / Retentive Ranges.
- K6/K6S User Manual: `Hardware -> Reten` y `Hardware -> Others` (Data Backup).
- KincoBuilder Help -> Apendice A (SM area) y capitulo de Troubleshooting.
