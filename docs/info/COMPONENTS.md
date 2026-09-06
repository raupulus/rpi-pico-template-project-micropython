# Componentes Hardware: `COMPONENTS.md`

Inventario exhaustivo y esquema de interconexión eléctrica de los componentes que integran la estación receptora.

## 1. Módulos y Placas Principales

| Componente | Fabricante / Chip | Función | Parámetros Clave |
|---|---|---|---|
| **Raspberry Pi Pico W** | Raspberry Pi / RP2040 + Infineon CYW43439 | Unidad de procesamiento principal y enlace Wi-Fi | Dual Core ARM Cortex-M0+ a 133 MHz, 264 KB SRAM, Wi-Fi 802.11n 2.4 GHz |
| **Transceptor CC1101** | Texas Instruments / Módulo genérico 868 MHz | Receptor sub-1GHz para señales FSK/ASK | Frecuencia 868.3 MHz, SPI hasta 10 MHz (configurado a 4 MHz), FIFO de 64 bytes |
| **Estación Bresser** | Bresser GmbH (modelos 5-en-1 / 6-en-1) | Emisor remoto de variables ambientales | Modulación 2-FSK, banda 868 MHz, periodicidad de emisión ~12s - 24s |

## 2. Mapa de Conexiones Físicas (Pinout)

### Conector SPI del CC1101 a Raspberry Pi Pico W
```
  CC1101 (Módulo)             Raspberry Pi Pico W (Pinout RP2040)
┌─────────────────┐          ┌───────────────────────────────────┐
│ Pin 1: VCC      │ ───────► │ Pin 36: 3V3(OUT) (3.3V DC)        │
│ Pin 2: GND      │ ───────► │ Pin 38: GND (Masa común)          │
│ Pin 3: MOSI/SI  │ ───────► │ Pin 25: GP19 (SPI0 TX)            │
│ Pin 4: SCLK/SCK │ ───────► │ Pin 24: GP18 (SPI0 SCK)           │
│ Pin 5: MISO/SO  │ ───────► │ Pin 21: GP16 (SPI0 RX)            │
│ Pin 6: GDO2     │ ───────► │ Pin 27: GP21 (Opcional)           │
│ Pin 7: GDO0     │ ───────► │ Pin 26: GP20 (IRQ fin de paquete) │
│ Pin 8: CSN/CS   │ ───────► │ Pin 22: GP17 (SPI0 CSn)           │
└─────────────────┘          └───────────────────────────────────┘
                                      ▲
                                      │ (Resistencia 10 kΩ pull-up a 3.3V)
```

> [!IMPORTANT]
> Es estrictamente obligatorio soldar o colocar una resistencia física de **10 kΩ Pull-Up** entre el pin `CSN` (GP17) y la línea de `3.3V` (Pin 36). Durante los reinicios del RP2040, las líneas GPIO flotan en alta impedancia; sin esta resistencia, el CC1101 entra en estados anómalos o bloquea el bus.

### Indicadores LED Externos

Cada LED exterior cuenta con su respectiva resistencia limitadora en serie (típicamente 220 Ω a 330 Ω hacia masa):

| Indicador | Color | Ánodo (GPIO Pico W) | Cátodo |
|---|---|---|---|
| LED ON (Bucle Activo) | Verde | Pin 20: `GP15` | GND vía resistencia 220 Ω |
| LED READ (Envío HTTP) | Rojo | Pin 10: `GP7` | GND vía resistencia 220 Ω |
| LED ALT1 (Recepción 1) | Azul | Pin 17: `GP13` | GND vía resistencia 220 Ω |
| LED ALT2 (Recepción 2) | Azul | Pin 19: `GP14` | GND vía resistencia 220 Ω |

## 3. Periféricos Opcionales / Futuros

- **Botón de Reset Hardware**: Puente directo entre el pin `RUN` (Pin 30 de la placa) y `GND` (Pin 28) mediante pulsador normalmente abierto.
- **Botón de Usuario 1**: `GP2` preparado con pull-up interno para interacción con pantalla LCD/OLED.
- **Entrada Analógica Batería**: `GP28` (ADC2) mediante divisor resistivo de tensión 1/2 para baterías LiPo de 3.7V - 4.2V.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
