# Erratas y Compatibilidad: API Raupulus WeatherStation (V2)

> **Fuentes**: Verificación de contrato oficial API V2.  
> **Fecha de verificación real**: 2026-09-06

## 1. Validación estricta de claves en lote multi-sensor
- **Comportamiento previo (V1)**: Claves no reconocidas se ignoraban en silencio.
- **Comportamiento V2**: El backend rechaza con `422` cualquier clave dentro del bloque `data` que no corresponda con los nombres exactos del catálogo (`temperature`, `humidity`, `wind`, `wind_direction`, `rain`, `light`, `air_quality`, `eco2`, `tvoc`, `lightning`).
- **Solución implementada**: `Api.py` mapea internamente las variables del decodificador únicamente a las claves permitidas en el catálogo V2.

## 2. Requisito de campo `moisture` en el sensor `rain`
- **Comportamiento V2**: La regla de validación de `rains` exige que el campo `moisture` esté presente y sea numérico. Dado que los sensores Bresser 5-en-1 / 6-en-1 estándar no disponen de sonda de humedad de suelo, el firmware envía `moisture: 0.0` por defecto para superar la validación.

## 3. Direcciones cardinales en `wind_direction`
- **Comportamiento V2**: Requiere `direction` (cadena de texto con rumbo cardinal, máx. 10 caracteres) además de `grades` (grados 0–360).
- **Solución implementada**: El firmware implementa una función pura [`degrees_to_cardinal()`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/src/Models/Api.py) que discretiza los grados en los 16 sectores estándar ("N", "NNE", "NE", etc.).

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
