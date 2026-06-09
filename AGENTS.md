# AGENTS.md — Guía para desarrollar este proyecto con MicroPython

Este archivo describe el contexto, arquitectura y convenciones que debe seguir cualquier agente (humano o IA) que trabaje en este proyecto.

---

## Descripción del proyecto

Receptor de datos de estación meteorológica Bresser 5-en-1 / 6-en-1 corriendo en una **Raspberry Pi Pico W** con MicroPython. El hardware de RF es un transceptor **CC1101** conectado por SPI que escucha a **868 MHz**. Los datos decodificados se suben a una API REST externa mediante Wi-Fi.

El proyecto es **solo recepción (RX)**; no emite señal alguna.

---

## Directorios relevantes

```
src/                 ← Código fuente activo. AQUÍ se trabaja.
  main.py            ← Bucle principal, IRQ GDO0, doble buffer, hilos
  env.py             ← Variables de entorno (credenciales, pines, flags)
  .env.example.py    ← Plantilla de env.py para nuevas instalaciones
  Drivers/
    CC1101.py        ← Driver SPI del transceptor CC1101
  Models/
    WeatherSensor.py ← Wrapper de alto nivel + decodificador Bresser
    Api.py           ← Cliente HTTP para la API REST
    RpiPico.py       ← Abstracción de hardware (Wi-Fi, SPI, I2C, ADC, RTC)

docs/
  info/              ← Documentación técnica detallada (Markdown)
  images/            ← Esquemas y fotos del hardware

old_c_project/       ← Proyecto C en ESP32. SOLO REFERENCIA para debugging.
old_python_project/  ← Versión Python anterior. SOLO REFERENCIA.
```

**Nunca modificar** `old_c_project/` ni `old_python_project/`. Son referencias de solo lectura para resolver dudas sobre algoritmos o comportamientos conocidos.

---

## Entorno de ejecución

- **Hardware**: Raspberry Pi Pico W (RP2040, doble core)
- **Firmware**: MicroPython 1.28+ para RP2 Pico
- **Python target**: MicroPython — sin CPython stdlib completa
- **Módulos disponibles en MicroPython**: `machine`, `network`, `urequests`, `ujson`, `utime`/`time`, `_thread`, `micropython`, `ntptime`, `gc`, `urandom`, `binascii`
- **Módulos NO disponibles**: `typing` (se shimea), `asyncio` (no se usa), `threading` (se usa `_thread`)

### Restricciones MicroPython importantes

- No usar f-strings en código muy crítico de memoria (aunque MicroPython 1.28 las soporta).
- `_thread` en RP2040 ejecuta el segundo hilo en **Core 1** — hay que proteger los recursos compartidos con `_thread.allocate_lock()`.
- `micropython.schedule()` es la única forma segura de hacer trabajo pesado desde una ISR (no hacer SPI dentro de IRQ).
- `gc.collect()` debe llamarse periódicamente en el bucle principal para evitar fragmentación de heap.
- No usar `time.sleep()` (bloquea); usar `sleep_ms()` de `time` o `utime`.

---

## Arquitectura de dos hilos

```
Core 0 (main.py bucle while True)
  ├─ Polling rápido del FIFO del CC1101 (ws.receive timeout=0)
  ├─ Escribe paquetes en el buffer activo (bufA o bufB)
  ├─ Rota el lote cuando está lleno o expira BATCH_WINDOW_MS
  ├─ Gestiona subida a la API (api.send_to_api)
  ├─ Heartbeat LED + parpadeo no bloqueante
  └─ IRQ GDO0 → micropython.schedule(_on_gdo0_scheduled)

Core 1 (processor_thread)
  ├─ Espera lotes marcados como ready (batch_ready[])
  ├─ Decodifica cada trama (ws.decode)
  ├─ Agrega temp/humidity/wind/rain
  └─ Cuando el conjunto está completo → _set_upload_payload()
```

La comunicación entre hilos usa variables globales + `_thread.allocate_lock()`. No usar `queue` (no existe en MicroPython).

---

## Flujo de recepción de un paquete

