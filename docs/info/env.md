# Módulo: `env.py`

Módulo central de configuración y parametrización de entorno del firmware en MicroPython.

## Qué hace y qué NO hace

### Qué hace
- Declara las variables de entorno utilizadas por todos los módulos del proyecto en tiempo de arranque y ejecución.
- Define las credenciales de red inalámbrica Wi-Fi y nombres de host.
- Define los endpoints y credenciales de acceso para la API REST V2 receptora de mediciones.
- Configura el mapeo de pines GPIO para los buses SPI, líneas de interrupción de radio y LEDs de señalización.
- Configura los parámetros de radiofrecuencia (frecuencia portadora 868.3 MHz, filtros de ancho de banda, longitud de paquete CC1101).
- Define flags de control operativo (`DEBUG`, `WIFI_ENABLED`, `API_ENABLED`, `ENABLE_WDT`, `FIND_STATION_IDS`, etc.).
- Gestiona listas blancas y negras de identificadores de estación (`SENSOR_IDS_INC`, `SENSOR_IDS_EXC`).

### Qué NO hace
- No valida la consistencia de tipos en tiempo de carga (las clases consumidoras realizan conversiones defensivas mediante `getattr()` o `int()`).
- No debe subirse con credenciales reales a repositorios públicos (se encuentra en `.gitignore`).

## Modelo de datos

### Resumen de variables declaradas (Contrato API V2)
```python
# Conectividad Wi-Fi
HOSTNAME = "RpiPicoW-Bresser-Scanner"
AP_NAME = "IoT_Developer"
AP_PASS = "..."
ALTERNATIVES_AP = []
WIFI_ENABLED = True

# Resiliencia y Watchdog
ENABLE_WDT = True

# API REST V2
API_URL = "https://api.raupulus.dev/api/v2"
API_PATH = "weather-stations/{station}/readings"
API_TOKEN = "..."
DEVICE_ID = 18
API_ENABLED = True
PARTIAL_UPLOAD_TIMEOUT_MS = 90000

# Radio CC1101
ENABLE_CC1101 = True
CC1101_SPI_BUS = 0
CC1101_SCLK = 18
CC1101_MOSI = 19
CC1101_MISO = 16
CC1101_CS = 17
CC1101_GDO0 = 20
CC1101_GDO2 = 21
CC1101_BAUDRATE = 4000000
CC1101_FREQ_HZ = 868300000
CC1101_PKT_LEN = 40
CC1101_SYNC_PROBE_PERIOD_MS = 30000
CC1101_BW_DEFAULT = '270k'

# LEDs de Señalización
ENABLE_ONBOARD_LED = True
LED_ON_PIN = 15
LED_READ_PIN = 7
LED_ALT1_PIN = 13
LED_ALT2_PIN = 14
LED_HEARTBEAT_MS = 1000
LED_ALT_MIN_BLINKS = 7
LED_ALT_MAX_BLINKS = 15
LED_ALT_MIN_DELAY_MS = 80
LED_ALT_MAX_DELAY_MS = 250

# Pipeline y Decodificación
DEBUG = False
SHOW_ALL_DECODED = False
BATCH_SIZE = 50
BATCH_WINDOW_MS = 60000
FIND_STATION_IDS = False
SENSOR_IDS_INC = [336593555]
SENSOR_IDS_EXC = []
DECODE_DEBUG = False
ALLOW_SLIDING_DECODE = True
```

## Flujos principales

1. `src/main.py` importa directamente `import env`.
2. Las clases consumen las variables directamente (`env.VARIABLE`) o con fallback mediante `getattr(env, 'VARIABLE', default)`.

## Puntos de entrada

- Archivo de constantes y atributos importable como módulo Python ordinario.

## Dependencias en ambos sentidos

### Consume de
- No tiene dependencias externas.

### Es consumido por
- [`src/main.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/main.py)
- [`src/Models/WeatherSensor.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/WeatherSensor.py)
- [`src/Models/Api.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/Api.py)
- [`src/Models/RpiPico.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/RpiPico.py)

## Configuración

Todas las variables del proyecto residen en este archivo. Consultar la tabla en [`docs/info/README.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/README.md) para un desglose exhaustivo de cada opción.

## Trampas conocidas

- **Gitignore activo**: `src/env.py` y `env.py` están en `.gitignore` para proteger contraseñas y tokens.
- **Falta de plantilla versionada**: Resuelto mediante el mantenimiento obligatorio de [`src/.env.example.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/.env.example.py).

## Tests que lo cubren

- Verificado sintácticamente en la ejecución del firmware.

## Pendiente real

- [x] Generar un archivo `src/.env.example.py` con credenciales ofuscadas para permitir una clonación limpia del repositorio.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
