# Protocolo Bresser 5-en-1 (26 Bytes)

> **Fuentes**: Implementación rtl_433 device 119 y código activo en `Models/WeatherSensor.py`.  
> **Fecha de verificación real**: 2026-09-06

## 1. Estructura de la Trama (26 bytes)

La trama consta de dos mitades simétricas de 13 bytes cada una:

```
Bytes 0..12:   Primera mitad (invertida respecto a la segunda)
Byte 13:       Checksum por conteo de bits 1 (popcount de los bytes 14 a 25)
Byte 14:       ID de la estación (8 bits)
Byte 15:       Tipo de sensor (bits 0..6) y flag de inicio/batería (bit 7)
Bytes 16..17:  Ráfaga de viento y dirección (nibble bajo x 22.5 grados)
Bytes 18..19:  Velocidad media de viento
Bytes 20..21:  Temperatura en BCD
Byte 22:       Humedad relativa en BCD
Bytes 23..24:  Lluvia acumulada en BCD (si type 0x39-0x3B, multiplicar x 2.5)
Byte 25:       Signo de temperatura en el nibble bajo (bit 3 activo indica negativo)
```

## 2. Validación de Integridad

1. **Paridad por XOR invertido**: Para cada índice `col` de 0 a 12:
   ```python
   msg[col] ^ msg[col + 13] == 0xFF
   ```
2. **Checksum de bits**: El conteo total de bits a `1` en los bytes 14 al 25 debe ser igual a `msg[13]`.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
