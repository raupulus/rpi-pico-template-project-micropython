# Contrato API V2 — Estación meteorológica (Weather Station)

> Este archivo documenta **solo el contrato HTTP** de este módulo: rutas, auth,
> parámetros y forma exacta de la respuesta. Está pensado para copiarse a otro
> proyecto (o pegarse en el contexto de una IA) y que con eso baste para
> integrar estos endpoints sin leer el código fuente.
>
> Para el contexto de negocio (qué es cada sensor, hardware, decisiones de
> producto) ver [`docs/info/weather-station.md`](../../weather-station.md). La
> integración con AEMET es interna y no tiene endpoints propios: no se
> documenta aquí.

## Base y convenciones comunes a toda la API V2

- **Base URL**: `/api/v2`
- **Todas las respuestas** usan este envelope (`App\Traits\ApiResponseTrait`):

  ```json
  // Éxito
  { "success": true, "message": "Operación exitosa", "data": { ... } }
  // Error
  { "success": false, "message": "Descripción del error", "errors": { "campo": ["detalle"] } }
  ```

  `errors` solo aparece si hay detalle (p. ej. errores de validación 422).
- **Colecciones paginadas** (`paginatedResponse`) añaden un bloque `meta`
  junto a `data`:

  ```json
  {
    "success": true,
    "message": "Operación exitosa",
    "data": [ /* array de recursos */ ],
    "meta": {
      "total": 128340,
      "per_page": 25,
      "current_page": 1,
      "last_page": 5134,
      "from": 1,
      "to": 25
    }
  }
  ```

- **Autenticación**: Laravel Sanctum, cabecera `Authorization: Bearer <token>`.
  Las lecturas públicas (`GET`) no requieren autenticación. Las escrituras
  (`POST`) requieren un **token de dispositivo IoT** con la ability
  `weatherstation:write` (`App\Support\Auth\TokenAbilities::WEATHERSTATION_WRITE`),
  emitido desde `POST /auth/tokens/devices` (ver
  [`docs/info/api/v2/auth.md`](./auth.md)). El token de dispositivo va además
  ligado a un `device:{id}` concreto: solo puede escribir en esa estación.
- **Ruta inexistente**: cualquier método/URL que no esté documentado responde
  `404` con `{ "success": false, "message": "API V2 - Endpoint no encontrado" }`
  (incluso si el método HTTP es el que no cuadra: el contrato es la pareja
  método+ruta, no hay 405).

### Diseño clave: una lectura cuelga de su estación

Antes la URL no decía de qué estación era una lectura: `GET
/weatherstation/temperature` devolvía las temperaturas de **todas** las
estaciones mezcladas, sin paginar (sobre una tabla de millones de filas, eso
no es una respuesta lenta, es el servidor caído). Ahora cada lectura cuelga de
su estación y va paginada: `GET /weather-stations/3/temperatures`.

Se mantiene **un endpoint por sensor** (no uno genérico) a propósito: permite
emitir un token de dispositivo que solo pueda subir, por ejemplo, luz y
radiación, y no el resto de sensores.

---

## Catálogo de sensores (`{sensor}`)

`{sensor}` en las rutas de lecturas es uno de estos **11 valores exactos**
(segmento de URL, en plural). Es la lista completa y cerrada —
`App\Support\WeatherStation\SensorCatalog`—, cualquier otro valor responde
`404`:

| `{sensor}` | Modelo | Recurso (`GET`) |
|---|---|---|
| `temperatures` | Temperature | `TemperatureResource` |
| `humidities` | Humidity | `HumidityResource` |
| `pressures` | Pressure | `PressureResource` |
| `lights` | Light | `LightResource` |
| `winds` | Wind | `WindResource` |
| `wind-directions` | WindDirection | `WindDirectionResource` |
| `rains` | Rain | `RainResource` |
| `eco2-readings` | Eco2 | `Eco2Resource` |
| `tvoc-readings` | Tvoc | `TvocResource` |
| `air-qualities` | AirQuality | `AirQualityResource` |
| `lightnings` | Lightning | `LightningResource` |

