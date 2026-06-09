# Driver CC1101 — `src/Drivers/CC1101.py`

## Descripción

Driver SPI de bajo nivel para el transceptor **Texas Instruments CC1101**. Está optimizado exclusivamente para **recepción (RX)** de tramas Bresser a ~868 MHz con modulación 2-FSK a ~8.2 kbps.

No implementa transmisión (TX) ni funciones de bajo consumo (WOR). Es un subconjunto pragmático de la funcionalidad del CC1101 enfocado en estabilidad y legibilidad.

## Comunicación SPI

El CC1101 usa SPI en modo 0 (CPOL=0, CPHA=0). Baudrate recomendado: **4 MHz** (seguro y probado).

### Tipos de acceso al registro

| Tipo | Byte de comando | Descripción |
|---|---|---|
| Escritura simple | `addr & 0x3F` | Un byte de dirección + un byte de datos |
| Escritura burst | `addr | 0x40` | Un byte de dirección + múltiples bytes de datos |
| Lectura simple | `addr | 0x80` | Un byte de dirección + leer un byte |
| Lectura burst | `addr | 0xC0` | Un byte de dirección + leer múltiples bytes |
| Registro de estado | `addr | 0xC0` (burst bit) | Para registros de solo lectura del CC1101 |
| Command strobe | byte único | Envía comando instantáneo al CC1101 |

### Secuencia CS

```
CS = 1  (idle)
CS = 0  (select)
  → SPI transfer
CS = 1  (deselect)
```

El pin CS requiere un **pull-up de 10 kΩ a 3.3V** por hardware para garantizar nivel alto durante el reset y el arranque del RP2040.

## Registros configurados

### Pines GDO

```python
IOCFG0 = 0x06   # GDO0: assert en inicio de sync, deassert al final del paquete
IOCFG2 = 0x0D   # GDO2: High-Z (sin uso activo por ahora)
```

`GDO0` se usa como señal de "fin de paquete". Su flanco de bajada dispara la IRQ en el Pico.

### Modo de paquete

```python
PKTCTRL1 = 0x00  # Sin comprobación de dirección, sin append de status
PKTCTRL0 = 0x02  # Longitud VARIABLE, CRC desactivado, sin append de status
PKTLEN   = 40    # Longitud máxima de paquete (cubre Bresser 5-en-1 y 6-en-1)
```

En modo longitud variable, el CC1101 espera que el primer byte del payload sea la longitud (L), y lee exactamente L bytes adicionales. El driver devuelve `[L | payload(L)]` sin bytes de status (status no appended).

### Frecuencia

La frecuencia se calcula como:

```
fword = (freq_hz * 2^16) // 26_000_000
FREQ2 = (fword >> 16) & 0xFF
FREQ1 = (fword >> 8)  & 0xFF
FREQ0 =  fword        & 0xFF
```

Por defecto: **868.3 MHz** (`freq_hz = 868_300_000`). Se puede cambiar desde `env.py` con `CC1101_FREQ_HZ`.

### Modulación y velocidad de datos

| Registro | Valor | Efecto |
|---|---|---|
| `MDMCFG4` | `0x0A` + bits BW | DRATE_E=10 → ~8.2 kbps; bits 7:4 = ancho de banda RX |
| `MDMCFG3` | `0x83` | DRATE_M=131 → precisión de la tasa |
| `MDMCFG2` | `0x13` | 2-FSK, sin Manchester, sincronización 16/16 bits |
| `MDMCFG1` | `0x22` | FEC desactivado, preámbulo de 4 bytes |
| `MDMCFG0` | `0xF8` | Espaciado de canal (no crítico para RX) |
| `DEVIATN` | `0x47` | Desviación de frecuencia ~57.1 kHz |

### Ancho de banda RX (perfiles)

El ancho de banda RX se configura en los bits 7:4 de `MDMCFG4` con la fórmula:

```
BW = f_xosc / (8 * (4 + M) * 2^E)    con f_xosc = 26 MHz
```

| Perfil | E | M | BW real | Uso |
|---|---|---|---|---|
| `'270k'` | 1 | 2 | ~270.8 kHz | Por defecto, recomendado |
| `'250k'` | 1 | 3 | ~232.1 kHz | Alternativo (aprox. 250 kHz) |
| `'100k'` | 0 | 3 | ~100.4 kHz | No recomendado (demasiado estrecho) |

El perfil se puede cambiar en caliente con `set_bw_profile(profile)` sin reiniciar el CC1101.

### AGC y compensación de frecuencia

```python
FOCCFG  = 0x16   # Compensación de offset de frecuencia
BSCFG   = 0x6C   # Configuración de sincronización de bit
AGCTRL2 = 0x07   # AGC: ganancia máxima
AGCTRL1 = 0x40   # AGC: umbral de ganancia relativa
AGCTRL0 = 0x91   # AGC: histeresis y tiempo de estabilización
```

