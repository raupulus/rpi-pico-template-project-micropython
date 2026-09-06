# Limitaciones: Protocolo Bresser RF

> **Fuentes**: Datasheet TI CC1101 y especificaciones de radio Bresser.  
> **Fecha de verificación real**: 2026-09-06

## 1. Ausencia de Acuse de Recibo (ACK)
El protocolo opera en transmisión unidireccional por radio sin confirmación de recepción (simplex). La estación exterior emite periódicamente sin saber si hay receptores activos.

## 2. Emisión en Ráfagas y Colisiones
Para mitigar pérdidas en el medio inalámbrico, la estación meteorológica transmite la misma trama 2 o 3 veces en ráfagas rápidas separadas por decenas de milisegundos.
- **Consecuencia**: El receptor debe procesar o descartar duplicados rápidamente para evitar desbordamientos del buffer FIFO.

## 3. Dispersión Temporal de Sensores
En las estaciones Bresser 6-en-1, no todas las mediciones se envían simultáneamente en la misma trama:
- La temperatura y humedad suelen transmitirse en un mensaje.
- El viento o la precipitación pueden alternarse en tramas sucesivas separadas por 12 o 24 segundos.
- **Consecuencia**: El receptor debe mantener un acumulador de estado temporal (`agg`) hasta consolidar un conjunto completo antes de realizar la subida a la API.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
