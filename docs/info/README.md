# Documentación Técnica Viva: `docs/info/`

Índice maestro de la documentación técnica activa del receptor de estación meteorológica Bresser sobre Raspberry Pi Pico W y CC1101.

> [!IMPORTANT]
> **Jerarquía de verdad sobre el estado actual:**
> Código (`src/`) > `docs/info/` > `AGENTS.md` > el resto.
> Cualquier discrepancia detectada entre la documentación y el código se corrige en el mismo commit.

---

## 1. Módulos del Sistema (`src/`)

Cada archivo de código cuenta con su documento técnico viva asociado según la plantilla oficial [`_MODULE_TEMPLATE.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/_MODULE_TEMPLATE.md):

| Módulo Fuente | Documento de Referencia | Responsabilidad Principal |
|---|---|---|
| [`src/main.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/main.py) | [`main.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/main.md) | Orquestador principal, multihilo dos cores RP2040, doble buffer y eventos GDO0. |
| [`src/Drivers/CC1101.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Drivers/CC1101.py) | [`CC1101.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/CC1101.md) | Driver SPI de bajo nivel para el transceptor RF CC1101 a 868.3 MHz. |
| [`src/Models/WeatherSensor.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/WeatherSensor.py) | [`WeatherSensor.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/WeatherSensor.md) | Decodificador multiprotocolo Bresser 5-en-1 y 6-en-1 (LFSR, paridad, BCD). |
| [`src/Models/Api.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/Api.py) | [`Api.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/Api.md) | Cliente HTTP REST con reconexión Wi-Fi y serialización de telemetría. |
| [`src/Models/RpiPico.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/RpiPico.py) | [`RpiPico.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/RpiPico.md) | Abstracción de la Pico W: Wi-Fi con fallback, bus SPI, RTC, temperatura interna RP2040. |
| [`src/env.py`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/env.py) | [`env.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/env.md) | Configuración global, credenciales, pines y flags operacionales. |

---

## 2. Documentos de Arquitectura, Hardware y Operación

- [`_MODULE_TEMPLATE.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/_MODULE_TEMPLATE.md): Plantilla obligatoria para documentar cualquier módulo nuevo.
- [`DESIGN.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/DESIGN.md): Arquitectura de estados del firmware y protocolo de señalización visual de LEDs.
- [`COMPONENTS.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/COMPONENTS.md): Inventario físico, diagrama de cableado SPI y pinout de la Raspberry Pi Pico W.
- [`commands.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/commands.md): Comandos de flasheo, consola REPL interactiva, y modos de búsqueda de IDs.
- [`decisiones-tecnicas.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/decisiones-tecnicas.md): Decisiones arquitecturales deliberadas (doble hilo, buffers estáticos, ISR diferida).
- [`apis/raupulus-weatherstation.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/apis/raupulus-weatherstation.md): Cómo se integra desde este cliente la API REST de destino.

---

## 3. APIs y Especificaciones Externas de Terceros

La documentación técnica destilada y verificada de tecnologías externas se encuentra en:
- [`docs/apis/bresser-protocol/`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/bresser-protocol/README.md): Especificación de trama de radio Bresser 868 MHz.
- [`docs/apis/cc1101/`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/cc1101/README.md): Registros y strobes del chip TI CC1101.
- [`docs/apis/raupulus-api/`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/raupulus-api/README.md): Especificación oficial de la API de telemetría.

---

## 4. Reglas de Lectura Dirigida

Al trabajar en una tarea específica, optimiza el contexto de lectura:
1. **Trabajando en un módulo**: Lee únicamente su `.md` correspondiente (ej. `CC1101.md`).
2. **Tocando pines o LEDs**: Añade `COMPONENTS.md` y `DESIGN.md`.
3. **Tocando una API o protocolo externo**: Añade su carpeta en `docs/apis/<api>/` siguiendo: `README.md` → `00-fundamentos.md` + `ERRATAS.md` + `LIMITACIONES.md`.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