### Front-end y calibración

```python
FREND1  = 0xB6
FREND0  = 0x10
FSCAL3  = 0xE9
FSCAL2  = 0x2A
FSCAL1  = 0x00
FSCAL0  = 0x1F
TEST2   = 0x81
TEST1   = 0x31
TEST0   = 0x09
```

Estos valores provienen de TI SmartRF Studio y son conocidos por funcionar con sensores Bresser a 868 MHz.

### Máquina de estados (MCSM)

```python
MCSM0 = 0x18   # Auto-calibración al entrar en RX/TX desde IDLE
MCSM1 = 0x0C   # Tras recibir paquete: volver a RX automáticamente
```

Con `MCSM1=0x0C`, el CC1101 vuelve a RX automáticamente después de cada paquete recibido, sin necesidad de comandos adicionales.

## API pública del driver

### `reset()`
Secuencia de reset por CS + strobe `SRES`. Inicializa el perfil de BW por defecto.

### `configure_bresser(pkt_len, strict_sync, bw_profile, freq_hz)`
Configura el CC1101 completo para recepción Bresser. Envía IDLE → flush FIFOs → escribe todos los registros → calibra → entra en RX.

### `enter_rx()`
```
SIDLE → SFRX (flush RX FIFO) → SRX
```
Lleva el radio a estado RX de forma limpia.

### `ensure_rx()`
Lee el MARCSTATE. Si hay overflow (0x11) hace flush y vuelve a RX. Si no está en RX (0x0D) intenta volver a RX sin flush. Método de recuperación tolerante a fallos.

### `read_packet(timeout_ms)`
Lógica de lectura de paquete desde el FIFO, soportando tres modos del CC1101:

**Modo longitud fija** (`PKTCTRL0 & 0x03 == 0`): Espera exactamente `PKTLEN` bytes (+ 2 status si `APPEND_STATUS`).

**Modo longitud variable** (`PKTCTRL0 & 0x03 == 1`): Lee el byte de longitud L, valida `1 ≤ L ≤ PKTLEN`, luego espera L bytes más (+ 2 status).

**Modo infinito** (`PKTCTRL0 & 0x03 == 2`): Lee lo que haya disponible en el FIFO hasta el timeout.

En todos los casos, si el bit de overflow está activo en RXBYTES (bit 7), se hace `SIDLE + SFRX + SRX` antes de reintentar.

### `get_rssi_dbm()`
```
rssi_reg >= 128  →  (rssi_reg - 256) / 2.0 - 74
rssi_reg < 128   →   rssi_reg / 2.0 - 74
```
Conversión del registro RSSI a dBm según datasheet del CC1101.

### `get_status()`
Devuelve un diccionario con: `partnum`, `version`, `marcstate`, `rssi`, `rssi_dbm`, `rxbytes`, `overflow`, `pklen` y los registros de demodulación principales. Útil para diagnóstico en producción.

### `set_bw_profile(profile)`
Modifica solo los bits CHANBW de MDMCFG4, recalibra (`SCAL`) y vuelve a RX. No requiere reconfigurar el radio completo.

## Command strobes

| Strobe | Código | Efecto |
|---|---|---|
| `SRES` | 0x30 | Reset completo del CC1101 |
| `SRX` | 0x34 | Entrar en modo RX |
| `STX` | 0x35 | Entrar en modo TX |
| `SIDLE` | 0x36 | Volver a IDLE |
| `SFRX` | 0x3A | Flush RX FIFO |
| `SFTX` | 0x3B | Flush TX FIFO |
| `SCAL` | 0x33 | Calibrar el sintetizador de frecuencia |

## MARCSTATE — estados de la máquina

| Valor | Estado |
|---|---|
| 0x0D | RX (recibiendo) |
| 0x0F | RX_END (paquete completo en FIFO) |
| 0x11 | RXFIFO_OVERFLOW (overflow, hay que hacer flush) |
| 0x01 | IDLE |

## Nota sobre la palabra de sincronización

El código incluye comentarios sobre dos configuraciones de sync posibles:

- **`0x2D 0xD4`** (strict): Sincronización exacta usada en el proyecto C original. Requiere que el preámbulo y sync word estén perfectamente alineados.
- **`0xAA 0x2D`** (lax): Truco para capturar el `0xD4` como primer byte de payload tras el sync `0xAA 0x2D`. Esto añade un byte al principio del paquete recibido.

Actualmente el código usa **modo longitud variable (PKTCTRL0=0x02)** con `PKTLEN=40`, sin sync word explícita en los registros SYNC1/SYNC0 (están comentados). El decodificador maneja la alineación por software.
