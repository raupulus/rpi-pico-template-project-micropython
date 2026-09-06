# Integración API: Raupulus WeatherStation

Documento de integración técnica que detalla cómo consume este proyecto la API meteorológica externa.

Para la documentación oficial destilada de la API externa, ver [`docs/apis/raupulus-api/`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/raupulus-api/README.md).

## 1. Responsable de la Integración en el Código

- Módulo: [`src/Models/Api.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/Api.py)
- Consumidor: [`src/main.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/main.py)

## 2. Puntos de Conexión y Endpoints

- **URL Base**: Configurada en `env.API_URL` (por defecto `https://api.raupulus.dev/api`).
- **Endpoint de Subida**: Configurado en `env.API_PATH` (por defecto `weatherstation/v1/generic/add/json`).
- **Método HTTP**: `POST`.
- **Autenticación**: `Authorization: Bearer <env.API_TOKEN>`.
- **Cabeceras HTTP**:
  - `Authorization`: Token secreto.
  - `Content-Type`: `application/json`.
  - `Accept`: `application/json`.

## 3. Contrato de Datos

### Estructura del Payload Enviado
El firmware empaqueta las métricas climáticas agregadas en dos niveles para garantizar retrocompatibilidad:

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

### Respuestas Esperadas del Servidor
- **HTTP 201 Created**: Telemetría guardada satisfactoriamente en base de datos.
- **HTTP 200 OK**: Petición procesada correctamente.
- **Cualquier otro código o timeout**: El método `send_to_api()` registra error por consola si `DEBUG=True` y retorna `False`.

## 4. Gestión de Caídas de Red y Reintentos

Si la llamada `urequests.post` lanza una excepción (socket roto o pérdida de enlace Wi-Fi):
1. `Api.py` captura la excepción.
2. Llama a `controller._reconnect_wifi()` para restablecer la conexión inalámbrica.
3. Se desecha el intento actual sin bloquear el receptor para permitir que la radio siga escuchando.
4. El siguiente lote consolidado volverá a intentar la subida.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
