# AGENTS.md — Guía para desarrollar este proyecto con MicroPython

Este archivo describe el contexto, arquitectura, reglas de documentación y convenciones que debe seguir cualquier agente (humano o IA) que trabaje en este proyecto.

---

## Documentación: Protocolo y Reglas Permanentes

> [!IMPORTANT]
> **Jerarquía de verdad sobre el estado actual:**
> Código (`src/`) > `docs/info/` > `AGENTS.md` > el resto.  
> `docs/planning/`, `docs/future/` y `docs/auditorias/` NUNCA son fuente de verdad del estado.

### Reglas Permanentes
1. **Documentar es parte de la tarea**: Ninguna tarea está terminada si su documentación no se actualiza EN EL MISMO COMMIT que el código.
2. **Discrepancia entre documentación y código**: Se corrige en el commit en que se detecta, no se anota para después.
3. **Mantenimiento de módulos**: Tocas un módulo → actualizas su `.md`. Creas uno → lo creas desde `docs/info/_MODULE_TEMPLATE.md` y lo indexas en `docs/info/README.md` y en `AGENTS.md`. Eliminas uno → borras su `.md` y lo quitas de TODOS los índices.
4. **Pie de firma temporal obligatorio**: Todo archivo bajo `docs/`, en cualquier subdirectorio, termina con esta línea exacta detrás de un separador `---`:  
   `> Creado: YYYY-MM-DD · Última revisión: YYYY-MM-DD`.  
   La fecha de creación no se modifica nunca; la de revisión se actualiza en el mismo commit que el documento.
5. **Checklists de verificación**: Toda fase o módulo de una planificación empieza con una descripción y termina con un checklist `- [ ]`. `[x]` significa verificado funcionando y cumpliendo. Escribir el código no marca la casilla.
6. **Contenido efímero**: `docs/planning/` y `docs/auditorias/` son trabajo temporal de UN desarrollador (no compartido, ignorados por git). Ciclo: crear → trabajar → verificar → promocionar lo duradero → BORRAR.
7. **Promoción antes de borrar**:
   - Comportamiento del módulo → `docs/info/<modulo>.md`
   - Decisión deliberada de diseño → `docs/info/decisiones-tecnicas.md`
   - Trampa duradera → Tabla de trampas de este `AGENTS.md`
   - Cambio de arquitectura, rutas o comandos → este `AGENTS.md`
   - Idea aplazada → `docs/future/`
   - Regresión → un test o procedimiento de verificación en el `.md` del módulo.
8. **Sin enlaces rotos**: Nada versionado en git puede enlazar a `docs/planning/` ni a `docs/auditorias/`. Ambos deben permanecer en `.gitignore`.
9. **Lectura Dirigida**: Trabajando en un módulo lees SOLO su `.md` en `docs/info/`; si tocas hardware o LEDs añades `DESIGN.md` y `COMPONENTS.md`; si tocas una API o protocolo de terceros añades `docs/apis/<api>/` en este orden: `README.md` → `00-fundamentos.md` + `ERRATAS.md` + `LIMITACIONES.md` → solo el archivo específico que necesites. No leas el resto de `docs/info/`, ni `docs/future/`, ni `docs/planning/`.
10. **Verificación de APIs externas**: Nunca configures nada a partir de la especificación oficial de una API o protocolo externo sin verificarlo con una petición o prueba real. Lo no comprobado se marca como `⚠️ sin verificar`.
11. **Convención de idioma**: Documentación, comentarios y textos de usuario en español. Identificadores, nombres de fichero y de directorio, y mensajes de log en inglés. Excepción: los campos que devuelve una API de terceros se leen tal como los envía.
12. **Atribución**: Nick `@raupulus`, email `public@raupulus.dev`. Sin firmas de agente en commits, PRs ni documentación (nada de `Co-Authored-By`, «Generated with…» ni identificadores de sesión).

### Índice Maestro de `docs/info/`

