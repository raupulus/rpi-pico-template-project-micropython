# Módulo: `Models/RpiPico.py`

Capa de abstracción de hardware para la Raspberry Pi Pico W (microcontrolador RP2040 con módem Wi-Fi CYW43439).

## Qué hace y qué NO hace

### Qué hace
- Administra el ciclo de vida de la conexión Wi-Fi (interfaz `network.WLAN` en modo `STA_IF`):
  - Soporta red principal (`ssid`, `password`) y lista de redes alternativas de respaldo (`alternatives_ap`).
  - Provee reconexión automática y diagnóstico de enlace (RSSI, canal, IP, MAC, potencia TX).
- Inicializa y gestiona buses serie del RP2040:
  - SPI (`machine.SPI` buses 0 o 1) con control independiente de pines SCK, MOSI, MISO y CS.
  - I2C (`machine.I2C` buses 0 o 1) con escaneo de dispositivos en el bus (`scanI2C`).
- Monitoriza la temperatura interna del silicio RP2040 mediante el canal ADC 4 interno, manteniendo estadísticas móviles (mínima, máxima y promedio).
- Lee tensiones analógicas externas y calcula el porcentaje de carga de baterías externas mediante divisor de tensión con umbrales configurables (`threshold_voltage_min`, `threshold_voltage_max`).
- Sincroniza la hora del reloj interno RTC mediante protocolo NTP (`ntptime.settime()`).
- Calcula el horario de verano / invierno (DST) para la zona horaria de España peninsular (`Europe/Madrid`, UTC+1 en invierno, UTC+2 en verano) determinando el último domingo de marzo y octubre.
- Permite la asignación de callbacks por interrupción a pines GPIO (`set_callback_to_pin`).

### Qué NO hace
- No contiene lógica del protocolo de radio Bresser ni maneja el CC1101 directamente.
- No almacena los datos climáticos en memoria persistente.
- No gestiona el formato específico de telemetría de la API REST.

## Modelo de datos

### Estadísticas de Temperatura CPU
```python
{
    'current': float,
    'min': float,
    'max': float,
    'avg': float,
    'reads': int
}
```

### Información Inalámbrica (`wireless_info`)
```python
{
    'connected': bool,
    'status': int,
    'ssid': str,
    'ip': str,
    'netmask': str,
    'gateway': str,
    'dns': str,
    'mac': str,
    'rssi': int,
    'channel': int,
    'txpower': int
}
```

## Flujos principales

### Conexión Wi-Fi con Respaldo
```
wifi_connect()
  │
  ├─► Intenta conectar a AP principal (ssid/password)
  │     └─ Si conecta en < timeout ──► Retorna True
  │
  └─► Si falla y existen alternatives_ap:
        └─ Itera por cada red alternativa:
             └─ Intenta conexión ──► Si conecta, retorna True
```

### Sincronización Horaria y Cálculo Local
```
sync_rtc_time() -> ntptime.settime() (UTC)
  │
  ▼
get_rtc_local_time()
  │
  ├─► Lee fecha/hora UTC desde machine.RTC()
  ├─► Evalúa is_dst_europe_madrid(year, month, day)
  └─► Suma +2 horas (verano) o +1 hora (invierno)
```

## Puntos de entrada

- `RpiPico(ssid=None, password=None, debug=False, country="ES", alternatives_ap=[], hostname="RpiPicoW")`: Constructor y configuración inicial.
- `wifi_connect(ssid=None, password=None) -> bool`: Establece conexión Wi-Fi con fallback.
- `wifi_disconnect() -> None`: Apaga la interfaz Wi-Fi.
- `wifi_is_connected() -> bool`: Comprueba el estado del enlace de red.
- `wireless_info() -> dict`: Retorna estado completo y parámetros de la red.
- `set_spi(pin_sck, pin_mosi, pin_miso, pin_cs, bus=0, baudrate=10000000) -> SPI`: Inicializa y devuelve un bus SPI hardware.
- `get_spi_cs(bus=0) -> Pin`: Obtiene el pin de CS asociado al bus SPI.
- `set_i2c(pin_sda, pin_scl, bus=0, frequency=400000) -> I2C`: Inicializa un bus I2C.
- `get_cpu_temperature() -> float`: Retorna la temperatura actual del chip RP2040.
- `get_cpu_temperature_stats() -> dict`: Retorna estadísticas acumuladas de temperatura.
- `read_analog_input(pin) -> float`: Mide la tensión analógica (0 a 3.3V) en un pin ADC.
- `set_external_battery(pin, threshold_voltage_min=2.5, threshold_voltage_max=4.2)`: Configura el monitor de batería.
- `read_external_battery() -> dict`: Retorna el voltaje y porcentaje estimado de la batería externa.
- `sync_rtc_time() -> bool`: Sincroniza la hora del sistema por NTP.
- `get_rtc_local_time() -> tuple`: Fecha y hora en formato tupla aplicando DST Europe/Madrid.
- `get_rtc_local_time_string() -> str`: Fecha y hora en formato string ISO-8601 legible.
- `set_callback_to_pin(pin_number, callback, event="HIGH")`: Registra interrupción en pin GPIO.

## Dependencias en ambos sentidos

### Consume de
- `network`: Módem inalámbrico CYW43439 de la Pico W.
- `machine` (`Pin`, `ADC`, `SPI`, `I2C`, `RTC`, `deepsleep`): Periféricos de bajo nivel del silicio.
- `ntptime`: Protocolo Simple NTP sobre UDP.
- `utime` / `time`: Temporizaciones y operaciones de calendario.

### Es consumido por
- [`src/main.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/main.py): Orquesta la inicialización del sistema y el bus SPI.
- [`src/Models/Api.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/Api.py): Para reconectar la red si una llamada HTTP falla.

## Configuración

| Variable | Valor por defecto | Efecto / Comportamiento |
|---|---|---|
| `AP_NAME` | `"IoT_Developer"` | SSID de la red Wi-Fi preferida |
| `AP_PASS` | Secreto | Clave WPA2/WPA3 de la red |
| `ALTERNATIVES_AP` | `[]` | Lista de redes alternativas `[{'ssid': ..., 'password': ...}]` |
| `HOSTNAME` | `"RpiPicoW-Bresser-Scanner"` | Nombre asignado por DHCP en la red local |
| `WIFI_ENABLED` | `True` | Habilita o cancela el encendido del módem inalámbrico |

## Trampas conocidas

- **Incompatibilidad de `time.gmtime()` con DST en MicroPython**: MicroPython no implementa zonas horarias ni base de datos de husos horarios (`tzdata`). El cálculo de DST europeo en `is_dst_europe_madrid` asume el algoritmo del último domingo del mes a las 02:00 / 03:00 am.
- **Divisor de tensión en ADC**: La entrada analógica del RP2040 soporta como máximo 3.3V. Si se conecta una celda de litio (hasta 4.2V), es indispensable un divisor de tensión exterior con resistencias calculadas para no destruir el pin ADC.
- **`country="ES"` en CYW43439**: Configurar el código de país correcto en la inicialización Wi-Fi es crítico para permitir la sintonización de los canales 12 y 13 regulados en Europa.

## Tests que lo cubren

- `⚠️ sin verificar` (no cuenta con tests unitarios simulados).
- Verificación manual: Comprobación de asignación IP por DHCP, sincronización con servidor NTP en pool.ntp.org y lectura válida del ADC 4 interno (~25°C - 35°C).

## Pendiente real

- [ ] Añadir reintento con backoff exponencial en `ntptime.settime()` si la consulta UDP inicial se pierde por latencia de la red.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
