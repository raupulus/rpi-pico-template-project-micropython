# Wireless
HOSTNAME = "RpiPicoW-Bresser-Scanner"
AP_NAME = "TU_SSID_WIFI"
AP_PASS = "TU_PASSWORD_WIFI"

ALTERNATIVES_AP = [
    # {"ssid": "RED_RESPALDO", "password": "PASSWORD_RESPALDO"},
]

# Datos para la API (Contrato API V2)
API_URL = "https://api.example.es/api/v2"
API_PATH = "weather-stations/{station}/readings"
API_TOKEN = "TU_API_BEARER_TOKEN"

# Identificador del dispositivo en la API (ID numérico de la estación)
DEVICE_ID = 1

# Indica si está en modo debug la aplicación
DEBUG = False

# Habilita la conexión Wi-Fi. Si es False el dispositivo funciona sin red.
WIFI_ENABLED = True

# Habilita la subida de datos a la API. Requiere WIFI_ENABLED=True.
API_ENABLED = True

# Tiempo máximo (ms) esperando datos de todos los sensores antes de subir parcial.
PARTIAL_UPLOAD_TIMEOUT_MS = 90000  # 90 segundos

# ---------------- RESILIENCIA Y WATCHDOG ----------------
# Habilita el temporizador de reinicio automático por hardware ante bloqueos (WDT)
ENABLE_WDT = True

# ---------------- CC1101 (868 MHz) ----------------
# Habilita el uso del receptor CC1101
ENABLE_CC1101 = True

# Pines según el esquema indicado en docs/info/COMPONENTS.md
CC1101_SPI_BUS = 0
CC1101_SCLK = 18
CC1101_MOSI = 19
CC1101_MISO = 16
CC1101_CS   = 17
CC1101_GDO0 = 20
CC1101_GDO2 = 21
CC1101_BAUDRATE = 4000000
CC1101_FREQ_HZ = 868300000
CC1101_PKT_LEN = 40
CC1101_SYNC_PROBE_PERIOD_MS = 30000
CC1101_BW_DEFAULT = '270k'

# ---------------- LEDS ----------------
ENABLE_ONBOARD_LED = True
LED_ON_PIN   = 15   # LED ON verde (bucle principal activo)
LED_READ_PIN = 7    # LED rojo (subida a API)
LED_ALT1_PIN = 13   # Parpadeo alterno azul 1
LED_ALT2_PIN = 14   # Parpadeo alterno azul 2
LED_HEARTBEAT_MS = 1000
LED_ALT_MIN_BLINKS = 7
LED_ALT_MAX_BLINKS = 15
LED_ALT_MIN_DELAY_MS = 80
LED_ALT_MAX_DELAY_MS = 250

# ---------------- LOG DE TRAMAS DE RADIO ----------------
SHOW_ALL_DECODED = False
BATCH_SIZE = 50
BATCH_WINDOW_MS = 60000  # 1 minuto
FIND_STATION_IDS = False

# IDs de sensores a incluir/excluir (vacío = aceptar todos)
SENSOR_IDS_INC = []
SENSOR_IDS_EXC = []

# Diagnóstico detallado del decodificador
DECODE_DEBUG = False
ALLOW_SLIDING_DECODE = True
