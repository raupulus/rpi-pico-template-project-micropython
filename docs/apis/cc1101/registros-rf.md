# Registros RF para Bresser 868.3 MHz

> **Fuentes**: SmartRF Studio de Texas Instruments y calibraciones validadas en hardware.  
> **Fecha de verificación real**: 2026-09-06

## Configuración de Registros Clave

| Registro | Dirección | Valor | Descripción |
|---|---|---|---|
| `IOCFG0` | `0x02` | `0x06` | Salida GDO0: activa en sincronismo, deassert al finalizar paquete |
| `PKTCTRL0` | `0x08` | `0x02` | Longitud variable de paquete, CRC interno desactivado |
| `PKTLEN` | `0x06` | `40` | Longitud máxima esperada en modo variable |
| `FREQ2` | `0x0D` | `0x21` | Frecuencia central 868.3 MHz (byte 2) |
| `FREQ1` | `0x0E` | `0x65` | Frecuencia central 868.3 MHz (byte 1) |
| `FREQ0` | `0x0F` | `0x6A` | Frecuencia central 868.3 MHz (byte 0) |
| `MDMCFG4` | `0x10` | `0x2A` / `0x3A` | Ancho de banda RX (bits 7..4) y exponente de tasa de símbolo (bits 3..0) |
| `MDMCFG3` | `0x11` | `0x83` | Mantisa de tasa de símbolo (~8.2 kbps) |
| `MDMCFG2` | `0x12` | `0x13` | Modulación 2-FSK, detección de sync 16/16 bits |
| `MDMCFG1` | `0x13` | `0x22` | Preámbulo de 4 bytes, sin FEC |
| `DEVIATN` | `0x15` | `0x47` | Desviación de frecuencia ~57.1 kHz |
| `MCSM1` | `0x17` | `0x0C` | Al terminar de recibir un paquete, retornar automáticamente a RX |
| `MCSM0` | `0x18` | `0x18` | Calibración automática del sintetizador al salir de IDLE |

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
