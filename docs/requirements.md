# Requisitos de la Maquina Industrial

## Hardware

- **HMI**: Pantalla tactil industrial 1920x1080 corriendo Linux
- **PLC**: Cualquier marca soportada via Modbus TCP (Delta DVP, Kinco K6, Siemens S7-1200, Schneider, etc.)
- **Servomotor**: 1 servo con control de velocidad, posicion y modo Jog
- **Valvulas**: 10 valvulas/pistones neumaticos individuales (on/off)
- **Sensores**: 2 sensores inductivos u opticos (booleanos)

## Entradas de Operador (Botones Fisicos)

| Boton          | Funcion                           | Prioridad |
|----------------|-----------------------------------|-----------|
| Start          | Iniciar ciclo automatico          | Normal    |
| Cycle Stop     | Paro al final del ciclo actual    | Normal    |
| Pause          | Pausa temporal del ciclo          | Normal    |
| E-Stop         | Paro de emergencia inmediato      | Critica   |

## Modos de Operacion

| Modo           | Descripcion                                                   |
|----------------|---------------------------------------------------------------|
| Automatico     | Ejecucion continua del ciclo de produccion                    |
| Manual         | Activacion directa e individual de las 10 valvulas            |
| Paso a Paso    | Avance paso a paso con boton "Paso Siguiente"                 |
| Depuracion     | Prueba por secciones con lectura/escritura directa de tags    |

## Seguridad

- E-Stop debe detener TODOS los actuadores inmediatamente
- El PLC debe validar que E-Stop este desactivado antes de permitir arranque
- Estado de maquina se reporta al HMI en cada ciclo de polling

## Comunicacion

- Protocolo: Modbus TCP (puerto 502 por defecto)
- Polling rate: 100ms (configurable)
- Perfiles de direccionamiento por PLC cargados desde JSON
- Sin modificaciones al codigo HMI para cambiar de PLC
