# Módulo: `Models/Api.py`

Cliente HTTP para la comunicación y envío de telemetría meteorológica a la API REST externa.

## Qué hace y qué NO hace

### Qué hace
- Construye la URL completa concatenando `url` y `path` normalizando barras intermedias.
- Envía paquetes de telemetría JSON mediante peticiones HTTP `POST` usando la librería `urequests` de MicroPython.
- Aplica autenticación Bearer Token en cabeceras HTTP (`Authorization: Bearer <API_TOKEN>`).
- Provee un mecanismo automático de reconexión Wi-Fi llamando al controlador (`controller._reconnect_wifi()`) si la petición falla por caída de enlace o socket roto.
- Sincroniza la hora del RTC (`get_data_from_api()`) consultando la cabecera `Date` de una respuesta HTTP como fallback si NTP no está disponible.
- Mantiene el payload compatible tanto con la raíz de variables individuales como con el subobjeto agrupador `data`.

### Qué NO hace
- No gestiona el temporizador de subida ni el encolado de datos (delegado en `main.py`).
- No parsea errores de validación de negocio devueltos por el servidor más allá de verificar el código de estado HTTP 201/200.

## Modelo de datos

### Cuerpo de la petición POST enviada a la API
```json
{
  "hardware_device_id": 18,
  "temperature": 21.4,
  "humidity": 65.0,
  "wind_speed": 1.2,
  "wind_average_speed": 1.2,
  "wind_min_speed": 1.2,
  "wind_max_speed": 3.5,
  "wind_grades": 180.0,
  "rain": 0.0,
  "rain_intensity": 0.0,
  "rain_month": 12.5,
  "data": {
    "temperature": 21.4,
    "humidity": 65.0,
    "wind_speed": 1.2,
    "wind_average_speed": 1.2,
    "wind_min_speed": 1.2,
    "wind_max_speed": 3.5,
    "wind_grades": 180.0,
    "rain": 0.0,
    "rain_intensity": 0.0,
    "rain_month": 12.5
  }
}
```

*Nota*: Si una métrica no está disponible en un envío parcial (timeout), el campo a nivel raíz se omite y en `data` se reporta con valor `null`.

## Flujos principales

### Envío de Mediciones (`send_to_api`)
```
send_to_api(data)
  │
  ├─► Valida conexión Wi-Fi (si caída, ejecuta _reconnect_wifi)
  ├─► Empaqueta campos en diccionario y serializa a JSON
  ├─► Realiza urequests.post(endpoint, headers, data=json_str)
  ├─► Evalúa status_code (espera 201 Created o 200 OK)
  ├─► Cierra el socket de respuesta (response.close())
  └─► Retorna True si éxito; False si error
```

## Puntos de entrada

- `Api(controller, url, path, token, device_id, debug=False)`: Constructor del cliente HTTP.
- `send_to_api(data={}) -> bool`: Envía el diccionario de telemetría a la API REST.
- `get_data_from_api()`: Petición GET para comprobar conectividad y sincronizar RTC con cabecera `Date`.

## Dependencias en ambos sentidos

### Consume de
- `urequests`: Cliente HTTP ligero de MicroPython para microcontroladores.
- `ujson`: Serialización JSON.
- `Models.RpiPico.RpiPico` (a través del parámetro `controller`): Para comprobar estado Wi-Fi y reconectar.
- `time.sleep_ms`: Pausas de reintento.

### Es consumido por
- [`src/main.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/main.py): Para subir las lecturas completas o consolidadas.

## Configuración

| Variable | Valor por defecto | Efecto / Comportamiento |
|---|---|---|
| `API_URL` | `"https://api.raupulus.dev/api"` | Dirección base de la API REST |
| `API_PATH` | `"weatherstation/v1/generic/add/json"` | Ruta del endpoint receptor |
| `API_TOKEN` | Credencial Bearer | Token de autenticación de la estación |
| `DEVICE_ID` | `18` | Identificador numérico de la estación en el backend |
| `API_ENABLED` | `True` | Habilita o inhabilita el envío HTTP |

## Trampas conocidas

- **Cierre de socket obligatorio**: En MicroPython, no cerrar `response.close()` en cada llamada de `urequests` provocará el agotamiento de sockets disponibles (`ENOMEM` o `OSError: -28`), bloqueando las comunicaciones Wi-Fi posteriores.
- **Llamada bloqueante**: El método `send_to_api()` es síncrono. Durante la resolución DNS, handshake TLS y transferencia HTTP, el hilo que lo ejecuta queda bloqueado. Por esta razón se ejecuta en el Core 0 de forma controlada mientras se señala con `led_read`.

## Tests que lo cubren

- `⚠️ sin verificar` (no hay mocks automatizados ni tests unitarios).
- Verificación manual: Comprobación contra servidor real con `DEBUG=True`, verificando la recepción de respuesta HTTP 201.

## Pendiente real

- [ ] Incorporar timeout explícito en la llamada a `urequests.post` para evitar bloqueos indefinidos si la red congela el socket TLS.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
