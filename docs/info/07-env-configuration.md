# Configuración — `src/env.py` y `src/.env.example.py`

## Descripción

Todo el comportamiento configurable del firmware se controla desde `src/env.py`. Este archivo no se incluye en el repositorio con datos reales (contiene credenciales). La plantilla vacía es `src/.env.example.py`.

Para desplegar: copiar `.env.example.py` a `env.py` y rellenar los valores.

---

## Sección Wi-Fi

```python
HOSTNAME = "RpiPicoW"          # Nombre del dispositivo en la red
AP_NAME  = "MiRed"             # SSID principal
AP_PASS  = "MiContraseña"      # Contraseña principal

ALTERNATIVES_AP = [
    # {"ssid": "Backup", "password": "pass"},
]
```

`ALTERNATIVES_AP` es una lista de diccionarios con redes de respaldo. El firmware las intenta en orden si la red principal no está disponible. Útil si el dispositivo se usa en varias ubicaciones.

---

## Sección API

```python
API_URL    = "https://api.example.com/api"
API_PATH   = "weatherstation/v1/lightning/add-json"
API_TOKEN  = "token_bearer"
DEVICE_ID  = 18
```

La URL completa de la petición POST será `API_URL + API_PATH`. El `DEVICE_ID` identifica este dispositivo en la API (permite múltiples estaciones en la misma cuenta).

---

## Sección Debug

```python
DEBUG = False   # True en desarrollo, False en producción
```

Con `DEBUG=True` se imprimen mensajes detallados por la consola serie: estado Wi-Fi, temperatura CPU, paquetes recibidos en hex, intentos de decodificación, estado del radio cada 30s, etc.

---

## Sección CC1101

```python
ENABLE_CC1101         = True       # Habilitar/deshabilitar el receptor RF
CC1101_SPI_BUS        = 0          # Bus SPI a usar (0 o 1)
CC1101_SCLK           = 18         # GPIO SCK
CC1101_MOSI           = 19         # GPIO MOSI
CC1101_MISO           = 16         # GPIO MISO
CC1101_CS             = 17         # GPIO CS (+ pull-up 10kΩ a 3.3V)
CC1101_GDO0           = 20         # GPIO GDO0 (fin de paquete, IRQ)
CC1101_GDO2           = 21         # GPIO GDO2 (estado radio, no crítico)
CC1101_BAUDRATE       = 4000000    # Baudrate SPI (4 MHz recomendado)
CC1101_FREQ_HZ        = 868000000  # Frecuencia central (868.0 o 868.3 MHz)
CC1101_PKT_LEN        = 40         # Longitud máxima de paquete
CC1101_BW_DEFAULT     = '270k'     # Ancho de banda RX ('270k' | '250k')
```

### Notas sobre `CC1101_FREQ_HZ`

- `868000000` (868.0 MHz): valor genérico de la banda.
- `868300000` (868.3 MHz): valor exacto usado en el proyecto C original y por rtl_433 para Bresser 6-en-1. Si hay problemas de recepción, probar ambos.

### Notas sobre `CC1101_PKT_LEN`

Con `PKTCTRL0=0x02` (modo longitud variable), este valor es la longitud **máxima** permitida. El CC1101 descarta paquetes cuyo byte de longitud sea mayor que este valor.

- Bresser 6-en-1: 18 bytes de payload.
- Bresser 5-en-1: 26 bytes de payload.
- El valor 40 cubre ambos con margen.

### Sonda automática (en modo búsqueda de IDs)

```python
CC1101_AUTO_SYNC_PROBE    = True    # Alternar modo de sync durante búsqueda
CC1101_SYNC_PROBE_PERIOD_MS = 30000 # Cada 30s alterna la config de sync
CC1101_AUTO_BW_PROBE      = True    # Alternar ancho de banda durante búsqueda
CC1101_BW_PROBE_PERIOD_MS = 30000   # Cada 30s alterna el BW
```

Solo activo cuando `FIND_STATION_IDS=True`. Permite explorar configuraciones para maximizar la probabilidad de capturar la primera trama.

---

## Sección LEDs

