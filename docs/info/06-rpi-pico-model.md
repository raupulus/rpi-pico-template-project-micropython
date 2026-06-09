# Modelo RpiPico — `src/Models/RpiPico.py`

## Descripción

Abstracción de alto nivel del hardware de la **Raspberry Pi Pico W**. Centraliza la inicialización y gestión de:

- Conectividad Wi-Fi (con redes alternativas)
- Buses SPI e I2C
- Sensor de temperatura interno del RP2040
- LED integrado
- RTC y sincronización NTP
- Batería externa (divisor de tensión ADC)
- Callbacks sobre pines GPIO (IRQ)
- Modo deepsleep

## Constructor

```python
rpi = RpiPico(
    ssid="MiRed",
    password="MiClave",
    debug=True,
    country="ES",
    alternatives_ap=[{"ssid": "Backup", "password": "pass"}],
    hostname="RpiPicoW"
)
```

En el constructor:
1. Inicializa el sensor de temperatura interno (`ADC(4)`).
2. Configura el LED integrado (`Pin("LED", Pin.OUT)`).
3. Si se proporcionan `ssid` y `password`, llama `wifi_connect()`.
4. Llama `cpu_temperature_reset_stats()` para inicializar estadísticas de temperatura.

## Wi-Fi

### Conexión con failover

`wifi_connect()` escanea las redes disponibles en cada intento:
- Si la red principal (`SSID`) está disponible → conecta a ella.
- Si no, itera `alternatives_ap` y conecta a la primera disponible.
- Repite hasta conectar (bucle bloqueante con `sleep_ms(1000)` entre intentos).

Desactiva el ahorro de energía del Wi-Fi con `config(pm=0xa11140)` para evitar pérdida de paquetes en recepción continua.

### Constantes de estado

| Constante | Valor | Significado |
|---|---|---|
| `WIFI_DISCONNECTED` | 0 | Sin conexión |
| `WIFI_CONNECTING` | 1 | Conectando |
| `WIFI_CONNECTED` | 3 | Conectado |

### Métodos útiles

| Método | Descripción |
|---|---|
| `wifi_is_connected()` | `True` si `status() == 3` y `isconnected()` |
| `wifi_status()` | Código de estado de la WLAN |
| `get_wireless_ip()` | IP asignada |
| `get_wireless_mac()` | MAC en formato `aa:bb:cc:dd:ee:ff` |
| `get_wireless_rssi()` | RSSI del router en dBm |
| `get_wireless_hostname()` | Hostname configurado |
| `wifi_debug()` | Imprime toda la info de red (solo en DEBUG) |
| `wifi_disconnect()` | Desconecta el Wi-Fi |

## Sensor de temperatura de CPU

El RP2040 tiene un sensor de temperatura en el canal ADC4 (pin interno, no GPIO).

### Lectura y conversión

```python
reading = (ADC(4).read_u16() * adc_conversion_factor) - adc_voltage_correction
temp_c = INTEGRATED_TEMP_CORRECTION - reading / 0.001721
```

Constantes de corrección:
- `INTEGRATED_TEMP_CORRECTION = 27` (corrección de offset)
- `adc_voltage_correction = 0.706`
- `voltage_working = 3.3`
- `adc_conversion_factor = 3.3 / 65535`

### Estadísticas de temperatura

`cpu_temp_stats` mantiene un historial de lecturas:

```python
{
    "max": float,
    "min": float,
    "avg": float,
    "current": float,
    "num_of_measurements": int,
    "sum_of_temps": float,
}
```

`get_cpu_temperature_stats()` devuelve este diccionario. Es útil para detectar sobrecalentamiento en deployments prolongados.

El método `cpu_temperature_read_sensor()` respeta el flag `locked` para evitar lecturas simultáneas con operaciones críticas.

## SPI

### Inicialización

```python
spi = rpi.set_spi(
    pin_sck=18, pin_mosi=19, pin_miso=16, pin_cs=17,
    bus=0, baudrate=4000000
)
```

Crea una instancia `SPI` y un `Pin` para CS. Los almacena internamente como `spi0`/`spi0_cs` o `spi1`/`spi1_cs`.

### Recuperar CS

```python
cs = rpi.get_spi_cs(bus=0)  # Devuelve el Pin configurado como CS
```

Necesario para pasarlo al constructor de `WeatherSensor`.

Solo se admiten buses 0 y 1 (hardware SPI del RP2040). Bus > 1 devuelve `None`.

## I2C

```python
i2c = rpi.set_i2c(pin_sda=20, pin_scl=21, bus=0, frequency=400000)
```

No usado actualmente en el proyecto, pero disponible para sensores I2C adicionales. Admite buses 0 y 1.

## RTC y sincronización horaria

### `sync_rtc_time()`

Sincroniza el RTC interno del Pico con un servidor NTP usando `ntptime.settime()`. Solo funciona si el Wi-Fi está conectado. Marca `is_rtc_set = True` en caso de éxito.

### `get_rtc_utc_time()`

Devuelve `(year, month, day, hour, minute, second)` en UTC desde el RTC.

### `get_rtc_local_time()`

Convierte la hora UTC a hora local de **España (Europa/Madrid)**, incluyendo ajuste de horario de verano (DST). Detecta automáticamente si es CET (UTC+1) o CEST (UTC+2) usando el último domingo de marzo/octubre.

### `get_rtc_local_time_string()`

Devuelve la hora local en formato `"YYYY-MM-DD HH:MM:SS"`.

## Batería externa

Para medir una batería externa con un divisor de tensión (máximo 3.3V en el pin ADC):

```python
rpi.set_external_battery(pin=28, threshold_voltage_min=2.5, threshold_voltage_max=4.2)
data = rpi.read_external_battery()
```

Devuelve un diccionario con voltaje actual, mínimo, máximo y porcentaje de carga. Usar divisor de tensión resistivo para baterías > 3.3V.

## Callbacks GPIO

```python
rpi.set_callback_to_pin(pin_number=2, callback=mi_funcion, event="LOW")
```

Configura una IRQ en el pin con pull-up. `event` puede ser `"HIGH"` (IRQ_RISING) o `"LOW"` (IRQ_FALLING). Lanza `ValueError` si ya hay un callback en ese pin.

`disable_all_callbacks()` deshabilita todas las IRQ configuradas y limpia la lista.

En este proyecto **no se usa** `set_callback_to_pin` para GDO0 — la IRQ de GDO0 se configura directamente en `main.py` con más control sobre debounce y `micropython.schedule`.

## Deepsleep

```python
rpi.deepsleep(seconds=60)  # Duerme 60 segundos
```

Desconecta el Wi-Fi primero para evitar problemas de hardware, luego llama `machine.deepsleep(ms)`. El RP2040 se reiniciará desde `main.py` al despertar.

No se usa en el modo de funcionamiento continuo actual, pero está disponible para modos de bajo consumo.

## Flag `locked`

Varias operaciones costosas (Wi-Fi, temperatura) usan un flag `locked` como mutex simple para evitar re-entradas. Es un mecanismo básico — en código multi-hilo real debe combinarse con `_thread.allocate_lock()`.