1. CC1101 recibe una trama en 868 MHz.
2. **GDO0 baja** (fin de paquete) → dispara `_gdo0_irq` (ISR).
3. ISR aplica debounce y llama `micropython.schedule(_on_gdo0_scheduled)`.
4. Handler programado lee hasta 3 paquetes del FIFO (`ws.receive(timeout_ms=0)`).
5. Llama `ws.decode(pkt)` → intenta 6-en-1 luego 5-en-1.
6. Si `crc_ok`, guarda en `last_valid_decoded` y señala parpadeo de LEDs.
7. En paralelo, el bucle principal también hace polling del FIFO y escribe en el doble buffer (bufA/bufB).
8. El hilo de Core 1 procesa lotes, agrega variables meteorológicas y cuando tiene un conjunto completo (temp + humedad + viento + lluvia) deja el payload en `payload_to_upload`.
9. El bucle principal detecta el payload pendiente y llama `api.send_to_api(payload)`.

---

## Decodificación Bresser

### Bresser 6-en-1 (18 bytes)

La trama válida tiene 18 bytes. Verificación:
- `digest = LFSR16(msg[2:17], gen=0x8810, init=0x5412)` debe coincidir con `(msg[0]<<8)|msg[1]`
- Suma de `msg[2:18]` debe ser `0xFF` (módulo 256)

Campos extraídos:
- `sensor_id`: bytes 2..5 (32 bits big-endian)
- `type`: nibble alto de byte 6
- `chan`: nibble bajo de byte 6 (bits 0-2)
- **Temperatura** (BCD): nibbles de bytes 15-16; si `raw > 600` → negativo como `(raw-1000)*0.1`
- **Humedad** (BCD): byte 17
- **Viento**: bytes 7-9 invertidos (`^ 0xFF`), BCD; dirección en bytes 10-11
- **Lluvia**: bytes 12-14 invertidos, BCD 6 dígitos → mm * 0.1

### Bresser 5-en-1 (26 bytes)

Verificación:
- **Paridad**: `msg[col] ^ msg[col+13] == 0xFF` para col 0..12
- **Checksum**: conteo de bits 1 en `msg[14:26]` debe igualar `msg[13]`

Campos extraídos:
- `sensor_id`: byte 14 (8 bits)
- `type`: `msg[15] & 0x7F` (bit7 = flag de arranque)
- **Temperatura** (BCD): bytes 20-21; signo en nibble bajo de byte 25
- **Humedad** (BCD): byte 22
- **Viento**: dirección = `(msg[17] & 0x0F) * 22.5`; ráfaga de bytes 16-17; media de bytes 18-19
- **Lluvia** (BCD): bytes 23-24; si `type >= 0x39 && <= 0x3B` (pluviómetro profesional), multiplicar por 2.5

### Estrategia de decodificación

```
packet recibido
  │
  ├─ Stripping del byte de longitud (modo variable-length del CC1101)
  │
  ├─ Fast path 6-in-1: primeros 18 bytes → _decode_6in1
  │
  ├─ Layout 27 bytes con packet[0]==0xD4 → msg = packet[1:27] → _try_decoders
  ├─ Layout 26 bytes → msg = packet[:26] → _try_decoders
  │
  └─ Sliding window (si ALLOW_SLIDING_DECODE=True)
       ├─ Ventanas de 18B para 6-in-1
       └─ Ventanas de 26B para _try_decoders
```

---

## Configuración (env.py)

Todos los parámetros viven en `src/env.py`. Nunca hardcodear credenciales en otro sitio.

Variables críticas que un agente debe tener en cuenta al desarrollar:

