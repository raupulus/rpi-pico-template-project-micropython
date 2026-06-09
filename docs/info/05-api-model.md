# Modelo API — `src/Models/Api.py`

## Descripción

Cliente HTTP ligero para comunicarse con la API REST del sistema de monitorización meteorológica. Usa `urequests` (HTTP sin SSL en versiones simples; con SSL si el firmware lo incluye) y `ujson` de MicroPython.

## Constructor

```python
api = Api(
    controller=rpi,      # Instancia de RpiPico (para acceso a Wi-Fi si fuera necesario)
    url="https://api.example.com/api",
    path="weatherstation/v1/lightning/add-json",
    token="Bearer_token_aqui",
    device_id=18,
    debug=True
)
```

La URL completa se construye como `url + path` sin separador extra, por lo que `url` debe terminar en `/` o `path` debe empezar con `/` según convenga.

## Método `send_to_api(data)` — POST

Envía los datos meteorológicos a la API.

### Cabeceras enviadas

```
Authorization: Bearer <TOKEN>
Content-Type: application/json
```

### Cuerpo de la petición (JSON)

```json
{
    "hardware_device_id": <DEVICE_ID>,
    "data": {
        "temperature": float,
        "humidity": float,
        "wind_speed": float,
        "wind_average_speed": float,
        "wind_min_speed": float,
        "wind_max_speed": float,
        "wind_grades": float,
        "rain": float,
        "rain_intensity": float,
        "rain_month": float
    }
}
```

### Respuesta esperada

- **HTTP 201**: Subida correcta → devuelve `True`.
- Cualquier otro código o excepción: devuelve `False`.

### Campos del payload

| Campo | Tipo | Descripción |
|---|---|---|
| `temperature` | float | Temperatura en °C |
| `humidity` | float | Humedad relativa en % |
| `wind_speed` | float | Velocidad del viento actual (m/s) — igual a `wind_average_speed` |
| `wind_average_speed` | float | Velocidad media del viento (m/s) |
| `wind_min_speed` | float | Velocidad mínima (m/s) — actualmente igual a la media |
| `wind_max_speed` | float | Ráfaga máxima de viento (m/s) |
| `wind_grades` | float | Dirección del viento en grados (0..359) |
| `rain` | float | Lluvia incremental desde la última subida (mm) |
| `rain_intensity` | float | Intensidad de lluvia calculada (mm/h) |
| `rain_month` | float | Acumulado total del pluviómetro desde su reset (mm) |

## Método `get_data_from_api()` — GET

Petición GET al endpoint configurado. Devuelve el JSON parseado si la respuesta es HTTP 201, `False` en caso de error. Actualmente no se usa en el flujo principal del firmware, pero está disponible para futuras funcionalidades (recibir configuración remota, hora, etc.).

## Gestión de errores

Todas las excepciones están capturadas. En modo `DEBUG`, se imprime el error. Nunca lanza una excepción al código llamante; siempre devuelve `False` en caso de fallo.

Esto es importante en MicroPython: una excepción no capturada en el bucle principal detendría el firmware.

## Notas de implementación

- `urequests.post(url, headers=headers, json=payload)`: El parámetro `json=` serializa el diccionario automáticamente. No es necesario llamar `ujson.dumps` explícitamente.
- La respuesta (`response.text`) no se parsea en `send_to_api` para ahorrar memoria — solo se comprueba el código de estado.
- No hay reintentos implementados. Si falla la subida, el firmware sigue recibiendo datos y preparará el siguiente payload en el siguiente ciclo de agregación.
