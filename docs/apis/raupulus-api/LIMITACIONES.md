# Limitaciones: API Raupulus WeatherStation

> **Fuentes**: Arquitectura de endpoints de `api.raupulus.dev`.  
> **Fecha de verificación real**: 2026-09-06

## 1. Conexiones simultáneas y Handshake TLS
La Raspberry Pi Pico W utiliza el procesador RP2040 con soporte software para TLS (mbedTLS embebido en MicroPython).
- Cada negociación de apretón de manos TLS (handshake) consume entre 500 ms y 1500 ms de procesamiento intensivo de CPU.
- **Consecuencia**: No se deben realizar llamadas HTTP con una frecuencia superior a la consolidación de lotes (mínimo ~30-60 segundos por ciclo).

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
