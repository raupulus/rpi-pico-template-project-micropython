# Arquitectura del Bucle Principal — `src/main.py`

## Descripción

`main.py` es el punto de entrada del firmware. Coordina la recepción de RF, el procesado en segundo hilo y la subida de datos a la API. Está diseñado para ejecutarse en **dos cores** del RP2040 con memoria compartida protegida por lock.

## Secuencia de arranque

```
1. Importar módulos y variables de entorno (env.py)
2. Inicializar gc (recolector de basura)
3. Instanciar RpiPico → conectar Wi-Fi → configurar SPI
4. Inicializar LEDs externos (LED_READ, LED_ALT1, LED_ALT2, onboard)
5. Realizar parpadeo de arranque (_startup_blink)
6. Instanciar WeatherSensor → begin(pkt_len) → CC1101 en RX
7. Instanciar Api (cliente HTTP)
8. Sincronizar RTC vía NTP (sync_rtc_time)
9. Configurar IRQ en GDO0 (setup_gdo0_irq)
10. Lanzar hilo de procesado en Core 1 (_thread.start_new_thread)
11. Entrar en el bucle principal (while True)
```

## LEDs

| LED | Pin por defecto | Función |
|---|---|---|
| `led_onboard` | "LED" (integrado) | Encendido permanente = con energía |
| `led_read` | GP12 | Se enciende durante subida a API; heartbeat si no hay otro |
| `led_alt1` | GP13 | Parpadeo alterno al recibir trama válida |
| `led_alt2` | GP14 | Parpadeo alterno al recibir trama válida (opuesto a alt1) |

El **heartbeat** (latido) es un parpadeo periódico a `LED_HEARTBEAT_MS` (1s por defecto) que indica que el bucle principal está vivo. Usa `led_read` si está disponible; si no, el LED integrado.

El **parpadeo alterno** entre `led_alt1` y `led_alt2` se activa al recibir una trama válida. El número de alternaciones y los tiempos se controlan con `LED_ALT_MIN_BLINKS`, `LED_ALT_MAX_BLINKS`, `LED_ALT_MIN_DELAY_MS` y `LED_ALT_MAX_DELAY_MS`. El parpadeo es **no bloqueante**: se gestiona con `schedule_random_blink()` y `service_blink()`.

## Sistema de IRQ (GDO0)

### `_gdo0_irq(pin)` — ISR

Se ejecuta en contexto de interrupción cuando GDO0 baja (fin de paquete). Hace lo mínimo posible:

1. Debounce: ignora si han pasado menos de `MIN_IRQ_INTERVAL_MS` (50ms) desde la última IRQ.
2. Si no hay handler pendiente (`_schedule_pending=False`), deshabilita la IRQ y llama `micropython.schedule(_on_gdo0_scheduled, 0)`.
3. Marca `_schedule_pending=True` para evitar múltiples schedules simultáneos.

**No hace SPI** dentro de la ISR — eso solo ocurre en el handler programado.

### `_on_gdo0_scheduled(_)` — Handler programado

Se ejecuta en el contexto normal del intérprete (no en ISR). Lee hasta 3 paquetes del FIFO:

```python
for _ in range(3):
    pkt = ws.receive(timeout_ms=0)
    if not pkt:
        break
    decoded = ws.decode(pkt)
    if decoded.get('crc_ok'):
        last_valid_decoded = decoded
        last_valid_rx_ms = ticks_ms()
        did_blink = True
```

Al finalizar: activa parpadeo alterno si hubo dato válido, resetea `_schedule_pending=False` y rehabilita la IRQ.

## Doble buffer de paquetes

Para desacoplar la recepción (crítica en tiempo) del procesado (costoso), se usa un sistema de **doble buffer preasignado**:

```
bufA[50]  lenA[50]  → Buffer A
bufB[50]  lenB[50]  → Buffer B
batch_count[2]
batch_ready[2]
active_buf           → 0 o 1 (cuál está siendo llenado)
write_idx            → índice de escritura en el buffer activo
```

### Escritura (Core 0)

En cada iteración del bucle principal, el Core 0 llama hasta 8 veces a `ws.receive(timeout_ms=0)` (polling sin bloqueo). Cada paquete se copia en `bufA[write_idx]` o `bufB[write_idx]` dentro de un `lock` y se incrementa `write_idx`.

### Rotación del buffer

