# WeatherSensor y Decodificador Bresser — `src/Models/WeatherSensor.py`

## Descripción

`WeatherSensor` es la capa de alto nivel que envuelve el driver `CC1101` y proporciona:

1. Inicialización y configuración del radio.
2. Recepción de paquetes crudos.
3. Decodificación de tramas **Bresser 5-en-1** y **6-en-1**.
4. Modo de descubrimiento de IDs (`probe_ids_from_packet`).

## Inicialización

```python
ws = WeatherSensor(spi=spi0, cs=cs_pin, gdo0=20, gdo2=21, debug=True)
ws.begin(pkt_len=40)
```

`begin()` instancia el `CC1101`, hace reset y llama `configure_bresser(pkt_len)`. Devuelve `True` si el radio responde correctamente.

El perfil de ancho de banda y la frecuencia se leen de `env.py` (`CC1101_BW_DEFAULT`, `CC1101_FREQ_HZ`) en el constructor.

## Recepción

```python
pkt = ws.receive(timeout_ms=0)  # No bloqueante
pkt = ws.receive(timeout_ms=200)  # Bloqueante hasta 200ms
```

Delega a `radio.read_packet()`. Si hay error, intenta recuperar el radio con `enter_rx()` y devuelve `None`.

En modo debug imprime la longitud y el hex del paquete recibido.

## Decodificación (`decode`)

### Entrada

Un `bytes` con el contenido crudo del FIFO del CC1101 en modo longitud variable: `[L | payload(L)]`.

### Preprocesado del paquete

El decodificador strip el byte de longitud L si el paquete tiene la forma `[L | payload(L)]` o `[L | payload(L) | status(2)]`:

```python
L = packet[0]
if 1 <= L <= 60:
    if len(packet) == L + 1:
        buf = packet[1:1+L]
    elif len(packet) == L + 3:
        buf = packet[1:1+L]
```

Después de este paso, `packet` contiene solo el payload puro.

### Estrategia de decodificación (en orden de prioridad)

```
1. Fast path 6-en-1:  packet[:18]
2. Layout 27B con D4:  packet[1:27]  (si packet[0]==0xD4 y len>=27)
3. Layout 26B directo: packet[:26]   (si len>=26)
4. Sliding window (solo si ALLOW_SLIDING_DECODE=True):
   - Ventanas de 18B → _decode_6in1
   - Ventanas de 26B → _try_decoders (6in1 luego 5in1)
```

Cada intento devuelve `None` en caso de fallo de verificación, o un diccionario con los datos si tiene éxito.

---

## Protocolo Bresser 6-en-1

### Estructura del mensaje (18 bytes)

```
Byte  0-1:  Checksum digest (LFSR-16, big-endian)
Byte  2-5:  Sensor ID (32 bits big-endian)
Byte  6:    [7:4]=tipo [2:0]=canal
Byte  7-9:  Velocidad de viento (XOR 0xFF, BCD)
Byte 10-11: Dirección del viento (BCD)
Byte 12-14: Contador de lluvia (XOR 0xFF, BCD)
Byte 13:    Batería (bit 1): 1=OK
Byte 15-16: Temperatura (BCD)
Byte 17:    Humedad (BCD)
```

### Verificación del digest (LFSR-16)

```python
def _lfsr_digest16(data, length, gen=0x8810, init=0x5412):
    reg = init  # 0x5412
    for i in range(length):
        cur = data[i]
        for b in range(8):
            fb = ((reg >> 15) & 1) ^ ((cur >> (7 - b)) & 1)
            reg = (reg << 1) & 0xFFFF
            if fb:
                reg ^= gen  # 0x8810
    return reg & 0xFFFF
```

Se aplica sobre `msg[2:17]` (15 bytes). El resultado debe coincidir con `(msg[0]<<8)|msg[1]`.

### Verificación del checksum aditivo

La suma de los bytes `msg[2:18]` (16 bytes) modulo 256 debe ser `0xFF`:

```python
sum(msg[2:18]) & 0xFF == 0xFF
```

### Temperatura

Los nibbles de los bytes 15 y 16 codifican la temperatura en BCD con resolución de 0.1°C:

```
temp_raw = (msg[15] >> 4)*100 + (msg[15] & 0x0F)*10 + (msg[16] >> 4)
temp_c = temp_raw * 0.1
if temp_raw > 600:
    temp_c = (temp_raw - 1000) * 0.1  # Temperatura negativa
```

Los nibbles son válidos solo si cada uno es ≤ 9 (BCD válido).

### Humedad

```
humidity = (msg[17] >> 4) * 10 + (msg[17] & 0x0F)
```

BCD de dos dígitos en byte 17. Válido si ambos nibbles ≤ 9.

### Viento

Los bytes 7, 8 y 9 se invierten antes de interpretar (`^ 0xFF`). Son BCD válidos si el byte invertido ≤ 0x99:

```
m7 = msg[7] ^ 0xFF
m8 = msg[8] ^ 0xFF
m9 = msg[9] ^ 0xFF

gust_raw  = (m7>>4)*100 + (m7&0x0F)*10 + (m8>>4)
wavg_raw  = (m9>>4)*100 + (m9&0x0F)*10 + (m8&0x0F)

wind_gust_ms = gust_raw * 0.1   # m/s
wind_avg_ms  = wavg_raw * 0.1   # m/s
```

Dirección del viento (bytes 10-11):
```
wind_dir_raw = (msg[10]>>4)*100 + (msg[10]&0x0F)*10 + (msg[11]>>4)
wind_dir_deg = float(wind_dir_raw)   # 0..359 grados
```

