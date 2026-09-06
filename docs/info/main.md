# Módulo: `main.py`

Punto de entrada y orquestador del sistema en MicroPython sobre Raspberry Pi Pico W.

## Qué hace y qué NO hace

### Qué hace
- Inicializa los subsistemas de hardware (Wi-Fi, SPI bus 0, receptor CC1101, RTC vía NTP, temporizador Watchdog WDT y LEDs).
- Ejecuta una arquitectura concurrente de dos núcleos:
  - **Core 0 (hilo principal)**: Bombeo rápido del FIFO del CC1101, volcado en memoria fija en doble buffer (`bufA`/`bufB`), alternancia de lotes por tamaño (`BATCH_SIZE`) o ventana de tiempo (`BATCH_WINDOW_MS`), gestión de peticiones HTTP a la API REST V2, supervisión del Watchdog, monitorización de actividad del Core 1, recolección periódica de basura en heap y servicio no bloqueante de parpadeo de LEDs.
  - **Core 1 (hilo de procesado `processor_thread`)**: Espera lotes listos, decodifica tramas Bresser (6-en-1 / 5-en-1), actualiza el latido de vida (`core1_last_alive_ms`), agrega mediciones climáticas y gestiona timeouts de datos parciales (`PARTIAL_UPLOAD_TIMEOUT_MS`).
- Gestiona eventos hardware mediante interrupción en flanco de bajada de `GDO0` desacoplada con `micropython.schedule(_on_gdo0_scheduled)`.
- Controla los estados de los LEDs visuales (`led_onboard`, `led_on`, `led_read`, `led_alt1`, `led_alt2`).
- Ejecuta recolección de basura periódica (`gc.collect()` cada 30 segundos).
- Resincroniza periódicamente el reloj interno RTC por NTP cada 24 horas.
- Supervisa la salud del hilo secundario en Core 1: si no emite pulso en >120 segundos, fuerza el reinicio por hardware (`machine.reset()`).
- Inicializa y alimenta el Watchdog hardware (`machine.WDT` con 8000 ms) para autorrecuperación total ante bloqueos no controlados.

### Qué NO hace
- No implementa la lógica de decodificación de tramas por radio (delegado en `WeatherSensor.py`).
- No realiza transacciones directas SPI de bajo nivel (delegado en `Drivers/CC1101.py`).
- No construye peticiones HTTP ni reconexiones de red a bajo nivel (delegado en `Models/Api.py` y `Models/RpiPico.py`).
- No emite señales de radio (solo recepción RX).

## Modelo de datos

### Estado de doble buffer
```python
bufA = [bytearray(PKT_LEN_BUF) for _ in range(BATCH_SIZE)]
bufB = [bytearray(PKT_LEN_BUF) for _ in range(BATCH_SIZE)]
lenA = [0 for _ in range(BATCH_SIZE)]
lenB = [0 for _ in range(BATCH_SIZE)]
batch_count = [0, 0]
batch_ready = [False, False]
batch_start_ms = [ticks_ms(), ticks_ms()]
active_buf = 0
write_idx = 0
```

### Agregación de mediciones en Core 1
```python
agg = {
    'first_read': True,
    'temp': 0.0, 'temp_ok': False,
    'humidity': 0.0, 'humidity_ok': False,
    'wind_avg': 0.0, 'wind_gust': 0.0, 'wind_dir': 0.0, 'wind_ok': False,
    'rain_month': 0.0, 'rain': 0.0, 'rain_intensity': 0.0, 'rain_ok': False,
    'last_rain_ts_ms': ticks_ms(),
    'last_sensor_id': None,
    'partial_start_ms': 0,
    'any_data': False
}
```

### Payload saliente hacia la API (Contrato V2)
```python
# Mapeado por Api.py en formato multi-sensor:
# POST /weather-stations/{station}/readings
payload = {
    'temperature': float,
    'humidity': float,
    'wind_speed': float,
    'wind_average_speed': float,
    'wind_min_speed': float,
    'wind_max_speed': float,
    'wind_grades': float,
    'rain': float,
    'rain_intensity': float,
    'rain_month': float
}
```

## Flujos principales

### 1. Secuencia de Arranque
1. Asignación de buffer de emergencia para excepciones en ISR: `micropython.alloc_emergency_exception_buf(100)`.
2. Habilitación de garbage collector (`gc.enable()`).
3. Instanciación de `RpiPico` e inicialización Wi-Fi si `WIFI_ENABLED=True`.
4. Test visual de LEDs (`_startup_blink()`).
5. Inicialización de SPI bus 0 en `RpiPico.set_spi()`.
6. Instanciación e inicialización de `WeatherSensor.begin()`.
7. Instanciación del cliente `Api`.
8. Sincronización horaria RTC por NTP (`rpi.sync_rtc_time()`).
9. Configuración opcional de IRQ en pin `GDO0` (`setup_gdo0_irq()`).
10. Inicialización del Watchdog Timer por hardware (`rpi.init_wdt(timeout_ms=8000)` si `ENABLE_WDT=True`).
11. Lanzamiento del hilo en Core 1 (`_thread.start_new_thread(processor_thread, (None,))`).
12. Entrada al bucle infinito en Core 0.

