# Diseño del Sistema: `DESIGN.md`

Este proyecto es un firmware embebido en MicroPython sin interfaz gráfica web ni frontend visual interactivo. El diseño del sistema se centra en el modelo de estados físicos del dispositivo, la temporización de periféricos y el lenguaje visual de señalización mediante LEDs.

## 1. Arquitectura de Estados del Firmware

```
           [ INICIO ]
               │
               ▼
      ( Test de LEDs ) ──► _startup_blink()
               │
               ▼
     ( Conexión Wi-Fi ) ──► Fallback en ALTERNATIVES_AP si falla
               │
               ▼
    ( Inicialización HW ) ──► SPI bus 0 + CC1101 (868.3 MHz)
               │
               ▼
    ( Sincronización RTC ) ──► NTP UDP pool
               │
         ┌─────┴─────────────────────────┐
         ▼                               ▼
 [ CORE 0: Radio & HTTP ]      [ CORE 1: Decodificador ]
  - Polling FIFO CC1101         - Espera batch listo
  - Doble buffer (bufA/bufB)     - Decodifica 6-en-1 / 5-en-1
  - Rotación por tamaño/tiempo   - Agrega métricas climáticas
  - POST HTTP a API REST        - Timeout parcial si faltan datos
  - Animación no bloqueante     - Señala payload completo
```

## 2. Lenguaje Visual de Señalización por LEDs

El sistema utiliza cinco emisores LED para comunicar el estado interno sin requerir monitor serie conectado:

| LED | GPIO | Color | Comportamiento | Significado del Estado |
|---|---|---|---|---|
| **Onboard** | `"LED"` | Verde | Encendido fijo continuo | El microcontrolador RP2040 tiene alimentación y el firmware ha arrancado. |
| **LED ON** | `GPIO15` | Verde | Encendido fijo / Apagado temporal | **Encendido**: El sistema está en el bucle principal a la espera de paquetes de radio. **Apagado**: Se apaga temporalmente al consolidar un paquete completo mientras se procesa y sube. |
| **LED READ** | `GPIO7` | Rojo | Encendido durante petición | Indica que hay una subida HTTP activa (`urequests.post`) hacia la API REST. Se apaga al cerrar el socket. |
| **LED ALT1** | `GPIO13` | Azul | Parpadeo ráfaga alterno | Se activa junto a ALT2 en alternancia rápida al decodificar exitosamente una trama de radio válida. |
| **LED ALT2** | `GPIO14` | Azul | Parpadeo ráfaga alterno | Se activa junto a ALT1 en alternancia rápida al decodificar exitosamente una trama de radio válida. |

### Secuencia de Arranque (`_startup_blink`)
1. **Destello total**: Todos los LEDs externos se encienden durante 200 ms y se apagan 100 ms para comprobar bombillas y conexiones eléctricas.
2. **Escaneo secuencial**: Se enciende y apaga cada LED individualmente (ON -> READ -> ALT1 -> ALT2) durante 200 ms cada uno para verificar la asignación de pines.
3. **Latido de entrada**: Tres destellos rápidos en el LED de latido (si está configurado) y encendido fijo final del LED ON (`GPIO15`).

## 3. Filosofía de No Bloqueo

Para garantizar que el receptor CC1101 no sufra desbordamientos de FIFO de 64 bytes:
- Ninguna animación visual utiliza `time.sleep_ms()` dentro de los bucles de trabajo.
- El servicio de parpadeo de LEDs alternos (`service_blink()`) y el latido (`service_heartbeat()`) funcionan mediante comparaciones de tiempo relativo basadas en `ticks_ms()` y `ticks_diff()`.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
