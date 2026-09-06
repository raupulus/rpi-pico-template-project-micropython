# Módulo: `Models/WeatherSensor.py`

Capa de dominio encargada de la coordinación de la radio y la decodificación matemática de las tramas meteorológicas emitidas por estaciones Bresser en 868 MHz.

## Qué hace y qué NO hace

### Qué hace
- Envuelve y administra el driver de hardware [`Drivers/CC1101.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Drivers/CC1101.py).
- Inicializa el transceptor y permite la reconfiguración en caliente del ancho de banda y del modo de sincronismo.
- Implementa el decodificador para el protocolo **Bresser 6-en-1** (tramas de 18 bytes):
  - Validación de integridad mediante LFSR-16 con polinomio `0x8810` e inicialización `0x5412`.
  - Validación de suma con acarreo en módulo 256 (`_add_bytes_with_carry == 0xFF`).
  - Extracción de ID de sensor (32 bits), tipo de sensor, canal, temperatura (BCD con soporte negativo para `raw > 600`), humedad relativa, ráfaga y promedio de viento, dirección cardinal y precipitación acumulada con escala de 0.1 mm.
- Implementa el decodificador para el protocolo **Bresser 5-en-1** (tramas de 26 bytes):
  - Validación por paridad invertida entre mitades: `msg[i] ^ msg[i+13] == 0xFF` para `i` de 0 a 12.
  - Validación de checksum mediante conteo de bits `1` en los bytes 14 a 25 igualado a `msg[13]`.
  - Extracción de ID de estación (8 bits), flags de inicio, temperatura con signo en nibble bajo, humedad, ráfaga y media de viento en m/s, dirección (pasos de 22.5°) y lluvia con factor multiplicador 2.5 para pluviómetros de alta resolución.
- Incorpora escaneo por ventana deslizante (sliding window) para rescatar paquetes desalineados o desplazados por ruido.
- Extrae IDs candidatos de paquetes corruptos (`probe_ids_from_packet`) para facilitar el descubrimiento de nuevas estaciones.
- Aplica filtros de lista blanca (`SENSOR_IDS_INC`) y lista negra (`SENSOR_IDS_EXC`).

### Qué NO hace
- No agrega mediciones a lo largo del tiempo ni calcula medias/máximos (delegado en `main.py`).
- No sube datos a la API REST (delegado en `Api.py`).
- No gestiona el parpadeo de LEDs ni hilos del sistema.

## Modelo de datos

### Diccionario de salida de `decode(packet) -> dict`
```python
{
    'ok': bool,                    # True si la trama pasó todas las validaciones
    'crc_ok': bool,                # True si el checksum/LFSR es matemáticamente exacto
    'sensor_id': int,              # ID numérico de la estación
    'type': int,                   # Tipo de sensor Bresser
    'chan': int,                   # Canal asignado (0-7)
    'battery_ok': bool,            # Estado de batería de la estación remota
    'temp_ok': bool,               # Flag de temperatura válida
    'temp_c': float,               # Temperatura en grados Celsius
    'humidity_ok': bool,           # Flag de humedad válida
    'humidity': float,             # Humedad relativa en porcentaje (0-100)
    'wind_ok': bool,               # Flag de anemómetro válido
    'wind_gust_ms': float,         # Ráfaga máxima de viento en m/s
    'wind_avg_ms': float,          # Velocidad media de viento en m/s
    'wind_dir_deg': float,         # Dirección del viento en grados (0.0 a 359.9)
    'rain_ok': bool,               # Flag de pluviómetro válido
    'rain_mm': float               # Acumulado total de lluvia en milímetros
}
```

## Flujos principales

### Decodificación de Trama
```
packet recibido (bytes)
  │
  ├─► Stripping de byte de longitud si está presente
  │
  ├─► Intento de decodificación directa:
  │     ├─ Si len >= 18 y FORCE_BRESSER_MODEL != '5in1' ──► _decode_6in1(msg[:18])
  │     ├─ Si len == 27 y packet[0] == 0xD4 ───────────────► _decode_5in1(packet[1:27])
  │     └─ Si len >= 26 ───────────────────────────────────► _decode_5in1(packet[:26])
  │
  └─► Si no hubo éxito y ALLOW_SLIDING_DECODE == True:
        ├─ Ventana deslizante de 18 bytes a lo largo del paquete ──► _decode_6in1
        └─ Ventana deslizante de 26 bytes a lo largo del paquete ──► _decode_5in1
```

## Puntos de entrada

- `WeatherSensor(spi, cs, gdo0=None, gdo2=None, debug=False)`: Constructor e instanciación del driver `CC1101`.
- `begin(pkt_len=27) -> bool`: Inicialización completa del transceptor.
- `receive(timeout_ms=200) -> Optional[bytes]`: Extracción de un paquete desde el buffer de la radio.
- `reconfigure_sync(strict_sync: bool) -> bool`: Reconfiguración del filtro de sincronismo.
- `reconfigure_bw(profile: str) -> bool`: Cambio dinámico de ancho de banda.
- `decode(packet: bytes) -> dict`: Función principal de decodificación multiprotocolo.
- `probe_ids_from_packet(packet: bytes) -> list[int]`: Extracción heurística de identificadores de estación para modo descubrimiento.

## Dependencias en ambos sentidos

### Consume de
- [`Drivers/CC1101.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Drivers/CC1101.py): Driver de hardware.
- `env`: Flags operacionales (`ALLOW_SLIDING_DECODE`, `FORCE_BRESSER_MODEL`, `SENSOR_IDS_INC`, `SENSOR_IDS_EXC`, `DECODE_DEBUG`, `FIND_ID_STRICT`).

