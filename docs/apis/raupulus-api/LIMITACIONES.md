# Limitaciones: API Raupulus WeatherStation (V2)

> **Fuentes**: Arquitectura de endpoints de `api.raupulus.dev/api/v2`.  
> **Fecha de verificación real**: 2026-09-06

## 1. Rate Limiting de Dispositivos IoT
- **Lote multi-sensor (`POST /weather-stations/{station}/readings`)**: Rate limit `api-store-batch` configurado a **20 peticiones/minuto** por token.
- **Sensor individual (`POST /weather-stations/{station}/{sensor}`)**: Rate limit `api-store` configurado a **60 peticiones/minuto** por token.
- Superar el límite devuelve HTTP `429 Too Many Requests`. El firmware mitiga esto acumulando lecturas completas o esperando el `PARTIAL_UPLOAD_TIMEOUT_MS` (90 s), garantizando una frecuencia de subida muy inferior al límite.

## 2. Tamaño Máximo de Lotes
- Límite máximo de **500** lecturas por petición en lotes de sensor. El firmware de la estación envía 1 lectura por sensor en cada ciclo de transmisión consolidado.

## 3. Comportamiento ante Rutas Inexistentes
- Cualquier par método+URL que no coincida exactamente con las rutas registradas responde con `404 Not Found` y cuerpo `{"success": false, "message": "API V2 - Endpoint no encontrado"}` (no existe código 405 Method Not Allowed).

## 4. Sobrecarga de Handshake TLS en MicroPython
- Cada conexión HTTPS a través de `urequests` negocia una sesión mbedTLS completa sobre el RP2040 (típicamente 500–1500 ms de CPU y consumo temporal de sockets lwIP).
- **Consecuencia**: El bucle principal pausa la atención de radio estrictamente durante la petición y reactiva el modo de recepción inmediatamente tras el cierre del socket con `ws.radio.ensure_rx()`.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