### 2. Flujo de Recepción y Subida
```
[CC1101 FIFO]
     │
     ▼ (Core 0: ws.receive polling)
[Buffer activo bufA/bufB]
     │ (al llenar BATCH_SIZE o expirar BATCH_WINDOW_MS)
     ▼
[Core 1: processor_thread] (actualiza core1_last_alive_ms)
     │ ws.decode()
     ▼
[Agregador de variables climáticas]
     │ (conjunto completo o timeout PARTIAL_UPLOAD_TIMEOUT_MS)
     ▼
[_set_upload_payload()] ──(lock)──► [_take_upload_payload()] (Core 0)
                                            │
                                            ▼
                                   [api.send_to_api(payload)]
```

## Puntos de entrada

- Archivo de arranque ejecutado automáticamente por MicroPython al reiniciar el RP2040.
- `_on_gdo0_scheduled(_)`: Callback planificado mediante `micropython.schedule` al detectar flanco de bajada en `GDO0`.
- `_gdo0_irq(pin)`: Manejador de interrupción hardware (ISR) con debounce de 50 ms.
- `processor_thread(_)`: Función del hilo secundario ejecutada en Core 1.
- `service_blink()`: Servicio periódico sin bloqueo para el juego de luces alternadas en los LEDs de recepción.
- `service_heartbeat()`: Servicio periódico sin bloqueo para el latido de actividad.

## Dependencias en ambos sentidos

### Consume de
- `machine.Pin`, `machine.reset`: Control de pines GPIO, interrupciones hardware y reinicio forzado.
- `_thread`: Multihilo en los dos cores del RP2040 con `allocate_lock()`.
- `micropython`: Buffer de excepciones y planificación `schedule()`.
- `time` (`sleep_ms`, `ticks_ms`, `ticks_diff`): Temporización segura ante desbordamiento de 30/32 bits.
- `gc`: Gestión manual y recolección periódica del heap (`gc.collect()`).
- `urandom`: Generación de retardos aleatorios para animación de LEDs.
- `env`: Carga de todas las variables de configuración del sistema.
- `Models.RpiPico.RpiPico`: Abstracción de conectividad, WDT, SPI, RTC y sensores internos.
- `Models.WeatherSensor.WeatherSensor`: Capa de radio y decodificación.
- `Models.Api.Api`: Cliente de subida REST V2 con telemetría de hardware.

### Es consumido por
- MicroPython runtime (arranque directo del sistema).

## Configuración

| Variable | Valor por defecto | Efecto / Comportamiento |
|---|---|---|
| `DEBUG` | `False` | Activa logs diagnósticos por consola REPL |
| `WIFI_ENABLED` | `True` | Permite o desactiva la inicialización inalámbrica |
| `API_ENABLED` | `True` | Habilita el envío HTTP de los payloads |
| `ENABLE_WDT` | `True` | Habilita el Watchdog Timer hardware con timeout de 8000 ms |
| `PARTIAL_UPLOAD_TIMEOUT_MS` | `90000` | Tiempo de espera antes de subir mediciones parciales incompletas |
| `BATCH_SIZE` | `50` | Número máximo de paquetes antes de rotar lote hacia Core 1 |
| `BATCH_WINDOW_MS` | `60000` | Tiempo máximo para rotar un lote si tiene paquetes acumulados |
| `FIND_STATION_IDS` | `False` | Modo descubrimiento: imprime IDs detectados y cancela subida a API |
| `SHOW_ALL_DECODED` | `False` | Imprime por consola cada trama decodificada con éxito |
| `ENABLE_ONBOARD_LED` | `True` | Mantiene el LED integrado encendido como testigo de encendido |
| `LED_ON_PIN` | `15` | Pin para LED verde de bucle activo |
| `LED_READ_PIN` | `7` | Pin para LED rojo durante el envío HTTP |
| `LED_ALT1_PIN` | `13` | Pin para LED azul alterno 1 |
| `LED_ALT2_PIN` | `14` | Pin para LED azul alterno 2 |

## Trampas conocidas

- **Concurrencia Core 0 / Core 1**: MicroPython en RP2040 implementa multihilo real mediante el hardware del RP2040. Cualquier variable compartida entre el bucle principal y `processor_thread` debe protegerse con `lock = _thread.allocate_lock()`.
- **SPI en ISR Prohibido**: Intentar comunicarse por SPI dentro de `_gdo0_irq` bloqueará el microcontrolador. Por ello se delega exclusivamente con `micropython.schedule()`.
- **Doble Buffer Preasignado**: Los buffers `bufA` y `bufB` se instancian al arranque como listas de `bytearray` fijos. No crear arrays dentro del bucle de radio para evitar fragmentar el heap de MicroPython.
- **Pausa de radio durante HTTP**: Durante la llamada bloqueante `api.send_to_api()`, el Core 0 no bombea la radio. El CC1101 continuará recibiendo en su FIFO hardware (64 bytes); al regresar del POST se realiza recuperación automática de estado.
- **Ventana de Watchdog (WDT)**: Con WDT activado (8.0s), cualquier operación de red prolongada o bucle interno debe invocar `rpi.feed_wdt()` periódicamente para prevenir reinicios del silicio.

## Tests que lo cubren

- `⚠️ sin verificar` (no existen tests unitarios automatizados para `main.py`).
- Verificación manual: Comprobación de encendido de LEDs de arranque, monitorización por consola REPL con `DEBUG=True`, y confirmación de recepción HTTP en servidor destino.

## Pendiente real

- [ ] Unificar el camino legacy de subida directa que aún reside al final del bucle principal de `main.py` con el pipeline del Core 1 para simplificar el flujo.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
