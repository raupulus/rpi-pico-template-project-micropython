# Comandos y Flujo de Trabajo: `commands.md`

Guía de herramientas, comandos de flasheo y depuración para el desarrollo en MicroPython sobre Raspberry Pi Pico W.

## 1. Configuración del Entorno de Desarrollo

El proyecto no requiere gestores de paquetes como pip ni entornos virtuales pesados en runtime, ya que el código se ejecuta en el intérprete MicroPython del microcontrolador.

### Dependencias de Host recomendadas
- Python 3.10+ en la máquina de desarrollo.
- `mpremote` (herramienta oficial de MicroPython) o `rshell` / `ampy`.
```bash
pip install mpremote
```

## 2. Flasheo y Subida de Archivos

### Método 1: PyCharm (Recomendado con archivo `.run`)
El repositorio incluye la configuración de ejecución [`.run/Flash src.run.xml`](file:///Users/fryntiz/git/rpi-pico-weatherstation-bresser-read-868mhz-cc1101/.run/Flash%20src.run.xml) compatible con el plugin MicroPico / MicroPython de JetBrains:
1. Conectar la Raspberry Pi Pico W por USB.
2. Abrir el proyecto en PyCharm.
3. Ejecutar la configuración **"Flash src"**. Flasheará recursivamente la carpeta `src/` al filesystem de la Pico y abrirá el REPL interactivo.

### Método 2: CLI con `mpremote`
Listar dispositivos conectados:
```bash
mpremote devs
```

Sincronizar todo el contenido de `src/` a la raíz de la placa:
```bash
# Copiar archivos individuales o directorios
mpremote fs cp src/main.py :main.py
mpremote fs cp src/env.py :env.py
mpremote fs cp -r src/Drivers :Drivers
mpremote fs cp -r src/Models :Models
```

Ejecutar un script en la placa sin grabarlo en flash:
```bash
mpremote run src/main.py
```

Abrir la consola interactiva REPL:
```bash
mpremote repl
```
*(Para salir de REPL con mpremote pulsar `Ctrl+]`)*.

### Método 3: Con Thonny IDE
1. Abrir Thonny y seleccionar en la esquina inferior derecha: **MicroPython (Raspberry Pi Pico)**.
2. Subir los archivos de `src/` al dispositivo.
3. Reiniciar con `Ctrl+D` (Soft reset) para ejecutar `main.py`.

## 3. Diagnóstico y Depuración en Tiempo de Ejecución

### Activar trazas completas de radio y decodificación
Editar `src/env.py`:
```python
DEBUG = True
SHOW_ALL_DECODED = True
DECODE_DEBUG = True
```
Y reiniciar el dispositivo. Verás cada byte extraído del FIFO, razones de rechazo (fallo de digest LFSR o paridad) y estados MARCSTATE.

### Modo Búsqueda de Identificadores (Station Discovery)
Para descubrir el ID emitido por una estación nueva:
Editar `src/env.py`:
```python
FIND_STATION_IDS = True
```
El firmware no subirá datos a la API y listará en consola:
```
ID detectado: 336593555  tipo: 1  chan: 0
(hilo2) IDs vistos hasta ahora: [336593555]
```

### Soft Reset por Terminal
En la consola REPL:
```python
import machine
machine.reset()
```

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
