# Visión General del Proyecto

## Propósito

Este proyecto implementa un receptor de datos meteorológicos que escucha las emisiones de radio de una estación **Bresser 5-en-1** (y potencialmente 6-en-1) en la banda de **868 MHz** usando una **Raspberry Pi Pico W** y un transceptor **CC1101**. Los datos decodificados (temperatura, humedad, viento y lluvia) se envían periódicamente a una API REST mediante Wi-Fi.

## Hardware

| Componente | Descripción |
|---|---|
| Raspberry Pi Pico W | Microcontrolador RP2040 doble core con Wi-Fi integrado (CYW43439) |
| CC1101 | Transceptor RF de Texas Instruments, 315/433/868/915 MHz |
| Estación Bresser 5-en-1 | Estación meteorológica que emite en 868 MHz con protocolo propietario |

## Conexionado CC1101 ↔ Pico W

```
CC1101     →   Raspberry Pi Pico W
-------        -------------------
VCC        →   3V3 (pin 36)
GND        →   GND
MOSI       →   GP19 (SPI0 TX)
MISO       →   GP16 (SPI0 RX)
SCLK       →   GP18 (SPI0 SCK)
CSN        →   GP17 (SPI0 CS)  [+ resistencia 10kΩ Pull-Up a 3.3V]
GDO0       →   GP20  (opcional, fin de paquete → IRQ)
GDO2       →   GP21  (opcional, estado radio)
```

## Software

- **Firmware**: MicroPython 1.28 para RP2 Pico
- **IDE recomendado**: Thonny, rshell o mpremote
- **Sin dependencias externas**: solo módulos incluidos en el firmware oficial

## Estructura de directorios activa

```
src/
├── main.py              Punto de entrada, bucle principal, hilos, IRQ
├── env.py               Configuración activa (credenciales, pines, flags)
├── .env.example.py      Plantilla vacía de env.py
├── Drivers/
│   └── CC1101.py        Driver SPI de bajo nivel para el CC1101
└── Models/
    ├── WeatherSensor.py  Wrapper radio + decodificador Bresser 5/6-en-1
    ├── Api.py            Cliente HTTP para la API REST
    └── RpiPico.py        Abstracción de hardware del Pico W
```

Los directorios `old_c_project/` y `old_python_project/` son referencias históricas de solo lectura y **no forman parte del código activo**.

## Flujo general de funcionamiento

```
Arranque
  │
  ├─ Conectar Wi-Fi (RpiPico.wifi_connect)
  ├─ Inicializar SPI bus 0
  ├─ Inicializar CC1101 a 868 MHz (WeatherSensor.begin)
  ├─ Sincronizar RTC por NTP
  ├─ Configurar IRQ en GDO0 (flanco de bajada)
  └─ Lanzar hilo de procesado en Core 1

Bucle principal (Core 0)
  │
  ├─ Polling FIFO CC1101 → paquetes al doble buffer
  ├─ Rotar buffer cuando lleno o expirado BATCH_WINDOW_MS
  ├─ Heartbeat LED
  ├─ Parpadeo alterno no bloqueante
  └─ Subir payload a API cuando el hilo 1 lo indica

Hilo de procesado (Core 1)
  │
  ├─ Esperar lote listo
  ├─ Decodificar tramas Bresser (6-en-1 → 5-en-1)
  ├─ Agregar temp/humedad/viento/lluvia
  └─ Señalar payload completo al Core 0
```

## Modos de operación

### Modo normal (producción)
`FIND_STATION_IDS = False`, `SENSOR_IDS_INC` con el ID de la estación. Decodifica, agrega y sube a la API.

### Modo descubrimiento de IDs
`FIND_STATION_IDS = True`. Solo imprime por consola los IDs detectados sin subir nada. Útil para identificar el ID de la propia estación entre vecinas.

### Modo diagnóstico
`DEBUG = True`, `DECODE_DEBUG = True`. Verbose completo de cada trama recibida, intentos de decodificación y causas de rechazo.