### Lluvia

Bytes 12, 13 y 14 invertidos (`^ 0xFF`). BCD de 6 dígitos:

```
r12 = msg[12] ^ 0xFF   # Válido si r12 <= 0x65
r13 = msg[13] ^ 0xFF   # Válido si r13 <= 0x99
r14 = msg[14] ^ 0xFF   # Válido si r14 <= 0x99

rain_raw = (r12>>4)*100000 + (r12&0x0F)*10000
         + (r13>>4)*1000   + (r13&0x0F)*100
         + (r14>>4)*10     + (r14&0x0F)

rain_mm = rain_raw * 0.1   # mm acumulados desde el reset
```

---

## Protocolo Bresser 5-en-1

### Estructura del mensaje (26 bytes)

```
Bytes  0-12:  Primera mitad de datos (con paridad)
Byte   13:    Checksum de conteo de bits (número de bits a 1 en bytes 14..25)
Bytes 14-25:  Segunda mitad de datos (inversa de 0..12)
```

La primera mitad y la segunda mitad son inversas: `msg[col] ^ msg[col+13] == 0xFF`.

### Verificación de paridad

```python
for col in range(13):
    if (msg[col] ^ msg[col + 13]) & 0xFF != 0xFF:
        return None  # Fallo de paridad
```

### Verificación de checksum

```python
bits_set = sum(bin(msg[p]).count('1') for p in range(14, 26))
if bits_set != msg[13]:
    return None  # Fallo de checksum
```

### Extracción de campos

Los campos se extraen de la segunda mitad del mensaje (`msg[14:26]`):

```
sensor_id  = msg[14]          # 8 bits (0..255)
type_full  = msg[15] & 0x7F   # Tipo de sensor
startup    = (msg[15] & 0x80) == 0   # True en los primeros ~60 min
```

#### Temperatura (BCD con signo)

```
temp_raw = (msg[20] & 0x0F) + ((msg[20]>>4) & 0x0F)*10 + (msg[21] & 0x0F)*100
if (msg[25] & 0x0F) != 0:
    temp_raw = -temp_raw
temp_c = temp_raw * 0.1
```

Los nibbles son válidos si cada uno ≤ 9.

#### Humedad (BCD)

```
humidity = (msg[22] & 0x0F) + ((msg[22]>>4) & 0x0F) * 10
```

#### Viento

```
wind_dir_deg  = (msg[17] & 0x0F) * 22.5     # 16 sectores de 22.5°
gust_raw      = ((msg[17]>>4 & 0x0F) << 8) | msg[16]
wind_gust_ms  = gust_raw * 0.1

wind_raw      = (msg[18] & 0x0F) + ((msg[18]>>4) & 0x0F)*10 + (msg[19] & 0x0F)*100
wind_avg_ms   = wind_raw * 0.1
```

#### Lluvia (BCD)

```
rain_raw = (msg[23] & 0x0F) + ((msg[23]>>4) & 0x0F)*10
         + (msg[24] & 0x0F)*100 + ((msg[24]>>4) & 0x0F)*1000

rain_mm = rain_raw * 0.1
```

Para pluviómetros profesionales (type_full entre 0x39 y 0x3B), el factor se multiplica por 2.5 y `wind_ok` y `humidity_ok` se fuerzan a False.

#### Batería

```
battery_ok = False if (msg[25] & 0x80) else True
```

---

## Filtrado de sensores

Tras una decodificación exitosa, se aplican los filtros de `env.py`:

```python
_SENSOR_INC = set(env.SENSOR_IDS_INC)   # IDs a aceptar (vacío = todos)
_SENSOR_EXC = set(env.SENSOR_IDS_EXC)   # IDs a rechazar

if sid in _SENSOR_EXC → filtered_out=True, ok=False
if _SENSOR_INC y sid not in _SENSOR_INC → filtered_out=True, ok=False
```

---

## Modo descubrimiento de IDs (`probe_ids_from_packet`)

Escanea el paquete crudo buscando IDs sin requerir una decodificación completa:

**Para 6-en-1**: Ventanas de 18 bytes. Si el digest LFSR y el checksum aditivo son correctos, extrae `sensor_id` de bytes 2..5.

**Para 5-en-1**: Ventanas de 26 bytes. Si la paridad de los 13 pares es correcta (y opcionalmente el checksum de bits si `FIND_ID_STRICT=True`), extrae `sensor_id` de byte 14.

Devuelve una lista de enteros con todos los IDs candidatos encontrados.

---

## Estructura del resultado de `decode()`

```python
{
    "ok": bool,              # True si al menos un campo decodificó correctamente
    "payload_hex": str,      # Hex del paquete crudo para diagnóstico
    "sensor_id": int | None,
    "type": int | None,      # Tipo de sensor del protocolo
    "chan": int | None,       # Canal (0 para 5-en-1)
    "battery_ok": bool | None,

    "temp_ok": bool,
    "temp_c": float | None,

    "humidity_ok": bool,
    "humidity": float | None,

    "wind_ok": bool,
    "wind_gust_ms": float | None,
    "wind_avg_ms": float | None,
    "wind_dir_deg": float | None,

    "rain_ok": bool,
    "rain_mm": float | None,   # mm acumulados desde el reset del contador

    # Solo en 5-en-1:
    "startup": bool,
    "complete": bool,

    # Solo si filtrado:
    "filtered_out": bool,

    # Solo en modo debug con sliding window:
    "align_offset": int,
    "align_len": int,
}
```

Un resultado con `ok=True` pero `filtered_out=True` indica que se decodificó correctamente pero fue descartado por filtro de ID.
