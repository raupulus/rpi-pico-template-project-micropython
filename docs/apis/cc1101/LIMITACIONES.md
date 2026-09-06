# Limitaciones: TI CC1101

> **Fuentes**: TI CC1101 Datasheet Rev. I.  
> **Fecha de verificación real**: 2026-09-06

## 1. Capacidad del FIFO de Recepción
El FIFO hardware interno de recepción tiene un límite estricto de **64 bytes**.
- A 8.2 kbps, 64 bytes se llenan en aproximadamente 62 milisegundos.
- Si dos paquetes consecutivos de 26 bytes llegan con poco intervalo y la CPU no drena el FIFO en ese margen, se produce indefectiblemente un desbordamiento.

## 2. Deriva de Frecuencia del Cristal Cuarzo
Los módulos comerciales económicos de CC1101 suelen equipar osciladores de 26 MHz con tolerancias de hasta ±20 ppm o más ante cambios térmicos.
- Una deriva de 20 ppm a 868 MHz representa un desplazamiento de más de 17 kHz.
- **Consecuencia**: El ancho de banda de recepción (`MDMCFG4`) no debe ajustarse demasiado estrecho (se recomienda el perfil `'270k'`, aproximadamente 270 kHz) para no perder la señal en exteriores.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