| Variable | Efecto |
|---|---|
| `ENABLE_CC1101` | Activa/desactiva el receptor RF |
| `CC1101_PKT_LEN` | Longitud máxima de paquete (recomendado 40) |
| `CC1101_FREQ_HZ` | Frecuencia central (868000000 o 868300000) |
| `CC1101_BW_DEFAULT` | Ancho de banda RX ('270k' o '250k') |
| `FIND_STATION_IDS` | Modo descubrimiento de IDs (sin subida a API) |
| `SENSOR_IDS_INC` | Filtro positivo de IDs |
| `SENSOR_IDS_EXC` | Filtro negativo de IDs |
| `ALLOW_SLIDING_DECODE` | Ventana deslizante para tramas desalineadas |
| `DECODE_DEBUG` | Log detallado de fallos de decodificación |
| `FORCE_BRESSER_MODEL` | Forzar modelo: None, '5in1' o '6in1' |
| `FIND_ID_STRICT` | Exige checksum además de paridad en búsqueda 5-en-1 |
| `BATCH_SIZE` | Tamaño del lote doble buffer (default 50) |
| `BATCH_WINDOW_MS` | Ventana temporal máxima del lote (default 60000ms) |
| `DEBUG` | Activa prints de diagnóstico generales |

---

## Convenciones de código

- Todo el código nuevo va en `src/`.
- Las clases de hardware van en `src/Drivers/` (bajo nivel, solo hardware).
- La lógica de negocio va en `src/Models/` (alto nivel).
- Toda excepción debe capturarse y, si `DEBUG`, imprimirse. Nunca dejar caer el bucle principal por una excepción no capturada.
- Las ISR deben ser mínimas: solo debounce + `micropython.schedule`. Nunca SPI ni I2C dentro de una ISR.
- Los buffers preasignados (`bufA`, `bufB`) son `bytearray` de tamaño fijo para no presionar el GC.
- Al trabajar con tiempo, siempre usar `ticks_ms()` y `ticks_diff()` de `time` (son seguros ante desbordamiento de 32 bits).

---

## Referencia de pines por defecto

| Señal | GPIO | Función |
|---|---|---|
| SPI0 SCK | GP18 | Reloj SPI del CC1101 |
| SPI0 MOSI | GP19 | Datos salida al CC1101 |
| SPI0 MISO | GP16 | Datos entrada del CC1101 |
| SPI0 CS (CSN) | GP17 | Chip select (pull-up 10kΩ a 3.3V) |
| GDO0 | GP20 | Fin de paquete (IRQ falling) |
| GDO2 | GP21 | Estado radio (opcional) |
| LED_READ | GP12 | Indicador de subida a API / heartbeat |
| LED_ALT1 | GP13 | Parpadeo alterno recepción válida |
| LED_ALT2 | GP14 | Parpadeo alterno recepción válida |

---

## Flujo de subida a la API

```
POST {API_URL}/{API_PATH}
Headers:
  Authorization: Bearer {API_TOKEN}
  Content-Type: application/json

Body:
{
  "hardware_device_id": <DEVICE_ID>,
  "data": {
    "temperature": float,
    "humidity": float,
    "wind_speed": float,
    "wind_average_speed": float,
    "wind_min_speed": float,
    "wind_max_speed": float,
    "wind_grades": float,
    "rain": float,
    "rain_intensity": float,
    "rain_month": float
  }
}

Respuesta esperada: HTTP 201
```

---

## Cómo trabajar en este proyecto

1. **Leer** `src/env.py` para entender la configuración activa.
2. **Nunca tocar** `old_c_project/` ni `old_python_project/` — solo leerlos como referencia.
3. **Probar cambios** cargando los archivos modificados de `src/` a la Pico con Thonny, rshell o mpremote.
4. **Diagnóstico**: activar `DEBUG=True` y `DECODE_DEBUG=True` en `env.py` para ver el flujo completo de decodificación.
5. **Descubrir el ID de la estación**: poner `FIND_STATION_IDS=True` y observar la consola hasta identificar el ID propio.
6. **Falsos positivos**: si se decodifican tramas de sensores vecinos, añadir el ID propio a `SENSOR_IDS_INC` y/o poner `FORCE_BRESSER_MODEL` al tipo correcto.

---

## Dependencias externas

Ninguna librería externa de terceros. Solo MicroPython estándar + módulos del firmware RP2 (`urequests`, `ujson`, `network`, `ntptime`, etc., que vienen incluidos en el firmware oficial de MicroPython para Pico W).