### Es consumido por
- [`src/main.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/main.py): Instanciado en el arranque; llamado en el bucle del Core 0 y en el procesador del Core 1.

## Configuración

| Variable | Valor por defecto | Efecto / Comportamiento |
|---|---|---|
| `FORCE_BRESSER_MODEL` | `None` | Si se fija en `'5in1'` o `'6in1'`, desactiva la prueba del otro protocolo |
| `ALLOW_SLIDING_DECODE` | `True` | Habilita búsqueda en subventanas para mitigar desalineaciones por bits espurios |
| `SENSOR_IDS_INC` | `[336593555]` | Filtro positivo: descarta tramas con IDs diferentes |
| `SENSOR_IDS_EXC` | `[]` | Filtro negativo: descarta tramas de IDs listados |
| `DECODE_DEBUG` | `False` | Imprime trazas de rechazo de paridad, digest o BCD inválido |
| `FIND_ID_STRICT` | `False` | Exige checksum además de paridad al buscar IDs candidatos de 5-en-1 |

## Trampas conocidas

- **Ventana Deslizante vs Falsos Positivos**: `ALLOW_SLIDING_DECODE=True` aumenta la tasa de captura ante pérdidas de sincronismo inicial, pero en entornos electromagnéticamente ruidosos puede generar falsas coincidencias aleatorias. Se recomienda acotar con `SENSOR_IDS_INC`.
- **Temperatura Negativa en 6-en-1**: Si el valor BCD deserializado supera 600, la estación Bresser codifica temperaturas bajo cero usando la fórmula `(raw - 1000) * 0.1`.
- **Pluviómetro de alta resolución en 5-en-1**: Si el campo `type` está en el rango `0x39` a `0x3B`, los pulsos mecánicos del balancín equivalen a 0.25 mm (factor 2.5 respecto a la base BCD).

## Tests que lo cubren

- `⚠️ sin verificar` (no hay tests unitarios con fixtures de tramas sintéticas o capturas reales).
- Verificación manual: Comprobación con emisiones de la estación física Bresser activa emitiendo en 868.3 MHz.

## Pendiente real

- [ ] Crear una suite de pruebas unitarias (`test_weather_sensor.py`) con una colección de tramas hexadecimales reales de 5-en-1 y 6-en-1 para verificar regresiones sin requerir hardware físico.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
