# Protocolo Bresser 6-en-1 (18 Bytes)

> **Fuentes**: Implementación rtl_433 device 172 y código activo en `Models/WeatherSensor.py`.  
> **Fecha de verificación real**: 2026-09-06

## 1. Estructura de la Trama (18 bytes)

```
Byte 0..1:   Digest de verificación LFSR-16
Byte 2..5:   ID del sensor (32 bits big-endian)
Byte 6:      Nibble alto: Tipo de sensor; Nibble bajo: Canal (bits 0..2) + Flags
Byte 7..9:   Ráfaga y media de viento (invertidos bitwise con XOR 0xFF, BCD)
Byte 10..11: Dirección del viento en grados
Byte 12..14: Lluvia acumulada (invertidos bitwise con XOR 0xFF, BCD 6 dígitos -> x 0.1 mm)
Byte 15..16: Temperatura (BCD de 3 nibbles; raw > 600 indica negativo)
Byte 17:     Humedad relativa en BCD (0..100 %)
```

## 2. Validación de Integridad

Para que una trama de 18 bytes sea considerada válida debe cumplir dos condiciones simultáneas:
1. **Suma modular 256**: La suma de los bytes del índice 2 al 17 con acarreo debe ser estrictamente `0xFF`.
2. **Digest LFSR-16**: El cálculo del LFSR sobre `msg[2:17]` con polinomio generador `0x8810` e inicialización `0x5412` debe igualar a `(msg[0] << 8) | msg[1]`.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
