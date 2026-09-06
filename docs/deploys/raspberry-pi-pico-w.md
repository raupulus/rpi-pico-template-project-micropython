# Despliegue: Raspberry Pi Pico W con MicroPython

Guía de despliegue en limpio para la Raspberry Pi Pico W.

## 1. Requisitos Previos

- Tarjeta Raspberry Pi Pico W (o Pico 2 W).
- Cable micro-USB con líneas de datos habilitadas.
- Firmware oficial de MicroPython (versión 1.28 o superior) en formato `.uf2` descargable desde [micropython.org](https://micropython.org/download/rp2-pico-w/).

## 2. Instalación de MicroPython

1. Mantener pulsado el botón blanco **BOOTSEL** de la Raspberry Pi Pico W mientras se conecta el cable micro-USB al ordenador.
2. Soltar el botón una vez que la placa aparezca como una unidad de almacenamiento masivo USB llamada `RPI-RP2`.
3. Copiar el archivo descargado `rp2-pico-w-YYYYMMDD-v1.XX.X.uf2` en la raíz de la unidad `RPI-RP2`.
4. La unidad se desmontará de forma automática y el microcontrolador se reiniciará ejecutando el intérprete MicroPython.

## 3. Carga del Firmware del Proyecto

1. Clonar el repositorio localmente.
2. Crear el archivo `src/env.py` a partir de `src/.env.example.py` con las credenciales Wi-Fi reales y el token de la API REST.
3. Copiar los archivos a la raíz de la placa utilizando `mpremote`:
   ```bash
   mpremote fs cp src/main.py :main.py
   mpremote fs cp src/env.py :env.py
   mpremote fs cp -r src/Drivers :Drivers
   mpremote fs cp -r src/Models :Models
   ```
4. Reiniciar la placa mediante desconexión/reconexión USB o enviando un reset por REPL:
   ```bash
   mpremote soft-reset
   ```

## 4. Verificación de Funcionamiento

- Comprobar que el **LED Onboard** queda encendido fijo (alimentación OK).
- Comprobar la secuencia inicial de comprobación de los cuatro LEDs exteriores (`_startup_blink`).
- El LED verde **ON** (`GP15`) debe permanecer encendido fijo esperando tramas.
- Al llegar emisiones de la estación meteorológica Bresser, los dos LEDs azules (`GP13` y `GP14`) deben parpadear alternadamente.
- Al consolidar un lote de lectura, el LED rojo **READ** (`GP7`) se encenderá unos instantes durante el envío HTTP y se apagará tras confirmarse la respuesta 201.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