Cada uno de estos 11 sensores tiene su propio `GET` (histórico paginado) y su
propio `POST` (escritura), documentados en la sección
[Lecturas por sensor](#lecturas-por-sensor-weather-stationsstationsensor).

Aparte, el endpoint agregado `GET /weather-stations` / `GET
/weather-stations/{station}` expone un conjunto **distinto** de claves de
sensor —agrupadas y ya formateadas para pintar—, controlado por
`WeatherStationResource::SENSORS`:

```
temperature, humidity, pressure, wind, light, air_quality, rain, lightning
```

(nota: aquí `wind` agrupa velocidad+dirección, `light` agrupa lux+UV,
`air_quality` agrupa calidad+eco2+tvoc y `rain` agrupa lluvia+intensidad — por
eso son 8 claves agregadas y no 11). No lo confundas con el catálogo de arriba.

---

## Estaciones (`/weather-stations`)

### `GET /weather-stations` — Listar estaciones (principal o por zona)

- **Auth**: pública, no requiere token.
- **Query params**:

| Parámetro | Tipo | Descripción |
|---|---|---|
| `zone` | string | Nombre de zona (insensible a mayúsculas). Sin este parámetro se devuelve solo la estación **principal** (la de exterior, o la primera disponible) dentro de un array de un elemento — o `[]` si no hay ninguna estación dada de alta. |
| `location_type` | string | Solo junto a `zone`. Uno de `indoor`, `outdoor`. |
| `sensors` | string | Lista separada por comas para acotar los bloques de sensor devueltos (ver catálogo agregado arriba). Sin este parámetro se devuelven los 8. |

- **Respuesta 200** (sin `zone`, estación principal):

```json
{
  "success": true,
  "message": "Operación exitosa",
  "data": [
    {
      "id": 3,
      "name": "Estación azotea (Chipiona)",
      "zone": "Chipiona",
      "location_type": "outdoor",
      "location_label": "Exterior",
      "instant": {
        "day_name": "domingo",
        "date_human_format": "30 de agosto de 2026",
        "time": "12:45",
        "day_status": "Día"
      },
      "temperature": 27.4,
      "humidity": 58.0,
      "pressure": 1012.3,
      "wind": {
        "average": 12.6,
        "min": 3.2,
        "max": 21.8,
        "direction": "NW",
        "direction_grades": 315
      },
      "light": {
        "lux": 45000.0,
        "uv_index": 6.2,
        "uva": 3.1,
        "uvb": 0.4
      },
      "air_quality": {
        "quality": 92.5,
        "eco2": 420,
        "tvoc": 15
      },
      "rain": {
        "value": 0.0,
        "intensity": 0.0
      },
      "lightning": {
        "last_at": "2026-08-29T18:20:11.000000Z",
        "window_minutes": 60,
        "count_in_window": 0,
        "distance": 12.4,
        "energy": 3200
      }
    }
  ]
}
```

  Cada bloque de sensor sale `null` (o con sus campos internos en `null`) si
  no hay ninguna lectura guardada todavía. `direction_grades` es entero
  (grados 0–360), `wind.average/min/max` van en km/h (convertidos desde el
  m/s que se almacena). Todos los decimales están redondeados a 2.

- **Errores**: ninguno propio; con `zone` sin coincidencias responde `200`
  con `data: []`.

### `GET /weather-stations/{station}` — Una estación por id

- **Auth**: pública.
- **Parámetros de ruta**: `{station}` = id numérico (`whereNumber`).
- **Query params**: `sensors` (igual que arriba).
- **Respuesta 200**: un único objeto con la misma forma que un elemento del
  array anterior (no array).
- **Errores**: `404` `{"success": false, "message": "Estacion meteorologica no encontrada"}`.

### `GET /weather-stations/zone/{zone}/{locationType?}` — Lectura AGREGADA de una zona

**Nuevo el 2026-09-06.**

⚠️ **No confundir con `GET /weather-stations?zone=…`**, que devuelve la *lista* de
estaciones de esa zona. Éste devuelve **una sola lectura**: la de la zona
entendida como conjunto.

Para cada sensor toma el registro **más reciente de cualquiera de las estaciones
de la zona**, en vez de atarse a un aparato concreto. Es lo que consume el widget
de portada.

El porqué: el widget iba fijado a una estación, y en cuanto ésa dejaba de subir
seguía enseñando su último valor —la humedad al 49 % durante días— mientras la
estación de al lado, en la misma azotea, subía el 20 % real. El dato bueno
estaba en la base y no se miraba.

- **Auth**: pública.
- **Parámetros de ruta**:
  - `{zone}`: nombre de la zona, insensible a mayúsculas (`Azotea`).
  - `{locationType}`: opcional, sólo `indoor` o `outdoor`. Acota el resto de sensores.
- **Respuesta 200**: un único objeto con **la misma forma** que
  `GET /weather-stations/{station}`. Un cliente que ya consumiera aquél sólo
  cambia la URL, no el parseo.
- **Errores**: `404` `{"success": false, "message": "Zona sin estaciones meteorologicas"}`.

Tres reglas del agregado que conviene tener claras:

1. **La presión ignora `{locationType}`**: sale de cualquier estación de la zona,
   interior incluida. Un barómetro mide lo mismo dentro que fuera y a la
   interperie se estropea antes, así que suele vivir en un cacharro de interior.
2. **Los rayos se cuentan en toda la zona**, no en un dispositivo.
3. La estación que aparece como referencia (`name`, `location_label`) es la que
   trae el dato más reciente de todas: la que está viva ahora mismo.

Zona por defecto del widget: `weather_station.main_zone` (variable de entorno
`WEATHER_STATION_MAIN_ZONE`); sin configurar, la primera zona de exterior.

---

## Lecturas por sensor (`/weather-stations/{station}/{sensor}`)

### `GET /weather-stations/{station}/{sensor}` — Histórico paginado de un sensor

- **Auth**: pública.
- **Rate limit**: ninguno propio (sujeto solo al limitador general `api`).
- **Parámetros de ruta**:
  - `{station}`: id numérico de la estación (`whereNumber`).
  - `{sensor}`: uno de los 11 valores del catálogo. Un valor fuera de la lista
    no matchea la ruta → `404` genérico de "Endpoint no encontrado".
- **Query params** (vía `CollectionQuery`, columnas permitidas: `created_at`):

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `page` | `?page=2` | Página, por defecto 1. |
| `per_page` | `?per_page=50` | Tamaño de página, por defecto 25, máximo **100**. |
| `sort` | `?sort=-created_at` | Orden; `-` es descendente. Por defecto `created_at` descendente. |
| `from` / `to` | `?from=2026-08-01&to=2026-08-30` | Alias de `created_at[gte]` / `created_at[lte]`. |
| `created_at[gte]`, `created_at[lte]`, etc. | `?created_at[gte]=2026-08-01` | Rango explícito (`gte`, `gt`, `lte`, `lt`, `ne`). |
| `minutes` | `?minutes=30` | Ventana en minutos hacia atrás desde ahora (`created_at >= now() - minutes`). Tope configurable, por defecto 10080 (7 días). Nació para `lightnings` pero aplica a cualquier sensor. |

- **Respuesta 200** (paginada, ejemplo con `temperatures`):

```json
{
  "success": true,
  "message": "Operación exitosa",
  "data": [
    {
      "id": 918234,
      "hardware_device_id": 3,
      "value": 27.4,
      "created_at": "2026-08-30T12:45:00.000000Z"
    }
  ],
  "meta": {
    "total": 2634981,
    "per_page": 25,
    "current_page": 1,
    "last_page": 105400,
    "from": 1,
    "to": 25
  }
}
```

- **Forma de cada Resource**: todos comparten la base `id`,
  `hardware_device_id`, `created_at` (ISO 8601, sin `updated_at`: son series
  temporales, una lectura no se corrige, se añade otra), más los campos
  propios de valor:

| `{sensor}` | Campos propios |
|---|---|
| `temperatures` | `value` |
| `humidities` | `value` |
| `pressures` | `value` |
| `eco2-readings` | `value` |
| `tvoc-readings` | `value` |
| `lights` | `lumens`, `index`, `lux` (puede ser `null`: falta en ~6 % de las filas de producción aunque la columna sea NOT NULL), `uva`, `uvb` |
| `winds` | `speed`, `average`, `min`, `max` |
| `wind-directions` | `resistance`, `direction`, `grades` |
| `rains` | `rain`, `rain_intensity`, `rain_month`, `moisture` |
| `air-qualities` | `gas_resistance`, `air_quality` |
| `lightnings` | `distance`, `energy`, `noise_floor` |

- **Errores**: `404` `{"success": false, "message": "Sensor no reconocido"}` si
  `{sensor}` no está en el catálogo (caso border: normalmente ni matchea la
  ruta y da el 404 genérico de "Endpoint no encontrado" antes de llegar al
  controlador).

### `POST /weather-stations/{station}/{sensor}` — Guardar lectura(s) de un sensor

- **Auth**: `auth:sanctum` + `ability:weatherstation:write`. El dispositivo
  indicado en la URL debe pertenecer al usuario dueño del token, y si el
  token está ligado a un `device:{id}` concreto, debe coincidir.
- **Rate limit**: `api-store` — 60 peticiones/min por token (`RATE_LIMIT_IOT_STORE`, configurable).
- **Parámetros de ruta**: igual que el `GET`.
- **Body**, dos formas admitidas:

  1. Una lectura suelta — los campos del sensor directamente en la raíz:

     ```json
     { "value": 27.4 }
     ```

  2. Un lote del mismo sensor:

     ```json
     { "readings": [ { "value": 27.4 }, { "value": 27.6 } ] }
     ```

  Máximo **500** lecturas por lote (`StoreSensorReadingsRequest::MAX_PER_BATCH`).
  Los campos exigidos son los mismos que aparecen en la tabla de "Campos
  propios" de arriba, con estas reglas de validación:

| `{sensor}` | Reglas |
|---|---|
| `temperatures`, `humidities`, `pressures`, `eco2-readings`, `tvoc-readings` | `value`: requerido, numérico |
| `lights` | `lumens`: requerido, numérico · `lux`, `index`, `uva`, `uvb`: opcionales, numéricos |
| `winds` | `speed`, `average`, `min`, `max`: requeridos, numéricos, ≥ 0 |
| `wind-directions` | `direction`: requerido, string, máx. 10 · `grades`: requerido, numérico, 0–360 · `resistance`: opcional, numérico |
| `rains` | `rain`: requerido, numérico, ≥ 0 · `moisture`: requerido, numérico · `rain_intensity`, `rain_month`: opcionales, numéricos, ≥ 0 |
| `air-qualities` | `gas_resistance`, `air_quality`: requeridos, numéricos |
| `lightnings` | `distance`: requerido, numérico, ≥ 0 · `energy`: requerido, numérico · `noise_floor`: opcional, numérico |

  Cualquier campo extra que mande el firmware (de una versión antigua, por
  ejemplo) se descarta sin error: solo se guardan los campos declarados
  arriba.

  Admite además, en la raíz (junto a la lectura o el lote), una clave opcional
  `hardware_device_info` (object|null) con el último estado del propio
  dispositivo (`temp`, `voltage`, `battery_level`, `cpu`, `disk`, `uptime`,
  `ram`, `ip_local`, `extra`; **`ip_public` ya no se acepta**, la pone el
  servidor); si viene, se aplica sobre `{station}` en
  la misma petición. Mismos campos que `PUT /hardware/devices/{device}/status`
  — contrato completo en [`hardware.md`](./hardware.md).

- **Respuesta 201**:

```json
{
  "success": true,
  "message": "Lectura almacenada",
  "data": { "stored": 1 }
}
```

  (`"Lecturas almacenadas"` en plural si se envió un lote con más de una
  lectura). `created_at` lo pone el servidor en el momento del insert; no se
  puede mandar en el body.

- **Errores**: `401` sin token o token inválido, `403` ability incorrecta o
  dispositivo que no pertenece al usuario/token, `404` `{"success": false,
  "message": "Sensor no reconocido"}` si `{sensor}` no está en el catálogo,
  `422` validación (campos requeridos, tipos, `hardware_device_id` inexistente
  o ajeno), `429` límite de tasa superado.

---

## Lote multi-sensor (`POST /weather-stations/{station}/readings`)

Excepción consciente al REST puro: en vez de 11 peticiones (una por sensor),
todos los sensores se suben en una sola. Pensado para un microcontrolador con
batería, donde cada petición de radio tiene coste.

- **Auth**: `auth:sanctum` + `ability:weatherstation:write` (misma
  comprobación de pertenencia que el `POST` individual).
- **Rate limit**: `api-store-batch` — 20 peticiones/min por token (`RATE_LIMIT_IOT_BATCH`, configurable).
- **Parámetros de ruta**: `{station}` = id numérico.
- **Body**: `data` es un objeto cuya clave es la **clave del lote** de cada
  sensor (no el segmento de URL) y cuyo valor es un array de lecturas de ese
  sensor, con los mismos campos y reglas que el `POST` individual:

| Clave en `data` | Segmento equivalente |
|---|---|
| `temperature` | `temperatures` |
| `humidity` | `humidities` |
| `pressure` | `pressures` |
| `light` | `lights` |
| `wind` | `winds` |
| `wind_direction` | `wind-directions` |
| `rain` | `rains` |
| `eco2` | `eco2-readings` |
| `tvoc` | `tvoc-readings` |
| `air_quality` | `air-qualities` |
| `lightning` | `lightnings` |

  Ejemplo:

  ```json
  {
    "data": {
      "temperature": [ { "value": 27.4 } ],
      "humidity": [ { "value": 58.0 } ],
      "wind": [ { "speed": 4.1, "average": 3.2, "min": 1.0, "max": 6.5 } ],
      "wind_direction": [ { "direction": "NW", "grades": 315 } ],
      "rain": [ { "rain": 0.0, "moisture": 12.0 } ],
      "light": [ { "lumens": 45000 } ],
      "air_quality": [ { "gas_resistance": 128000, "air_quality": 92.5 } ],
      "eco2": [ { "value": 420 } ],
      "tvoc": [ { "value": 15 } ],
      "lightning": [ { "distance": 12.4, "energy": 3200 } ]
    }
  }
  ```

  No hace falta mandar los 11: los que falten simplemente no se guardan en
  esta petición. Una clave que no esté en la tabla de arriba se rechaza con
  `422` (antes se ignoraba en silencio y esa lectura se perdía sin avisar).

  Igual que en el `POST` individual, admite en la raíz una clave opcional
  `hardware_device_info` con el estado del dispositivo — se aplica sobre
  `{station}` en la misma petición. Contrato completo en
  [`hardware.md`](./hardware.md).

- **Respuesta 201**:

```json
{
  "success": true,
  "message": "Lecturas almacenadas",
  "data": { "stored": 7 }
}
```

  `stored` es el total de filas insertadas sumando todos los sensores del
  lote, no el número de sensores.

- **Errores**: `401` sin token, `403` ability/pertenencia, `422` validación
  (clave de sensor desconocida, campos de un sensor concreto inválidos,
  `data` vacío), `429` límite de tasa superado.

---

## Lo que existió y ya no tiene ruta (no lo reimplementes igual)

| Ruta antigua | Qué pasó |
|---|---|
| `GET /weatherstation/temperature` (y equivalentes por sensor) | Devolvía **todas** las lecturas de **todas** las estaciones sin paginar. Ahora es `GET /weather-stations/{station}/temperatures`, paginado y filtrado por estación. |
| `GET /weatherstation/zone/{zone}` | Es `GET /weather-stations?zone={zone}`: la zona pasó a ser un filtro de la colección, no una ruta propia. |
| 11 controladores + 11 FormRequests casi idénticos, uno por sensor | Un único `SensorReadingController` + `SensorCatalog` como fuente única de verdad de sensores/reglas/modelos/resources. |

---

> Creado: 2026-08-30 · Última revisión: 2026-09-06