Se llama `_rotate_batch_if_needed(now_ms)` después de cada escritura. El buffer rota si:
- `write_idx >= BATCH_SIZE` (buffer lleno), o
- Han pasado `BATCH_WINDOW_MS` ms desde que empezó a llenarse y tiene al menos un paquete.

Cuando rota: marca el buffer actual como listo (`batch_ready[active_buf] = True`), alterna `active_buf` y resetea `write_idx = 0`.

### Lectura (Core 1)

El hilo de procesado espera con `sleep_ms(5)` hasta que `batch_ready[0]` o `batch_ready[1]` sea `True`. Toma el índice, limpia el flag (con lock) y procesa los paquetes fuera del lock.

## Hilo de procesado (Core 1) — `processor_thread`

El hilo mantiene su propio estado de agregación `agg`:

```python
agg = {
    'temp': 0.0, 'temp_ok': False,
    'humidity': 0.0, 'humidity_ok': False,
    'wind_avg': 0.0, 'wind_gust': 0.0, 'wind_dir': 0.0, 'wind_ok': False,
    'rain_month': 0.0, 'rain': 0.0, 'rain_intensity': 0.0, 'rain_ok': False,
    'first_read': True,
    'last_rain_ts_ms': ...,
    'last_sensor_id': None,
}
```

Para cada paquete del lote:

1. Llama `ws.decode(pkt)`.
2. En **modo FIND_STATION_IDS**: solo imprime IDs y llama `probe_ids_from_packet`.
3. En **modo normal**: si `decoded['ok']`, actualiza los flags de `agg` según qué campos contenga la trama.

### Cálculo de lluvia incremental

El campo `rain_mm` del protocolo es un contador acumulado desde el reset de la estación. El hilo calcula la lluvia incremental:

```python
diff_mm = new_month - agg['rain_month']
rain = diff_mm if diff_mm > 0 else 0.0
rain_intensity = (rain / (dt_s)) * 3600.0  # mm/h
```

La primera lectura solo establece la base (`first_read = True`), no genera lluvia incremental.

### Detección de cambio de sensor

Si el `sensor_id` cambia entre tramas, se reinician todos los flags de `agg` para evitar mezclar datos de sensores distintos.

### Payload completo

Cuando `agg['temp_ok'] and agg['humidity_ok'] and agg['wind_ok'] and agg['rain_ok']`, el hilo llama `_set_upload_payload(payload)` y reinicia los cuatro flags.

## Comunicación entre hilos

| Función | Dirección | Uso |
|---|---|---|
| `_set_upload_payload(p)` | Core 1 → Core 0 | Señala que hay un payload listo para subir |
| `_take_upload_payload()` | Core 0 | Consume el payload si existe |
| `_signal_blink_request(n)` | Core 1 → Core 0 | Solicita n parpadeos alternos |
| `_consume_blink_request()` | Core 0 | Consume una petición de parpadeo |

Todas estas funciones adquieren el `lock` para acceso seguro a las variables globales compartidas.

## Bucle principal (Core 0) — pasos en cada iteración

```
1. Comprobar payload pendiente → si hay, subir a API (led_read ON durante POST)
2. Polling del FIFO CC1101 (hasta 8 paquetes por iteración)
3. Escribir paquetes en buffer activo + rotar si toca
4. service_blink() → avanzar parpadeo alterno no bloqueante
5. Consumir blink_requests del Core 1
6. service_heartbeat() → parpadear LED de vida si toca
7. Comprobación de estado del radio (DEBUG cada 30s)
8. sleep_ms(15) → pausa cooperativa
```

## Subida a la API

Cuando hay payload (ya sea del Core 1 o del estado local del Core 0):

```python
upload_in_progress = True
led_read.value(1)                     # LED ON durante POST
ok = api.send_to_api(payload)
led_read.value(0)                     # LED OFF al terminar
upload_in_progress = False
```

El heartbeat respeta `upload_in_progress` para no parpadear el LED mientras está fijo encendido.

Tras una subida exitosa: se reinician los flags de `ok`, se llama `schedule_random_blink()` como confirmación visual, y se llama `gc.collect()`.

## Diagnóstico de radio (DEBUG)

Cada 30 segundos (si `DEBUG=True`), el bucle principal llama `ws.radio.get_status()` e imprime el diccionario completo con MARCSTATE, RSSI, RXBYTES, configuración de demodulación, etc.

## Función `urandint(a, b)`

Wrapper sobre `urandom.randint` con fallback a `urandom.getrandbits` para garantizar compatibilidad con distintas versiones del módulo `urandom` de MicroPython.
