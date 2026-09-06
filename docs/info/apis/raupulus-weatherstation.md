# Integración API: Raupulus WeatherStation (V2)

Documento de integración técnica que detalla cómo consume este proyecto la API meteorológica externa versión 2.

Para la documentación oficial destilada de la API externa, ver [`docs/apis/raupulus-api/`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/raupulus-api/README.md).

## 1. Responsable de la Integración en el Código

- Módulo: [`src/Models/Api.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/Api.py)
- Consumidor: [`src/main.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/main.py)

## 2. Puntos de Conexión y Endpoints

- **URL Base**: Configurada en `env.API_URL` (por defecto `https://api.raupulus.dev/api/v2`).
- **Endpoint de Subida Lote**: Configurado en `env.API_PATH` (por defecto `weather-stations/{station}/readings`).
  - `{station}` se interpola dinámicamente con `env.DEVICE_ID` en runtime.
- **Método HTTP**: `POST`.
- **Autenticación**: `Authorization: Bearer <env.API_TOKEN>` con ability `weatherstation:write`.
- **Cabeceras HTTP**:
  - `Authorization`: Token secreto.
  - `Content-Type`: `application/json`.
  - `Accept`: `application/json`.

## 3. Contrato de Datos V2

### Estructura del Payload Enviado
El firmware empaqueta las métricas climáticas agregadas en el formato multi-sensor V2:

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

### Reglas de Conversión
- **Rumbo cardinal**: La función [`degrees_to_cardinal()`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/Api.py) convierte `wind_grades` en uno de los 16 sectores estándar ("N", "NNE", etc.).
- **Campo `moisture`**: Asignado a `0.0` por defecto para sensores Bresser 5-en-1 / 6-en-1 que carecen de sonda de suelo, cumpliendo la validación obligatoria del backend.
- **Telemetría de la Pico (`hardware_device_info`)**:
  - `temp`: Temperatura CPU del RP2040 en °C.
  - `ip_local`: IP local asignada por Wi-Fi.
  - `uptime`: Segundos transcurridos desde el arranque del microcontrolador.
  - `disk`: Porcentaje de uso del LittleFS flash interno.
  - `ram`: Porcentaje de uso de memoria RAM (heap) en MicroPython (0–100%).
  - `extra`: Diccionario con métricas de bajo nivel (`rssi` en dBm, `mac`, `cpu_freq_mhz` y `reset_cause`).
  - *Nota*: `ip_public` no se envía desde el cliente; el backend la extrae de la conexión HTTP.

### Respuestas Esperadas del Servidor
- **HTTP 201 Created**: Lote insertado correctamente. Devuelve `{"success": true, "message": "Lecturas almacenadas", "data": {"stored": N}}`.
- **HTTP 200 OK**: Aceptado como fallback.
- **HTTP 422 Unprocessable Entity**: Validación fallida (claves o tipos incorrectos).
- **HTTP 401 / 403**: Fallo de token o ability `weatherstation:write`.

## 4. Gestión de Caídas de Red y Reintentos

Si la llamada `urequests.post` lanza una excepción (socket roto, timeout o caída Wi-Fi):
1. `Api.py` captura el error con backoff progresivo (`RETRY_DELAY_MS * intento`).
2. Alimenta el WDT hardware durante los intervalos de espera.
3. Invoca `controller._reconnect_wifi()` si detecta que la interfaz de red cayó.
4. Tras agotar `MAX_RETRIES` (3 intentos), descarta el payload sin bloquear el sistema para que la radio continúe drenando paquetes en Core 0.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
