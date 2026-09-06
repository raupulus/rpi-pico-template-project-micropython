# Erratas y Comportamientos Inesperados: TI CC1101

> **Fuentes**: TI CC1101 Errata Notes y depuración experimental en microcontrolador RP2040.  
> **Fecha de verificación real**: 2026-09-06

## 1. Bit de Overflow en el Registro RXBYTES
- **Problema**: El registro de estado `RXBYTES` (`0x3B | 0xC0`) contiene en los bits 6..0 el número de bytes disponibles, y en el bit 7 (`0x80`) el flag de overflow. Si el bit 7 se activa, el conteo de bytes devuelto en los bits inferiores puede ser erróneo o corrupto.
- **Solución implementada**: Si `rxbytes & 0x80` está activo, se debe descartar el buffer inmediatamente, emitir `SIDLE` seguido de `SFRX` y reingresar a `SRX`.

## 2. Bloqueo de SPI durante calibración automática
- **Problema**: Cuando el sintetizador ejecuta auto-calibración al pasar de IDLE a RX (`MCSM0=0x18`), el pin MISO/SO puede mantenerse en alto varios microsegundos, provocando respuestas corruptas si se leen registros inmediatamente.
- **Solución implementada**: Pequeñas pausas de microsegundos (`sleep_us`) tras strobes de estado.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
