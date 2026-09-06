# Fundamentos: Texas Instruments CC1101

> **Fuentes**: TI CC1101 Datasheet Rev. I.  
> **Fecha de verificación real**: 2026-09-06

## 1. Interfaz Serie SPI

El chip opera como esclavo SPI en Modo 0 (CPOL=0, CPHA=0). Soporta frecuencias de reloj hasta 10 MHz (4 MHz utilizado en este firmware).

### Formato del Byte de Cabecera SPI
- **Bit 7**: R/W (0 = Escritura, 1 = Lectura).
- **Bit 6**: Burst access (0 = Byte individual, 1 = Ráfaga continua).
- **Bits 5..0**: Dirección de registro de configuración (0x00 a 0x2E) o comando Strobe (0x30 a 0x3D).

## 2. Máquina de Estados (MARCSTATE)

El estado del radio se consulta leyendo el registro de estado `MARCSTATE` (`0x35 | 0xC0`):
- `0x01`: **IDLE** (reposo).
- `0x0D`: **RX** (escuchando o recibiendo en el canal).
- `0x0F`: **RX_END** (fin de paquete en FIFO).
- `0x11`: **RXFIFO_OVERFLOW** (desbordamiento; el radio no recibe nada más hasta que se ejecute `SIDLE` y `SFRX`).

## 3. Comandos de Strobe Principales

- `0x30` (`SRES`): Reset por software del chip.
- `0x34` (`SRX`): Habilitar recepción (RX).
- `0x36` (`SIDLE`): Forzar estado de reposo (IDLE).
- `0x3A` (`SFRX`): Vaciar buffer FIFO de recepción.
- `0x33` (`SCAL`): Calibrar el sintetizador de frecuencia.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
