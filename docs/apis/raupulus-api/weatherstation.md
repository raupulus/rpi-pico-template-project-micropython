# Endpoint: `/weatherstation/v1/generic/add/json`

> **Fuentes**: Implementación de backend `api.raupulus.dev`.  
> **Fecha de verificación real**: 2026-09-06

## Contrato de Datos

### Petición HTTP
- **Método**: `POST`
- **Ruta**: `/weatherstation/v1/generic/add/json`

### Estructura del Cuerpo (JSON)
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

### Campos
| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `hardware_device_id` | `integer` | Sí | Identificador de hardware del equipo |
| `temperature` | `float` | No | Temperatura en grados Celsius |
| `humidity` | `float` | No | Humedad relativa (0.0 - 100.0 %) |
| `wind_speed` | `float` | No | Velocidad instantánea del viento en m/s |
| `wind_average_speed` | `float` | No | Velocidad media del viento en m/s |
| `wind_min_speed` | `float` | No | Velocidad mínima del viento en m/s |
| `wind_max_speed` | `float` | No | Ráfaga máxima del viento en m/s |
| `wind_grades` | `float` | No | Dirección del viento en grados (0.0 - 359.9) |
| `rain` | `float` | No | Precipitación acumulada del evento en mm |
| `rain_intensity` | `float` | No | Tasa de precipitación estimada en mm/h |
| `rain_month` | `float` | No | Acumulado mensual de lluvia en mm |
| `data` | `object` | No | Objeto contenedor duplicado para compatibilidad con esquemas legados |

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
