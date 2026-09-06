# Módulo: `Models/Api.py`

Cliente HTTP para la comunicación y envío de telemetría meteorológica a la API REST V2 externa.

## Qué hace y qué NO hace

### Qué hace
- Construye la URL completa sustituyendo `{station}` o `{device_id}` por `self.DEVICE_ID` en `API_PATH`.
- Fija el timeout global de sockets TCP/TLS a 6.0 segundos (`socket.setdefaulttimeout(6.0)`), evitando que handshakes SSL o caídas de enrutador congelen el hilo indefinidamente.
- Alimenta el perro guardián por hardware (`feed_wdt`) del microcontrolador antes de las peticiones y durante los períodos de pausa entre reintentos.
- Reconexión Wi-Fi acotada (`max_retries=2`) ante fallos de conexión para no retener el hilo principal.
- Transforma el diccionario plano de telemetría interna del decodificador al esquema multi-sensor del contrato V2: `POST /weather-stations/{station}/readings`.
- Convierte rumbos en grados (0–360) a los 16 rumbos cardinales estándar ("N", "NNE", "NE", etc.) mediante [`degrees_to_cardinal()`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/Api.py).
- Inyecta `moisture: 0.0` para superar la validación requerida del backend en el bloque `rain`.
- Inyecta opcionalmente `hardware_device_info` en la raíz con:
  - `temp`: Temperatura interna del RP2040 (°C).
  - `ip_local`: Dirección IP local asignada a la interfaz Wi-Fi.
  - `uptime`: Segundos transcurridos desde el arranque del dispositivo.
  - `disk`: Porcentaje de ocupación del almacenamiento Flash interno (LittleFS).
  - `ram`: Porcentaje de ocupación de la memoria RAM (heap) en MicroPython (0–100%).
  - `extra`: Diccionario de metadatos del microcontrolador (`rssi` en dBm, `mac`, `cpu_freq_mhz` y `reset_cause`).
  - *Nota*: `ip_public` no se envía (la extrae y gestiona el backend automáticamente).
- Aplica autenticación Bearer Token en cabeceras HTTP (`Authorization: Bearer <API_TOKEN>`).
- Envía peticiones HTTP mediante `urequests` con hasta 3 reintentos y reconexión automática Wi-Fi ante caídas de socket.
- Consulta el estado de la estación vía `GET /weather-stations/{station}`.

### Qué NO hace
- No gestiona el temporizador de subida ni el encolado de datos (delegado en `main.py`).
- No reintenta peticiones rechazadas con código 4xx (errores de validación de cliente).
- No envía `ip_public` (el contrato V2 la obtiene en el servidor).

## Modelo de datos

### Cuerpo de la petición POST enviada a la API (Contrato V2)
```json
{
  "data": {
    "temperature": [ { "value": 21.4 } ],
    "humidity": [ { "value": 65.0 } ],
    "wind": [ { "speed": 1.2, "average": 1.2, "min": 1.2, "max": 3.5 } ],
    "wind_direction": [ { "direction": "S", "grades": 180.0 } ],
    "rain": [ { "rain": 0.0, "moisture": 0.0, "rain_intensity": 0.0, "rain_month": 12.5 } ]
  },
  "hardware_device_info": {
    "temp": 34.2,
    "ip_local": "192.168.1.145",
    "uptime": 14520,
    "disk": 12.4,
    "ram": 28.5,
    "extra": {
      "rssi": -68,
      "mac": "28:cd:c1:05:22:98",
      "cpu_freq_mhz": 133,
      "reset_cause": 1
    }
  }
}
```

## Flujos principales

### Envío de Mediciones (`send_to_api`)
```
send_to_api(data)
  │
  ├─► Alimenta WDT (_feed_wdt)
  ├─► Transforma data mediante _build_v2_payload(data)
  ├─► Si data no contiene ningún sensor válido, cancela el envío
  ├─► Inyecta telemetría hardware_device_info enriquecida si el controlador está disponible
  ├─► Comprueba enlace Wi-Fi y reconecta de forma acotada si está caído
  ├─► Realiza urequests.post(url, headers, json=payload) [timeout de socket = 6.0s]
  ├─► Evalúa status_code (espera 201 Created o 200 OK)
  ├─► Si falla con OSError (socket caído), reconecta Wi-Fi y reintenta alimentando WDT en las pausas
  ├─► Cierra el socket de respuesta (response.close())
  └─► Retorna True si éxito; False si error
```

## Puntos de entrada

- `Api(controller, url, path, token, device_id, debug=False)`: Constructor del cliente HTTP.
- `send_to_api(data={}) -> bool`: Envía las lecturas consolidadas al endpoint multi-sensor de la API V2.
- `get_data_from_api()`: Petición GET para comprobar la estación en `/weather-stations/{station}`.
- `degrees_to_cardinal(deg)`: Convierte grados (0-360) al rumbo cardinal de 16 sectores.

## Dependencias en ambos sentidos

### Consume de
- `urequests`: Cliente HTTP ligero de MicroPython.
- `ujson`: Serialización y deserialización JSON.
- `usocket` / `socket`: Configuración de timeout global de sockets.
- `Models.RpiPico.RpiPico` (a través del parámetro `controller`): Para consultar telemetría (temperatura CPU, IP, uptime, disco, RAM, RSSI, MAC), alimentar WDT y reconectar Wi-Fi.
- `machine`: Frecuencia del microprocesador (`freq`) y causa de reset (`reset_cause`).
- `gc`: Memoria asignada y libre en heap (`mem_alloc`, `mem_free`).
- `time.sleep_ms`: Pausas entre reintentos.

### Es consumido por
- [`src/main.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/main.py): Para subir las lecturas completas o el timeout de datos parciales.

## Configuración

| Variable | Valor recomendado | Efecto / Comportamiento |
|---|---|---|
| `API_URL` | `"https://api.raupulus.dev/api/v2"` | Dirección base de la API REST V2 |
| `API_PATH` | `"weather-stations/{station}/readings"` | Endpoint multi-sensor para IoT |
| `API_TOKEN` | Token Bearer | Credencial con ability `weatherstation:write` |
| `DEVICE_ID` | `18` | Identificador numérico de la estación en el backend |
| `API_ENABLED` | `True` | Habilita o inhabilita el envío HTTP |

## Trampas conocidas

- **Cierre de socket obligatorio**: En MicroPython, no cerrar `response.close()` en cada llamada de `urequests` provoca agotamiento de sockets (`ENOMEM` / `OSError`), bloqueando el subsistema Wi-Fi.
- **Validación 422 estricta**: En V2, cualquier clave no registrada en el catálogo dentro de `data` provoca `422 Unprocessable Entity`. `_build_v2_payload` solo emite las 5 claves soportadas por la estación física.
- **Requisito de `moisture` en `rain`**: La validación exige `moisture` aunque la estación no tenga dicho sensor; se envía `0.0`.
- **Margen de timeout frente a WDT**: El timeout de socket (6.0s) debe ser estrictamente menor que el timeout del watchdog hardware (8.0s) para garantizar que los fallos de red lancen `OSError` capturable antes del reinicio forzoso del hardware.

## Tests que lo cubren

- `⚠️ sin verificar` (sin suite de tests automatizada en CI).
- Verificación manual: Comprobación contra servidor real con `DEBUG=True`, verificando la recepción de respuesta HTTP 201 y el conteo de registros insertados.

## Pendiente real

- Ninguna acción crítica pendiente.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