| Documento | Enlace | Contenido |
|---|---|---|
| Índice Maestro | [`docs/info/README.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/README.md) | Visión general, índice de módulos y reglas de navegación |
| Plantilla de Módulo | [`docs/info/_MODULE_TEMPLATE.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/_MODULE_TEMPLATE.md) | Estructura canónica obligatoria para documentar módulos |
| Orquestador Main | [`docs/info/main.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/main.md) | Bucle principal, multihilo RP2040, buffers y sincronismo |
| Driver CC1101 | [`docs/info/CC1101.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/CC1101.md) | Driver SPI a 868.3 MHz, registros de radio y control de FIFO |
| Decodificador Radio | [`docs/info/WeatherSensor.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/WeatherSensor.md) | Decodificación Bresser 5-en-1 y 6-en-1, LFSR, paridad y BCD |
| Cliente API REST | [`docs/info/Api.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/Api.md) | Cliente HTTP con urequests, reconexión Wi-Fi y JSON |
| Abstracción Hardware | [`docs/info/RpiPico.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/RpiPico.md) | Wi-Fi con fallback, SPI, RTC, temperatura interna RP2040 |
| Variables de Entorno | [`docs/info/env.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/env.md) | Configuración de pines, claves, flags y límites |
| Diseño de Estados y LEDs | [`docs/info/DESIGN.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/DESIGN.md) | Diagrama de estados y código de parpadeos de LEDs |
| Componentes y Pinout | [`docs/info/COMPONENTS.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/COMPONENTS.md) | Inventario físico, diagrama de pines y resistencia pull-up |
| Comandos de Flashing | [`docs/info/commands.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/commands.md) | Guía de mpremote, PyCharm run configurations y REPL |
| Decisiones Técnicas | [`docs/info/decisiones-tecnicas.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/decisiones-tecnicas.md) | Justificación de 2 hilos, buffers estáticos e ISR diferida |
| Integración API REST | [`docs/info/apis/raupulus-weatherstation.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/info/apis/raupulus-weatherstation.md) | Cómo consume el firmware el endpoint `/add/json` |

---

## Descripción del proyecto

Receptor de datos de estación meteorológica Bresser 5-en-1 / 6-en-1 corriendo en una **Raspberry Pi Pico W** con MicroPython. El hardware de RF es un transceptor **CC1101** conectado por SPI que escucha a **868.3 MHz**. Los datos decodificados se suben a una API REST externa mediante Wi-Fi.

El proyecto es **solo recepción (RX)**; no emite señal alguna.

---

## Directorios relevantes

```
src/                       ← Código fuente activo en MicroPython.
  main.py                  ← Bucle principal, IRQ GDO0, doble buffer, hilos
  env.py                   ← Variables de entorno activas (ignorado en git)
  .env.example.py          ← Plantilla base de configuración para nuevas instalaciones
  Drivers/
    CC1101.py              ← Driver SPI del transceptor CC1101
  Models/
    WeatherSensor.py       ← Wrapper de radio + decodificador Bresser 5/6-en-1
    Api.py                 ← Cliente HTTP para la API REST
    RpiPico.py             ← Abstracción de hardware (Wi-Fi, SPI, I2C, ADC, RTC)

docs/
  info/                    ← Documentación técnica VIVA del proyecto
  apis/                    ← Documentación oficial destilada de tecnologías de terceros
    bresser-protocol/      ← Especificación del protocolo de radio Bresser 868 MHz
    cc1101/                ← Registros y strobes del chip TI CC1101
    raupulus-api/          ← Especificación del servicio REST de telemetría
  future/                  ← Iniciativas y componentes decididos pero aplazados
  deploys/                 ← Guías de despliegue en placas Pico W
  images/                  ← Esquemas y fotos del hardware

old_c_project/             ← Proyecto C en ESP32. SOLO REFERENCIA para debugging (no tocar).
old_python_project/        ← Versión Python anterior. SOLO REFERENCIA (no tocar).
```

---

## Entorno de ejecución

- **Hardware**: Raspberry Pi Pico W (RP2040, dual core ARM Cortex-M0+ a 133 MHz)
- **Firmware**: MicroPython 1.28+ para RP2 Pico W
- **Python target**: MicroPython — sin CPython stdlib completa
- **Módulos disponibles en MicroPython**: `machine`, `network`, `urequests`, `ujson`, `utime`/`time`, `_thread`, `micropython`, `ntptime`, `gc`, `urandom`, `binascii`
- **Módulos NO disponibles**: `typing` (se shimea), `asyncio` (no se usa en este proyecto), `threading` (se usa `_thread`)

### Restricciones MicroPython importantes

- `_thread` en RP2040 ejecuta el segundo hilo en **Core 1** — proteger recursos compartidos con `_thread.allocate_lock()`.
- `micropython.schedule()` es la única forma segura de procesar eventos tras una ISR (prohibido transaccionar por SPI dentro de una IRQ).
- `gc.collect()` debe llamarse periódicamente en el bucle principal para evitar fragmentación del heap.
- No usar `time.sleep()` (bloquea); usar `sleep_ms()` de `time` o `utime`.
- Los buffers de recepción deben ser preasignados como `bytearray` fijos para no generar presión en el recolector de basura.

---

## Arquitectura de dos hilos

```
Core 0 (main.py bucle while True)
  ├── Polling rápido del FIFO del CC1101 (ws.receive timeout=0)
  ├── Escribe paquetes en el buffer activo (bufA o bufB)
  ├── Rota el lote cuando está lleno (BATCH_SIZE) o expira BATCH_WINDOW_MS
  ├── Gestiona subida a la API (api.send_to_api)
  ├── Servicio de LEDs alternos y latido no bloqueante
  └── IRQ GDO0 → micropython.schedule(_on_gdo0_scheduled)

Core 1 (processor_thread)
  ├── Espera lotes marcados como ready (batch_ready[])
  ├── Decodifica cada trama (ws.decode)
  ├── Agrega variables meteorológicas (temp / hum / viento / lluvia)
  ├── Controla timeout de mediciones parciales (PARTIAL_UPLOAD_TIMEOUT_MS)
  └── Cuando el conjunto está completo → _set_upload_payload()
```

La comunicación entre hilos usa matrices preasignadas + `_thread.allocate_lock()`.

---

## Decodificación Bresser

- **Bresser 6-en-1 (18 bytes)**: Verificación con LFSR-16 (`gen=0x8810`, `init=0x5412`) coincidente con `(msg[0]<<8)|msg[1]` y suma con acarreo en `msg[2:18]` igual a `0xFF`. Temperatura negativa calculada como `(raw - 1000) * 0.1` si `raw > 600`.
- **Bresser 5-en-1 (26 bytes)**: Verificación por paridad invertida (`msg[i] ^ msg[i+13] == 0xFF`) y checksum por popcount en `msg[14:26]` igual a `msg[13]`. Factor de lluvia 2.5 en sensores profesionales `type >= 0x39 && <= 0x3B`.

---

## Tabla de Trampas Conocidas

| Subsistema | Trampa | Causa / Comportamiento | Solución / Mitigación |
|---|---|---|---|
| **Hardware SPI** | CC1101 en estado zombie al reiniciar Pico W | El pin CS queda flotando en alta impedancia durante el arranque | Instalar resistencia pull-up física de 10 kΩ a 3.3V en pin CSN (`GP17`) |
| **Transceptor RF** | Pérdida de recepción por `MARCSTATE=0x11` | El FIFO de 64 bytes se llena si se emiten ráfagas y el bucle tarda en drenar | Ejecutar `ensure_rx()` periódicamente para hacer flush (`SIDLE` + `SFRX` + `SRX`) |
| **MicroPython ISR** | Cuelgue del intérprete al recibir paquete | Intentar llamadas SPI directas dentro de la interrupción hardware del pin | Usar `micropython.schedule()` para diferir la lectura al contexto de MicroPython |
| **Cliente HTTP** | `OSError: -28` o agotamiento de memoria | No cerrar el socket de red tras una petición HTTP en microcontrolador | Llamar siempre a `response.close()` en un bloque `finally` |
| **Multihilo RP2040** | Corrupción de payloads o deadlocks | Escritura concurrente en buffers compartidos sin lock | Utilizar `_thread.allocate_lock()` en lecturas/escrituras de buffers y banderas |
| **Memoria Heap** | Congelaciones por Stop-The-World en GC | Creación continua de listas o cadenas temporales en el bucle de radio | Usar slicing sobre `bytearray` estáticos preasignados (`bufA`, `bufB`) |

---

## Referencia de Pines GPIO por Defecto

| Señal | GPIO Pico W | Función |
|---|---|---|
| SPI0 SCK | `GP18` | Reloj SPI del CC1101 |
| SPI0 MOSI | `GP19` | Salida de datos Pico W → CC1101 |
| SPI0 MISO | `GP16` | Entrada de datos CC1101 → Pico W |
| SPI0 CS (CSN) | `GP17` | Chip select (requiere resistencia Pull-Up 10kΩ a 3.3V) |
| GDO0 | `GP20` | Fin de paquete de radio (IRQ falling diferida) |
| GDO2 | `GP21` | Estado de radio (reservado) |
| LED ON | `GP15` | Indicador fijo de bucle activo esperando datos (verde) |
| LED READ | `GP7` | Indicador de subida HTTP activa a la API (rojo) |
| LED ALT1 | `GP13` | Parpadeo alterno al decodificar paquete válido (azul 1) |
| LED ALT2 | `GP14` | Parpadeo alterno al decodificar paquete válido (azul 2) |
| Onboard LED | `"LED"` | Indicador fijo de encendido del microcontrolador (verde) |

---

## Cómo trabajar en este proyecto

1. **Lectura dirigida**: Al trabajar en un módulo, lee únicamente su documento técnico en `docs/info/<modulo>.md`.
2. **Configuración local**: Copia `src/.env.example.py` a `src/env.py` y ajusta credenciales. Nunca subas `env.py` al control de versiones.
3. **Flashing**: Flashea con la configuración PyCharm "Flash src" o mediante `mpremote fs cp ...`.
4. **No tocar referencias históricas**: `old_c_project/` y `old_python_project/` son de solo lectura.
5. **Cierre de tareas**: No des por finalizada ninguna tarea sin actualizar en el **mismo commit** el documento correspondiente en `docs/info/` y la fecha de última revisión.
