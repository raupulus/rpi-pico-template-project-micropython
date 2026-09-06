# Protocolo Bresser RF 868 MHz

> **Fuentes**: Implementaciones de referencia `rtl_433` (dispositivos 119 y 172), ingeniería inversa de la comunidad radioaficionada y proyectos de referencia `old_c_project/` y `old_python_project/`.  
> **Fecha de descarga / consulta**: 2026-09-06  
> **Fecha de verificación real**: 2026-09-06 (verificado contra señales RF en vivo de estaciones Bresser 868 MHz)

Documentación oficial destilada del protocolo inalámbrico utilizado por estaciones meteorológicas Bresser en Europa.

## Índice de Documentos

- [`00-fundamentos.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/bresser-protocol/00-fundamentos.md): Modulación física, sincronismo de preámbulo y estructura de trama.
- [`protocolo-6en1.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/bresser-protocol/protocolo-6en1.md): Especificación detallada de tramas de 18 bytes (6-en-1).
- [`protocolo-5en1.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/bresser-protocol/protocolo-5en1.md): Especificación detallada de tramas de 26/27 bytes (5-en-1).
- [`ERRATAS.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/bresser-protocol/ERRATAS.md): Inconsistencias documentadas entre especificaciones públicas y comportamiento real.
- [`LIMITACIONES.md`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/docs/apis/bresser-protocol/LIMITACIONES.md): Límites físicos, periodicidad de transmisión y colisiones de RF.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
