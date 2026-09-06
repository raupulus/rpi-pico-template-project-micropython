# Fundamentos: Protocolo Bresser RF

> **Fuentes**: Implementaciones de referencia `rtl_433` (devices 119 y 172).  
> **Fecha de descarga**: 2026-09-06  
> **Fecha de verificación real**: 2026-09-06 (comprobado con receptor CC1101)

## 1. Capa Física de Radiofrecuencia

- **Banda**: 868 MHz SRD (Short Range Device) en Europa.
- **Frecuencia central típica**: `868.300 MHz` (en algunos modelos 868.350 MHz o 868.000 MHz).
- **Modulación**: 2-FSK (Frequency Shift Keying).
- **Desviación de frecuencia**: ~57.1 kHz.
- **Velocidad de símbolo (Bitrate)**: ~8.21 kbps.
- **Codificación**: NRZ (sin codificación Manchester en el payload).
- **Sincronismo de trama**: Secuencia de preámbulo de unos y ceros alternos (`0xAA`) seguida de palabra de sincronismo (Sync Word) `0x2D 0xD4` (o capturada mediante ventana de sincronismo adaptada).

## 2. Modelos Soportados

1. **Bresser 6-en-1**: Tramas cortas de 18 bytes. Utiliza comprobación de redundancia cíclica basada en un registro de desplazamiento con retroalimentación lineal (LFSR-16) y checksum módulo 256. Emisión en ráfagas cada ~12 segundos.
2. **Bresser 5-en-1**: Tramas largas de 26 bytes (o 27 bytes si se prefija `0xD4`). Utiliza redundancia por paridad invertida bit a bit entre la primera y la segunda mitad del mensaje y checksum de conteo de unos (`popcount`). Emisión en ráfagas cada ~12 o 24 segundos.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
