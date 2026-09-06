# API Externa Raupulus WeatherStation (V2)

> **Fuentes**: Especificación oficial del backend REST en `https://api.raupulus.dev/api/v2`.  
> **Fecha de descarga**: 2026-09-06  
> **Fecha de verificación real**: 2026-09-06

Documentación oficial destilada del servicio receptor de telemetría ambiental para estaciones meteorológicas en su versión 2.

## Índice de Documentos

- [`00-fundamentos.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/raupulus-api/00-fundamentos.md): Esquema de autenticación Bearer Token, base URL `/api/v2`, envelope universal y códigos de estado.
- [`weatherstation.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/raupulus-api/weatherstation.md): Especificación del contrato V2: endpoint multi-sensor `POST /weather-stations/{station}/readings`, endpoints individuales y consulta `GET /weather-stations/{station}`.
- [`ERRATAS.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/raupulus-api/ERRATAS.md): Comportamientos documentados y consideraciones de migración desde V1.
- [`LIMITACIONES.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/raupulus-api/LIMITACIONES.md): Rate limiting específico (`api-store-batch`: 20 req/min), validación estricta de claves y 404 estricto sin 405.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