```python
ENABLE_ONBOARD_LED  = True   # LED integrado ON al arrancar
LED_READ_PIN        = 12     # GPIO para LED de subida a API (-1 = desactivado)
LED_ALT1_PIN        = 13     # GPIO para parpadeo alterno 1 (-1 = desactivado)
LED_ALT2_PIN        = 14     # GPIO para parpadeo alterno 2 (-1 = desactivado)
LED_HEARTBEAT_MS    = 1000   # Intervalo de parpadeo heartbeat (ms)
LED_ALT_MIN_BLINKS  = 7      # Mínimo de alternaciones por evento
LED_ALT_MAX_BLINKS  = 15     # Máximo de alternaciones por evento
LED_ALT_MIN_DELAY_MS = 80    # Tiempo mínimo entre alternaciones (ms)
LED_ALT_MAX_DELAY_MS = 250   # Tiempo máximo entre alternaciones (ms)
```

---

## Sección Batching (doble buffer)

```python
BATCH_SIZE      = 50      # Máximo de paquetes por lote
BATCH_WINDOW_MS = 60000   # Ventana temporal máxima de un lote (1 minuto)
```

Cuando se acumulan `BATCH_SIZE` paquetes o pasan `BATCH_WINDOW_MS` ms, el lote se cede al hilo de procesado. Valores más pequeños reducen la latencia pero incrementan el overhead de sincronización.

---

## Sección Decodificación y Filtrado

### Modo búsqueda de IDs

```python
FIND_STATION_IDS = False   # True = solo mostrar IDs, sin agregar ni subir
```

En este modo el firmware es un "sniffer" pasivo. Por consola se ven líneas como:

```
ID detectado: 12345678  tipo: 1  chan: 0
ID candidato: 42
```

Una vez identificado el ID propio, ponerlo en `SENSOR_IDS_INC` y desactivar este modo.

### Filtros de ID

```python
SENSOR_IDS_INC = [12345678]   # Solo aceptar este ID (vacío = aceptar todos)
SENSOR_IDS_EXC = [99999999]   # Rechazar este ID (vacío = no rechazar ninguno)
```

Se evalúa primero EXC, luego INC. Si `SENSOR_IDS_INC` tiene elementos, solo esos IDs pasarán.

### Forzar modelo Bresser

```python
FORCE_BRESSER_MODEL = None      # Auto-detectar (None | '5in1' | '6in1')
```

Con `'5in1'` o `'6in1'`, el decodificador solo intenta ese protocolo. Reduce falsos positivos en entornos con mucho ruido RF o sensores vecinos.

### Diagnóstico del decodificador

```python
DECODE_DEBUG = False   # True = imprimir razón de rechazo de cada trama
```

Produce muchas líneas por consola. Usar solo para diagnosticar problemas de decodificación, no en producción.

### Modo estricto de búsqueda de IDs 5-en-1

```python
FIND_ID_STRICT = False   # True = exigir checksum además de paridad al buscar IDs
```

Con `False` (por defecto): acepta cualquier trama que pase la verificación de paridad como candidata a ID. Con `True`: además exige que el checksum de conteo de bits coincida (más restrictivo, menos falsos positivos).

### Decodificación con ventana deslizante

```python
ALLOW_SLIDING_DECODE = False   # True = intentar todas las alineaciones posibles
```

Si `True`, el decodificador prueba todas las ventanas de 18B y 26B dentro del paquete recibido. Útil cuando hay problemas de alineación por configuraciones de sync word diferentes. Por defecto desactivado para evitar falsos positivos con datos de ruido.

### Requisito del byte 0xD4

```python
REQUIRE_D4_FIRST_BYTE = True   # True = el primer byte debe ser 0xD4 (layout 27B)
```

En el modo de sync "AA 2D", el primer byte del payload es `0xD4` (el segundo byte de la palabra de sincronización). Con `True`, se usa ese byte para alinear el mensaje de 26 bytes (layout 27B). Con `False`, se intenta también el layout de 26B sin verificar el primer byte.

---

## Referencia rápida de flags de diagnóstico

| Flag | Producción | Desarrollo | Efecto |
|---|---|---|---|
| `DEBUG` | `False` | `True` | Prints generales del sistema |
| `DECODE_DEBUG` | `False` | `True` | Fallos de decodificación por trama |
| `SHOW_ALL_DECODED` | `False` | `True` | Todas las tramas decodificadas (aunque incompletas) |
| `FIND_STATION_IDS` | `False` | `True` | Solo buscar IDs, no subir datos |
| `ALLOW_SLIDING_DECODE` | `False` | `True` | Alineación flexible (más falsos positivos) |
