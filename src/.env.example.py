# Wireless
HOSTNAME = "RpiPicoW"
AP_NAME = ""
AP_PASS = ""

# Habilita la conexión Wi-Fi. Si es False el dispositivo funciona sin red.
WIFI_ENABLED = False

# Puntos de accesos alternativos, para redes de respaldo o si mueves la RPI
ALTERNATIVES_AP = [
    #{"ssid": "", "password": ""},
]

# Datos para la API
API_URL = "http://localhost:8000/api"
API_PATH = "path/to/endpoint"
API_TOKEN = "apitoken"

# Nombre del equipo para identificarlo en la api, id y nombre.
DEVICE_ID = 0

# Habilita la subida de datos a la API. Requiere WIFI_ENABLED=True.
API_ENABLED = False

# Indica si está en modo debug la aplicación
DEBUG = False

# Tiempo máximo (ms) esperando datos de todos los sensores antes de subir parcial.
# Si pasa este tiempo y faltan tipos de sensor, se suben los disponibles con NULL.
PARTIAL_UPLOAD_TIMEOUT_MS = 60000  # 60000 = 1 minuto

# ---------------- CC1101 (868 MHz) ----------------
# Habilita el uso del receptor CC1101
ENABLE_CC1101 = True

# Pines según el esquema indicado en README / issue
# SPI0: SCK=GP18, MOSI=GP19, MISO=GP16
CC1101_SPI_BUS = 0
CC1101_SCLK = 18
CC1101_MOSI = 19
CC1101_MISO = 16
CC1101_CS   = 17
# Pines opcionales de estado GDO0/GDO2
CC1101_GDO0 = 20
CC1101_GDO2 = 21
# Baudrate para SPI del CC1101 (4 MHz es seguro)
CC1101_BAUDRATE = 4000000
# Frecuencia central (Hz) del CC1101 (recomendado 868.000.000 según rtl_433)
CC1101_FREQ_HZ = 868000000
# Longitud máxima de paquete (PKTLEN) cuando el CC1101 está en modo de longitud variable.
# Usa 40 para cubrir con holgura Bresser 5‑en‑1 (26) y 6‑en‑1 (18) sin truncar.
CC1101_PKT_LEN = 40
# Sonda automática de sincronización: alterna entre modos estricto (2D D4) y AA 2D
# durante la búsqueda de IDs para maximizar la probabilidad de detección.
CC1101_AUTO_SYNC_PROBE = True
# Periodo para alternar sincronización durante la búsqueda (ms)
CC1101_SYNC_PROBE_PERIOD_MS = 30000
# Perfil de ancho de banda por defecto ('270k' o '250k' (aprox 232kHz))
CC1101_BW_DEFAULT = '270k'
# Auto-sondeo de ancho de banda durante la búsqueda de IDs
CC1101_AUTO_BW_PROBE = True
# Periodo para alternar BW en búsqueda (ms)
CC1101_BW_PROBE_PERIOD_MS = 30000

# ---------------- LEDS ----------------
# Enciende el LED integrado al iniciar para indicar que hay energía
ENABLE_ONBOARD_LED = True
# Pines GPIO para los LEDs externos (usar -1 para desactivar)
# LED_ON_PIN:   LED verde de bucle principal (encendido mientras espera datos, se apaga al recibirlos)
# LED_READ_PIN: LED rojo de subida a API (encendido durante el POST, se apaga al terminar)
# LED_ALT1_PIN y LED_ALT2_PIN: parpadeo alterno azul cuando se decodifica un paquete válido
LED_ON_PIN   = -1   # LED ON verde (bucle principal activo) (ej: 15)
LED_READ_PIN = -1   # LED rojo (subida a API) (ej: 7)
LED_ALT1_PIN = -1   # Parpadeo alterno azul 1 (evento de recepción válida) (ej: 13)
LED_ALT2_PIN = -1   # Parpadeo alterno azul 2 (evento de recepción válida) (ej: 14)
# Heartbeat: LED que late para indicar que el bucle principal está vivo.
# Usa LED_ON_PIN si está disponible; si no, cae al LED integrado.
LED_HEARTBEAT_MS = 1000  # intervalo de parpadeo en ms
# Configuración de parpadeo alterno
LED_ALT_MIN_BLINKS = 7
LED_ALT_MAX_BLINKS = 15
LED_ALT_MIN_DELAY_MS = 80
LED_ALT_MAX_DELAY_MS = 250

# ---------------- LOG DE TRAMAS DE RADIO ----------------
# Si está a True, muestra por consola todas las tramas decodificadas (aunque
# no formen aún un conjunto completo para la API). Si está a False, sólo se
# mostrarán los mensajes habituales.
SHOW_ALL_DECODED = False

# Parámetros de batching (doble buffer) para el receptor
# Se acumulan hasta BATCH_SIZE paquetes o hasta BATCH_WINDOW_MS antes de ceder
# el lote al hilo de procesado.
BATCH_SIZE = 50
BATCH_WINDOW_MS = 60000  # 1 minuto

# Modo búsqueda de IDs de estaciones: si True, el programa se centrará en
# decodificar y mostrar los IDs detectados, sin agregar ni subir a la API.
FIND_STATION_IDS = False

# Forzar tipo de decodificación (None | '5in1' | '6in1') para filtrar y acelerar
FORCE_BRESSER_MODEL = None

# IDs de sensores a incluir/excluir (vacío = aceptar todos)
SENSOR_IDS_INC = []
SENSOR_IDS_EXC = []

# Diagnóstico detallado del decodificador (evitar en producción por ruido)
DECODE_DEBUG = False

# Modo estricto al buscar IDs en paquetes 5-en-1: si True, además de paridad
# correcta exige que el checksum de conteo de bits coincida. Si False (por
# defecto), aceptará IDs candidatos con solo paridad correcta para facilitar
# el descubrimiento del ID de tu estación.
FIND_ID_STRICT = False

# Política de enmarcado/decodificación
# - REQUIRE_D4_FIRST_BYTE: en modo AA 2D (STRICT_SYNC=False) exige que el primer
#   byte del paquete sea 0xD4 (como en el proyecto C). Si no se cumple, se descarta
#   el paquete (salvo que desactives esta opción).
REQUIRE_D4_FIRST_BYTE = True
# - ALLOW_SLIDING_DECODE: permite el escaneo de ventanas deslizantes de 26 bytes
#   dentro del paquete para intentar decodificar en caso de desalineación. Por
#   defecto está desactivado para evitar falsos positivos.
ALLOW_SLIDING_DECODE = False
