# Calibración y Ajuste del Sistema

## Calibración de la frecuencia del CC1101

La estación Bresser 5-en-1 emite en la banda de 868 MHz. La frecuencia exacta puede variar ligeramente entre unidades. Si hay problemas de recepción:

### Probar frecuencias conocidas

- **868.000 MHz** (`CC1101_FREQ_HZ = 868000000`): frecuencia genérica de la banda ISM europea.
- **868.300 MHz** (`CC1101_FREQ_HZ = 868300000`): frecuencia usada por rtl_433 para Bresser 6-en-1 y en el proyecto C original. **Recomendada como primera opción.**

Ambas se pueden probar alternando el valor en `env.py` y reiniciando.

### Ancho de banda RX

Un ancho de banda más amplio tolera mejor errores de frecuencia del oscilador del CC1101 pero capta más ruido. Uno más estrecho es más selectivo.

| BW configurado | BW real | Cuándo usar |
|---|---|---|
| `'270k'` | ~270.8 kHz | Por defecto, funciona bien con la mayoría de módulos |
| `'250k'` | ~232.1 kHz | Si hay interferencias y la señal es fuerte y limpia |

Si el CC1101 tiene un oscilador de cristal de 26 MHz con poca precisión, puede ser necesario ajustar `CC1101_FREQ_HZ` en ±100 kHz para compensar.

### Desviación de frecuencia

```python
DEVIATN = 0x47   # ~57.1 kHz
```

Este valor está calibrado para Bresser 5/6-en-1 a ~8.2 kbps 2-FSK. Cambiar solo si se sabe que la estación usa una desviación diferente.

---

## Calibración del sensor de temperatura interno del RP2040

El sensor ADC interno del RP2040 es poco preciso (±5°C según datasheet). Su único uso en este proyecto es indicativo (diagnóstico de sobrecalentamiento). Las constantes de corrección en `RpiPico.py`:

```python
INTEGRATED_TEMP_CORRECTION = 27  # Offset de corrección
adc_voltage_correction = 0.706   # Corrección de voltaje
```

Si se necesita mayor precisión para la temperatura de CPU, ajustar `INTEGRATED_TEMP_CORRECTION` hasta que el valor coincida con un termómetro de referencia cerca del chip.

---

## Ajuste del decodificador Bresser

### Distinguir 5-en-1 de 6-en-1

La duda de si la estación emite como 5-en-1 o 6-en-1 se resuelve observando:

1. Activar `DECODE_DEBUG=True` y `SHOW_ALL_DECODED=True`.
2. Observar qué decodificador tiene éxito primero en las tramas recibidas.
3. Una vez confirmado el tipo, poner `FORCE_BRESSER_MODEL='5in1'` o `'6in1'` para evitar intentos innecesarios.

El decodificador intenta siempre primero 6-en-1 (18 bytes) y luego 5-en-1 (26 bytes). Las verificaciones matemáticas (LFSR-16 + suma para 6-en-1; paridad XOR + bitcount para 5-en-1) son lo suficientemente robustas para discriminar.

### Tramas desalineadas

Si `DECODE_DEBUG` muestra "fallo de decodificación" con `len=40` pero la hex parece válida, puede haber un problema de alineación. Probar:

1. Activar `ALLOW_SLIDING_DECODE=True` temporalmente.
2. Observar si el debug muestra `align_offset` con valor distinto de 0.
3. Si siempre desencadena en el mismo offset, ajustar `REQUIRE_D4_FIRST_BYTE` o revisar la configuración del sync word en el driver.

---

## Proceso de descubrimiento del ID de la estación

1. Poner `FIND_STATION_IDS=True`, `DEBUG=True`, `DECODE_DEBUG=False` en `env.py`.
2. Cargar el firmware en la Pico y abrir la consola serie.
3. Sacar la estación meteorológica fuera o acercarla a la antena del CC1101.
4. Esperar 2-3 minutos. La estación emite periódicamente (cada ~14 segundos en Bresser 5-en-1).
5. Observar las líneas `ID detectado:` e `ID candidato:` en la consola.
6. El ID que aparece de forma repetida y con tipo correcto es el de la propia estación.
7. Poner ese ID en `SENSOR_IDS_INC = [<ID>]` y desactivar `FIND_STATION_IDS=False`.

Si hay sensores de vecinos, usar `SENSOR_IDS_EXC` para descartarlos.

### Modo FIND_ID_STRICT

Con `FIND_ID_STRICT=False` (por defecto), en la búsqueda de 5-en-1 solo se exige la paridad XOR. Esto puede producir "ID candidato" falsos. Con `FIND_ID_STRICT=True`, también se exige el checksum de conteo de bits, lo que reduce falsos positivos a costa de poder perder algunos IDs reales si la señal llega con ruido.

---

## Ajuste de LEDs

Los LEDs externos sirven como indicadores visuales sin necesidad de abrir la consola:

- **LED_READ** latiendo lentamente (1Hz): el bucle principal está vivo y el Wi-Fi funciona.
- **LED_READ** fijo durante 1-2s: se está subiendo un payload a la API.
- **LED_ALT1 y LED_ALT2** parpadeando alternamente en ráfaga: se recibió una trama de radio válida.

Si el parpadeo alterno es demasiado rápido o lento para el entorno, ajustar:

```python
LED_ALT_MIN_DELAY_MS = 80   # Mínimo entre alternaciones (ms)
LED_ALT_MAX_DELAY_MS = 250  # Máximo entre alternaciones (ms)
LED_ALT_MIN_BLINKS   = 7    # Número mínimo de alternaciones
LED_ALT_MAX_BLINKS   = 15   # Número máximo de alternaciones
```

---

## Ajuste del intervalo de subida

El firmware sube datos cada vez que agrega un conjunto completo (temp + humedad + viento + lluvia). El intervalo entre subidas depende de la frecuencia de emisión de la estación y del tamaño del lote:

- Bresser 5-en-1 emite aproximadamente cada 14 segundos.
- Un lote de `BATCH_SIZE=50` paquetes a esa frecuencia tardará ~11 minutos en llenarse.
- Con `BATCH_WINDOW_MS=60000` (1 minuto), el lote se procesa al menos cada minuto aunque no esté lleno.

Para subidas más frecuentes: reducir `BATCH_WINDOW_MS`. Para menor tráfico de red: aumentarlo.

---

## Diagnóstico de problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| No se recibe ningún paquete | Frecuencia incorrecta o mal cableado | Verificar pines en `env.py` y `CC1101_FREQ_HZ` |
| Muchos fallos de decodificación | Desalineación de sync o BW incorrecto | Probar `ALLOW_SLIDING_DECODE=True`, cambiar `CC1101_BW_DEFAULT` |
| Se decodifican IDs desconocidos | Sensores de vecinos en la misma frecuencia | Usar `SENSOR_IDS_INC` con el propio ID |
| La API no recibe datos | Wi-Fi no conectado o token inválido | Verificar `AP_NAME`, `AP_PASS`, `API_TOKEN` |
| El firmware se cuelga | Excepción no capturada o FIFO overflow | Activar `DEBUG=True` para ver el error en consola |
| Lluvia siempre 0 | Primera lectura solo establece base | Normal — la segunda lectura ya produce diferencial |
| Temperatura de CPU muy alta | Carcasa sin ventilación o componentes cercanos | El RP2040 puede operar hasta ~85°C, pero encima de ~70°C reducir frecuencia de operación |
