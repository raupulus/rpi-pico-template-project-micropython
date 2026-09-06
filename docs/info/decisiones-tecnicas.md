# Decisiones Técnicas y Arquitectura: `decisiones-tecnicas.md`

Este documento registra las decisiones técnicas deliberadas tomadas en el diseño del firmware para Raspberry Pi Pico W y transceptor CC1101, así como los motivos que las respaldan para evitar cambios o "refactorizaciones" perjudiciales.

---

## 1. Arquitectura de Dos Hilos (`_thread`) en lugar de `asyncio`

### Decisión
Utilizar los dos núcleos físicos del microcontrolador RP2040 asignando el Core 0 al bombeo constante de radio / subida HTTP, y el Core 1 al procesamiento matemático de tramas mediante el módulo nativo `_thread`.

### Motivo
- La decodificación Bresser de tramas con ventanas deslizantes, cálculo de LFSR-16 en bucle de software y desempaquetado de nibbles BCD consume decenas de milisegundos de CPU.
- Si esto se realizase en un único hilo cooperativo con `uasyncio`, la ejecución de CPU bloquearía la atención del FIFO del CC1101. Como el FIFO del CC1101 tiene solo 64 bytes de capacidad y las ráfagas emiten a 8.2 kbps, cualquier retardo prolongado provoca desbordamientos (`MARCSTATE=0x11`) y pérdidas irrecuperables de paquetes.
- El Core 1 opera de forma aislada procesando lotes ya volcados en memoria, mientras el Core 0 se mantiene libre para drenar el hardware.

---

## 2. Doble Buffer Preasignado (`bufA` / `bufB`)

### Decisión
Preasignar al arranque dos matrices estáticas de objetos `bytearray` fijos (`BATCH_SIZE` elementos de tamaño `PKT_LEN_BUF`), alternando entre ambos mediante índices.

### Motivo
- MicroPython implementa un recolector de basura de tipo Stop-The-World sobre una memoria heap contigua de ~200 KB.
- Crear y destruir dinámicamente objetos `bytes` o listas dentro de un bucle de alta velocidad que drena paquetes genera una fragmentación severa del heap. Esto fuerza ejecuciones frecuentes y prolongadas de `gc.collect()`, durante las cuales el microcontrolador no responde a eventos de radio.
- Al preasignar los buffers, la copia de datos desde el FIFO se realiza mediante slicing sobre memoria existente sin provocar asignaciones dinámicas.

---

## 3. Modo Longitud Variable (`PKTCTRL0 = 0x02`) con Límite `PKTLEN = 40`

### Decisión
Configurar el CC1101 en modo longitud variable (`PKTCTRL0=0x02`) con un tamaño máximo en `PKTLEN=40`, en vez de modo longitud fija.

### Motivo
- Las estaciones Bresser 6-en-1 emiten paquetes de 18 bytes útiles, mientras que las estaciones Bresser 5-en-1 transmiten 26 bytes (o 27 bytes si se incluye el byte de sincronismo prefijado `0xD4`).
- El modo longitud fija obligaría a truncar los paquetes largos de 5-en-1 o a forzar lecturas de bytes basura en los paquetes cortos de 6-en-1.
- El modo variable permite que el primer byte extraído determine la longitud esperada por hardware, admitiendo la convivencia de ambos protocolos en el mismo receptor.

---

## 4. Desacoplamiento de Interrupción Hardware con `micropython.schedule`

### Decisión
La rutina de servicio de interrupción (ISR) en el pin `GDO0` (`_gdo0_irq`) no ejecuta ninguna transacción SPI, sino que aplica un debounce y delega la ejecución al bucle de MicroPython mediante `micropython.schedule(_on_gdo0_scheduled)`.

### Motivo
- En MicroPython sobre RP2040, las ISRs hardware se ejecutan bajo restricciones críticas: no pueden asignar memoria en el heap, no deben durar más de unos microsegundos y las operaciones complejas de bus (como SPI) pueden provocar bloqueos de hardware o corrupciones de estado si coinciden con otra transacción.
- La planificación con `micropython.schedule` aplaza la lectura SPI de forma segura al contexto de ejecución normal del intérprete.

---

## 5. Algoritmo de Zona Horaria Española Peninsular en Código Embebido

### Decisión
Implementar un cálculo directo por reglas de calendario para el horario de verano (`Europe/Madrid`, último domingo de marzo y octubre) dentro de `RpiPico.is_dst_europe_madrid`.

### Motivo
- MicroPython no incluye la base de datos `zoneinfo` ni `pytz` debido a restricciones de memoria flash y RAM.
- La Raspberry Pi Pico W obtiene la hora UTC desde servidores NTP. Para registrar o presentar la hora local correcta en logs sin depender de llamadas a servicios web de geolocalización, una función de cálculo matemático de 15 líneas proporciona la hora local exacta sin sobrecoste.

---

## 6. Estrategia de Resiliencia 24/7 y Tolerancia a Fallos

### Decisión
Incorporar Watchdog Hardware (`machine.WDT` a 8.0 segundos), reconexión Wi-Fi acotada (`max_retries=3`), timeout global en sockets (6.0 segundos), recolección periódica de basura cada 30 segundos y supervisión mutua entre núcleos (Core 0 resetea si Core 1 no da pulso en >120 segundos).

### Motivo
- En despliegues remotos desatendidos (ej: tejados, mástiles o altillos), un bloqueo por caída temporal del router doméstico, socket colgado en handshake TLS o desbordamiento silencioso del hilo secundario exigiría apagar y encender manualmente el transformador eléctrico.
- Con timeout de sockets a 6.0s y WDT a 8.0s, los fallos de red generan excepciones capturadas de forma limpia antes de que venza el perro guardián.
- La reconexión Wi-Fi no es un bucle infinito bloqueante; desiste y permite continuar la operativa de radio local y alimentación del watchdog.
- Si ocurre un congelamiento real o el Core 1 fallece silenciosamente, el hardware reinicia automáticamente el sistema en segundos.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
