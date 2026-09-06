import gc
from time import sleep_ms, ticks_ms, ticks_diff
from machine import Pin
import micropython
micropython.alloc_emergency_exception_buf(100)
import urandom
import _thread
from Models.Api import Api
from Models.RpiPico import RpiPico
from Models.WeatherSensor import WeatherSensor

# Importo variables de entorno
import env

# Habilito recolector de basura
gc.enable()

DEBUG = env.DEBUG

# Flags de conectividad y API
WIFI_ENABLED = bool(getattr(env, 'WIFI_ENABLED', True))
API_ENABLED  = bool(getattr(env, 'API_ENABLED', True))

# Rpi Pico Model Instance
# Si WIFI_ENABLED=False se instancia sin credenciales para no intentar conectar
if WIFI_ENABLED:
    rpi = RpiPico(ssid=env.AP_NAME, password=env.AP_PASS, debug=DEBUG,
                         alternatives_ap=env.ALTERNATIVES_AP, hostname=env.HOSTNAME)
else:
    rpi = RpiPico(ssid=None, password=None, debug=DEBUG,
                         alternatives_ap=[], hostname=env.HOSTNAME)
    if DEBUG:
        print('WIFI_ENABLED=False — sin conexión inalámbrica')

# LED integrado encendido al iniciar (indica energía)
led_onboard = None
if hasattr(env, 'ENABLE_ONBOARD_LED') and env.ENABLE_ONBOARD_LED:
    try:
        led_onboard = Pin("LED", Pin.OUT)
        led_onboard.value(1)
    except Exception as e:
        if DEBUG:
            print('No se pudo encender LED integrado:', e)

# Inicializar pines para LEDs externos desde env
led_on   = None   # GPIO15 verde: bucle principal activo / esperando datos
led_read = None   # GPIO7  rojo:  subida a API en curso
led_alt1 = None   # GPIO13 azul:  parpadeo alterno al decodificar
led_alt2 = None   # GPIO14 azul:  parpadeo alterno al decodificar
try:
    if hasattr(env, 'LED_ON_PIN') and isinstance(env.LED_ON_PIN, int) and env.LED_ON_PIN >= 0:
        led_on = Pin(env.LED_ON_PIN, Pin.OUT)
        led_on.value(1)
        sleep_ms(300)
        led_on.value(0)
    if hasattr(env, 'LED_READ_PIN') and isinstance(env.LED_READ_PIN, int) and env.LED_READ_PIN >= 0:
        led_read = Pin(env.LED_READ_PIN, Pin.OUT)
        led_read.value(1)
        sleep_ms(300)
        led_read.value(0)
    if hasattr(env, 'LED_ALT1_PIN') and isinstance(env.LED_ALT1_PIN, int) and env.LED_ALT1_PIN >= 0:
        led_alt1 = Pin(env.LED_ALT1_PIN, Pin.OUT)
        led_alt1.value(1)
        sleep_ms(300)
        led_alt1.value(0)
    if hasattr(env, 'LED_ALT2_PIN') and isinstance(env.LED_ALT2_PIN, int) and env.LED_ALT2_PIN >= 0:
        led_alt2 = Pin(env.LED_ALT2_PIN, Pin.OUT)
        led_alt2.value(1)
        sleep_ms(300)
        led_alt2.value(0)
except Exception as e:
    if DEBUG:
        print('Error inicializando LEDs externos:', e)

# LED_ON (GPIO15): indicador de bucle activo — se mantiene encendido de forma FIJA
# mientras el sistema espera datos. Se apaga cuando llegan datos y se enciende tras subir.
# NO se usa para heartbeat (parpadeo), ese rol cae al LED integrado.

# Heartbeat desactivado: led_onboard debe permanecer siempre encendido (indicador de energía),
# y led_on (GPIO15) es indicador fijo de bucle activo — ninguno debe parpadear.
heartbeat_led = None

# Intervalo de parpadeo del heartbeat
HEARTBEAT_MS = getattr(env, 'LED_HEARTBEAT_MS', 1000)
heartbeat_next_ms = ticks_ms() + HEARTBEAT_MS
heartbeat_state = 0

# Flag para indicar si hay subida a API en curso
upload_in_progress = False

if DEBUG:
    try:
        print('LEDs configurados -> ON:', bool(led_on), 'READ:', bool(led_read), 'ALT1:', bool(led_alt1), 'ALT2:', bool(led_alt2), 'ONBOARD:', bool(led_onboard))
        print('Heartbeat desactivado — led_onboard=fijo encendido, led_on=fijo bucle activo')
    except Exception:
        pass


# Almacena la información de registros recibidos agrupados por ID de estación.
weatherdatas = []

# Patrón de inicio para confirmar que todos los LEDs externos funcionan.
# Enciende cada uno en secuencia para que el usuario pueda verificar el cableado.
def _startup_blink():
    # 1) Encender todos simultáneamente 200ms (prueba de hardware rápida)
    for pin in (led_on, led_read, led_alt1, led_alt2):
        try:
            if pin is not None:
                pin.value(1)
        except Exception:
            pass
    sleep_ms(200)
    for pin in (led_on, led_read, led_alt1, led_alt2):
        try:
            if pin is not None:
                pin.value(0)
        except Exception:
            pass
    sleep_ms(100)

    # 2) Recorrer cada LED uno a uno para identificarlos
    for pin in (led_on, led_read, led_alt1, led_alt2):
        try:
            if pin is not None:
                pin.value(1)
                sleep_ms(200)
                pin.value(0)
                sleep_ms(100)
        except Exception:
            pass

    # 3) Parpadeo triple del heartbeat para confirmar que el bucle está activo
    if heartbeat_led is not None:
        try:
            for _ in range(3):
                heartbeat_led.value(1)
                sleep_ms(120)
                heartbeat_led.value(0)
                sleep_ms(120)
        except Exception:
            pass

    # 4) Encender led_on para indicar que el sistema entra en el bucle principal
    if led_on is not None:
        try:
            led_on.value(1)
        except Exception:
            pass

sleep_ms(100)
_startup_blink()

# Debug para mostrar el estado del wifi
if DEBUG:
    rpi.wifi_debug()

    # Ejemplo Mostrando temperatura de cpu tras 5 lecturas (+1 al instanciar modelo)
    print('Leyendo temperatura por 1a vez:', str(rpi.get_cpu_temperature()))
    sleep_ms(100)
    print('Leyendo temperatura por 2a vez:', str(rpi.get_cpu_temperature()))
    sleep_ms(100)
    print('Leyendo temperatura por 3a vez:', str(rpi.get_cpu_temperature()))
    sleep_ms(100)
    print('Leyendo temperatura por 4a vez:', str(rpi.get_cpu_temperature()))
    sleep_ms(100)
    print('Leyendo temperatura por 5a vez:', str(rpi.get_cpu_temperature()))
    sleep_ms(100)
    print('Mostrando estadisticas de temperatura para CPU:', str(rpi.get_cpu_temperature_stats()))

    sleep_ms(100)

# Instanciando SPI en bus 0.
spi0 = rpi.set_spi(env.CC1101_SCLK, env.CC1101_MOSI, env.CC1101_MISO, env.CC1101_CS, env.CC1101_SPI_BUS, env.CC1101_BAUDRATE)

sleep_ms(100)

# Inicializar receptor CC1101 si está habilitado en env
ws = None
if hasattr(env, 'ENABLE_CC1101') and env.ENABLE_CC1101 and spi0:
    try:
        cs_pin = rpi.get_spi_cs(env.CC1101_SPI_BUS)
        ws = WeatherSensor(spi=spi0, cs=cs_pin, gdo0=env.CC1101_GDO0, gdo2=env.CC1101_GDO2, debug=DEBUG)
        if ws.begin(pkt_len=env.CC1101_PKT_LEN):
            if DEBUG:
                print('CC1101 inicializado correctamente')
        else:
            if DEBUG:
                print('Fallo al inicializar CC1101')
            ws = None
    except Exception as e:
        if DEBUG:
            print('Error al preparar CC1101:', e)
        ws = None

# Ejemplo instanciando I2C en bus 0.
#i2c0 = rpi.set_i2c(20, 21, 0, 400000)
#address = 0x03 # Dirección de un dispositivo i2c
# Ya podemos usar nuestro sensor con la dirección almacenada en "address"

# Ejemplo escaneando todos los dispositivos encontrados por I2C.
#print('Dispositivos encontrados por I2C:', i2c0.scan())

# Ejemplo asociando un callback al recibir +3.3v en el gpio 2
#rpi.set_callback_to_pin(2, "LOW", tu_callback)
#rpi.set_callback_to_pin(2, lambda p: print("Se ejecuta el callback"), "LOW")

# Ejemplo leyendo batería externa (¡Cuidado! usa divisor de tensión, max 3,3v)
#rpi.set_external_battery(28)
#rpi.read_external_battery()

sleep_ms(200)

# Preparo la instancia para la comunicación con la API
api = Api(controller=rpi, url=env.API_URL, path=env.API_PATH,
          token=env.API_TOKEN, device_id=env.DEVICE_ID, debug=env.DEBUG)


# Intento sincronizar reloj RTC (solo si hay Wi-Fi)
sleep_ms(1000)
if WIFI_ENABLED:
    if env.DEBUG:
        print('Intentando Obtener hora RTC de la API')
    rpi.sync_rtc_time()
elif env.DEBUG:
    print('WIFI_ENABLED=False — saltar sincronización RTC')

# Pausa preventiva al desarrollar (al usar usar dos hilos puede ahorrar tiempo
# por bloqueos de hardware ante errores)
sleep_ms(2000)

def urandint(a: int, b: int) -> int:
    """randint compatible con MicroPython, preferiblemente usando urandom."""
    try:
        return urandom.randint(a, b)
    except AttributeError:
        # Fallback simple con getrandbits
        span = b - a + 1
        if span <= 0:
            return a
        val = urandom.getrandbits(16) % span
        return a + val


# ---------------- Recepción por eventos (GDO0) ----------------
# Último mensaje válido decodificado y marca de tiempo
last_valid_decoded = None
last_valid_rx_ms = 0

# Último dato subido para evitar duplicados
last_uploaded_rx_ms = 0

# Próxima comprobación de subida (cada minuto)
UPLOAD_INTERVAL_MS = 1 * 60 * 1000
next_upload_ms = ticks_ms() + UPLOAD_INTERVAL_MS

# Flag para evitar programar múltiples handlers simultáneamente
_schedule_pending = False

# Mantener referencia al pin con IRQ para evitar GC
gdo0_pin = None
irq_setup_done = False

# Debounce simple para GDO0 y control de colisiones de schedule
last_irq_ms = 0
MIN_IRQ_INTERVAL_MS = 50
last_sched_fail_ms = 0
MIN_SCHED_LOG_INTERVAL_MS = 1000

# Estado de parpadeo diferido (no bloquear dentro de schedule)
blink_remaining = 0
blink_state = 0
blink_next_at_ms = 0


def schedule_random_blink():
    """Programa un parpadeo alterno (no bloqueante) entre 7-15 veces."""
    global blink_remaining, blink_state, blink_next_at_ms
    if not (led_alt1 and led_alt2):
        return
    n = urandint(getattr(env, 'LED_ALT_MIN_BLINKS', 7), getattr(env, 'LED_ALT_MAX_BLINKS', 15))
    # Cada iteración alterna el estado, por lo que n alternancias bastan
    blink_remaining = n
    blink_state = 0
    dmin = getattr(env, 'LED_ALT_MIN_DELAY_MS', 80)
    dmax = getattr(env, 'LED_ALT_MAX_DELAY_MS', 250)
    blink_next_at_ms = ticks_ms() + urandint(dmin, dmax)


def service_blink():
    """Realiza un paso del parpadeo si toca, sin bloquear."""
    global blink_remaining, blink_state, blink_next_at_ms
    if blink_remaining <= 0 or not (led_alt1 and led_alt2):
        return
    now = ticks_ms()
    if ticks_diff(now, blink_next_at_ms) >= 0:
        # Alterna LEDs
        blink_state ^= 1
        try:
            led_alt1.value(blink_state)
            led_alt2.value(1 - blink_state)
        except Exception:
            pass
        blink_remaining -= 1
        if blink_remaining <= 0:
            # Apaga ambos al finalizar
            try:
                led_alt1.value(0)
                led_alt2.value(0)
            except Exception:
                pass
        else:
            dmin = getattr(env, 'LED_ALT_MIN_DELAY_MS', 80)
            dmax = getattr(env, 'LED_ALT_MAX_DELAY_MS', 250)
            blink_next_at_ms = now + urandint(dmin, dmax)


def _on_gdo0_scheduled(_):
    """Handler programado (no ISR) para leer el paquete cuando GDO0 cae (fin de trama).
    Lee rápidamente uno o varios paquetes disponibles, decodifica y conserva el último válido.
    Además dispara el parpadeo de los LEDs alternos cuando hay dato válido.
    """
    global _schedule_pending, last_valid_decoded, last_valid_rx_ms, ws, gdo0_pin
    if ws is None:
        _schedule_pending = False
        # Rehabilitar IRQ si estaba deshabilitada
        try:
            if gdo0_pin:
                gdo0_pin.irq(trigger=Pin.IRQ_FALLING, handler=_gdo0_irq)
        except Exception:
            pass
        return

    did_blink = False
    try:
        # Drena ráfagas (muchos sensores Bresser repiten varias veces)
        for _ in range(3):
            pkt = ws.receive(timeout_ms=0)
            if not pkt:
                break
            decoded = ws.decode(pkt)
            if isinstance(decoded, dict):
                if env.DEBUG:
                    # Imprime cada intento fallido/exitoso para diagnóstico
                    print('DECODE GDO0 Attempt:', decoded)
                if decoded.get('crc_ok'):
                    last_valid_decoded = decoded
                    last_valid_rx_ms = ticks_ms()
                    did_blink = True
    except Exception as e:
        if env.DEBUG:
            print('Error en handler programado:', e)
        try:
            if ws and ws.radio:
                ws.radio.enter_rx()
        except Exception:
            pass
    finally:
        if did_blink:
            schedule_random_blink()
        _schedule_pending = False
        # Rehabilitar IRQ para próximas tramas
        try:
            if gdo0_pin:
                gdo0_pin.irq(trigger=Pin.IRQ_FALLING, handler=_gdo0_irq)
        except Exception:
            pass


def _gdo0_irq(pin):
    """ISR de GDO0: sólo programa la ejecución diferida para no hacer SPI en IRQ.
    Aplica debounce y deshabilita la IRQ hasta que el handler programado termine,
    para evitar llenar la cola de `micropython.schedule`.
    """
    global _schedule_pending, last_irq_ms, last_sched_fail_ms
    now = ticks_ms()
    # Debounce básico para evitar ráfagas/bounce
    if ticks_diff(now, last_irq_ms) < MIN_IRQ_INTERVAL_MS:
        return
    last_irq_ms = now

    if not _schedule_pending:
        _schedule_pending = True
        # Deshabilitar IRQ mientras tenemos un handler pendiente
        try:
            if gdo0_pin:
                gdo0_pin.irq(handler=None)
        except Exception:
            pass
        try:
            micropython.schedule(_on_gdo0_scheduled, 0)
        except Exception as e:
            # Rehabilitar inmediatamente si no se pudo programar
            try:
                if gdo0_pin:
                    gdo0_pin.irq(trigger=Pin.IRQ_FALLING, handler=_gdo0_irq)
            except Exception:
                pass
            _schedule_pending = False
            # Registrar el fallo de forma silenciosa para evitar floods en IRQ
            last_sched_fail_ms = now


def setup_gdo0_irq():
    """Configura la IRQ en GDO0 para recepción por eventos (si está disponible)."""
    global gdo0_pin
    try:
        if ws is not None and isinstance(env.CC1101_GDO0, int) and env.CC1101_GDO0 >= 0:
            gdo0_pin = Pin(env.CC1101_GDO0, Pin.IN)
            # IOCFG0=0x06 → deassert al final de paquete; usamos flanco de bajada
            gdo0_pin.irq(trigger=Pin.IRQ_FALLING, handler=_gdo0_irq)
            if DEBUG:
                print('IRQ GDO0 configurado en pin', env.CC1101_GDO0)
    except Exception as e:
        if DEBUG:
            print('No se pudo configurar IRQ GDO0:', e)


# ----------------- Doble buffer y procesamiento en segundo hilo -----------------
# Parámetros de lote desde env
BATCH_SIZE = int(getattr(env, 'BATCH_SIZE', 50) or 50)
BATCH_WINDOW_MS = int(getattr(env, 'BATCH_WINDOW_MS', 60000) or 60000)
# Longitud de paquete configurada (máxima en el CC1101). En modo longitud variable,
# el driver devuelve [L|payload(L)] sin bytes de estado, por lo que añadimos +1 para L.
PKT_LEN_BUF = int(getattr(env, 'CC1101_PKT_LEN', 27) or 27) + 1

# Buffers preasignados (dos lotes A/B)
bufA = [bytearray(PKT_LEN_BUF) for _ in range(BATCH_SIZE)]
bufB = [bytearray(PKT_LEN_BUF) for _ in range(BATCH_SIZE)]
lenA = [0 for _ in range(BATCH_SIZE)]
lenB = [0 for _ in range(BATCH_SIZE)]
batch_count = [0, 0]
batch_ready = [False, False]
batch_start_ms = [ticks_ms(), ticks_ms()]
active_buf = 0
write_idx = 0

# Señalización entre hilos
upload_ready = False
payload_to_upload = None
blink_requests = 0

# Protección básica
lock = _thread.allocate_lock()


def _signal_blink_request(times: int = 1):
    global blink_requests
    with lock:
        blink_requests += max(1, int(times))


def _consume_blink_request() -> int:
    global blink_requests
    with lock:
        if blink_requests > 0:
            blink_requests -= 1
            return 1
        return 0


def _set_upload_payload(payload: dict):
    global upload_ready, payload_to_upload
    with lock:
        payload_to_upload = payload
        upload_ready = True


def _take_upload_payload():
    global upload_ready, payload_to_upload
    with lock:
        if upload_ready and payload_to_upload is not None:
            p = payload_to_upload
            payload_to_upload = None
            upload_ready = False
            return p
        return None


def _rotate_batch_if_needed(now_ms: int):
    global active_buf, write_idx
    # Comprueba tamaño o ventana de tiempo (solo rota por tiempo si hay datos)
    if write_idx >= BATCH_SIZE or (write_idx > 0 and ticks_diff(now_ms, batch_start_ms[active_buf]) >= BATCH_WINDOW_MS):
        batch_ready[active_buf] = True
        # alternar
        active_buf = 1 - active_buf
        batch_start_ms[active_buf] = now_ms
        batch_count[active_buf] = 0
        # Reiniciar índice de escritura
        write_idx = 0


core1_last_alive_ms = ticks_ms()


def processor_thread(_):
    global core1_last_alive_ms
    """Segundo hilo: procesa lotes preparados por el hilo principal.
    - Decodifica todas las tramas del lote listo.
    - Si encuentra un conjunto completo (temp+hum+viento+lluvia), prepara payload
      y lo marca para subida por el hilo principal (pausando recepción durante la subida).
    - En modo FIND_STATION_IDS, imprime IDs detectados y no prepara payloads.
    """
    if env.DEBUG:
        try:
            print('\nInicia hilo de procesado (core 1)')
        except Exception:
            pass

    # Tiempo máximo esperando datos incompletos antes de subir con los que haya (ms)
    PARTIAL_UPLOAD_TIMEOUT_MS = int(getattr(env, 'PARTIAL_UPLOAD_TIMEOUT_MS', 60000))

    # Estado de agregación independiente del hilo principal
    agg = {
        'first_read': True,
        'temp': 0.0, 'temp_ok': False,
        'humidity': 0.0, 'humidity_ok': False,
        'wind_avg': 0.0, 'wind_gust': 0.0, 'wind_dir': 0.0, 'wind_ok': False,
        'rain_month': 0.0, 'rain': 0.0, 'rain_intensity': 0.0, 'rain_ok': False,
        'last_rain_ts_ms': ticks_ms(),
        'last_sensor_id': None,
        # Timeout de datos incompletos
        'partial_start_ms': 0,   # cuándo llegó el primer dato del ciclo actual
        'any_data': False,        # hay al menos un campo recibido en el ciclo actual
    }

    FIND_MODE_LOCAL = bool(getattr(env, 'FIND_STATION_IDS', False))
    SHOW_ALL = bool(getattr(env, 'SHOW_ALL_DECODED', False))

    seen_ids_local = set()
    last_ids_print_ms = ticks_ms() + 15000

    while True:
        core1_last_alive_ms = ticks_ms()
        # Elegir lote listo
        take_idx = -1
        count = 0
        with lock:
            if batch_ready[0]:
                take_idx = 0
                batch_ready[0] = False
                count = batch_count[0]
            elif batch_ready[1]:
                take_idx = 1
                batch_ready[1] = False
                count = batch_count[1]
        if take_idx == -1 or count <= 0:
            sleep_ms(5)
            continue

        # Procesar fuera del lock
        try:
            if take_idx == 0:
                buf = bufA
                lens = lenA
            else:
                buf = bufB
                lens = lenB

            for i in range(count):
                ln = lens[i]
                if ln <= 0:
                    continue


                # Crear una vista/bytes de longitud real
                #pkt = bytes(memoryview(buf[i])[:ln])
                pkt = bytes(memoryview(buf[i]))
                decoded = None



                # TMP: Buscando tamaños y probando recepción
                """
                if env.DEBUG:
                    print('len: ', len(bytes(memoryview(buf[i]))))
                    print(' '.join(f'{b:02X}' for b in bytes(memoryview(buf[i]))))
                """

                try:
                    if ws is not None:
                        decoded = ws.decode(pkt)
                except Exception as e:
                    if env.DEBUG:
                        try:
                            print('Decode error:', e)
                        except Exception:
                            pass
                    decoded = None

                # Modo búsqueda de IDs
                if FIND_MODE_LOCAL:
                    sid = decoded.get('sensor_id') if isinstance(decoded, dict) else None
                    if isinstance(decoded, dict) and decoded.get('ok') and sid is not None and sid not in seen_ids_local:
                        seen_ids_local.add(sid)
                        try:
                            print('ID detectado:', sid, ' tipo:', decoded.get('type'), ' chan:', decoded.get('chan'))
                        except Exception:
                            pass
                        _signal_blink_request(1)
                    elif sid is None and ws is not None:
                        # Intentar candidatos de ID desde el paquete bruto
                        try:
                            ids = ws.probe_ids_from_packet(pkt)
                            for sidc in ids:
                                if sidc not in seen_ids_local:
                                    seen_ids_local.add(sidc)
                                    try:
                                        print('(hilo2) ID candidato:', sidc)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    # Logs periódicos
                    if env.DEBUG:
                        nowp = ticks_ms()
                        if ticks_diff(nowp, last_ids_print_ms) >= 0:
                            try:
                                print('(hilo2) IDs vistos hasta ahora:',
                                      list(seen_ids_local))
                            except Exception:
                                pass
                            last_ids_print_ms = nowp + 15000
                    # No agregamos ni preparamos payloads en modo búsqueda
                    continue

                # Modo normal: logs opcionales y agregación
                if SHOW_ALL and isinstance(decoded, dict):
                    try:
                        print('Decodificado:', decoded)
                    except Exception:
                        pass

                if not isinstance(decoded, dict) or not decoded.get('ok'):
                    continue

                # Blink visual por trama válida
                _signal_blink_request(1)

                sid = decoded.get('sensor_id') if isinstance(decoded, dict) else None
                if sid is not None:
                    if agg['last_sensor_id'] is None:
                        agg['last_sensor_id'] = sid
                    elif agg['last_sensor_id'] != sid:
                        # Reiniciar flags para nuevo sensor
                        agg['temp_ok'] = agg['humidity_ok'] = agg['wind_ok'] = agg['rain_ok'] = False
                        agg['rain'] = 0.0
                        agg['rain_intensity'] = 0.0
                        agg['last_sensor_id'] = sid

                if decoded.get('temp_ok'):
                    agg['temp'] = decoded.get('temp_c') or 0.0
                    agg['temp_ok'] = True
                if decoded.get('humidity_ok'):
                    agg['humidity'] = decoded.get('humidity') or 0.0
                    agg['humidity_ok'] = True
                if decoded.get('wind_ok'):
                    agg['wind_avg'] = decoded.get('wind_avg_ms') or 0.0
                    agg['wind_gust'] = decoded.get('wind_gust_ms') or 0.0
                    agg['wind_dir'] = decoded.get('wind_dir_deg') or 0.0
                    agg['wind_ok'] = True
                if decoded.get('rain_ok'):
                    new_month = decoded.get('rain_mm') or 0.0
                    nowm = ticks_ms()
                    if agg['first_read']:
                        agg['rain_month'] = new_month
                        agg['last_rain_ts_ms'] = nowm
                        agg['first_read'] = False
                    else:
                        diff_mm = new_month - agg['rain_month']
                        agg['rain'] = diff_mm if diff_mm > 0 else 0.0
                        agg['rain_month'] = new_month
                        dt_ms = max(1, ticks_diff(nowm, agg['last_rain_ts_ms']))
                        agg['last_rain_ts_ms'] = nowm
                        agg['rain_intensity'] = (agg['rain'] / (dt_ms / 1000.0)) * 3600.0 if agg['rain'] > 0 else 0.0
                    agg['rain_ok'] = True

                # Marcar inicio del ciclo parcial en cuanto llega el primer dato
                if not agg['any_data'] and (agg['temp_ok'] or agg['humidity_ok'] or agg['wind_ok'] or agg['rain_ok']):
                    agg['any_data'] = True
                    agg['partial_start_ms'] = ticks_ms()





                if DEBUG:
                    if agg['temp_ok']:
                        print('Temperatura:', agg['temp'])
                    elif agg['humidity_ok']:
                        print('Humedad:', agg['humidity'])
                    elif agg['wind_ok']:
                        print('Viento:', agg['wind_avg'], agg['wind_gust'], agg['wind_dir'])
                    elif agg['rain_ok']:
                        print('Lluvia:', agg['rain'], agg['rain_intensity'])
                    else:
                        print('No se pudo procesar trama:', decoded)

                # Si ya hay conjunto completo, preparar payload y marcar para subida por hilo principal
                if agg['temp_ok'] and agg['humidity_ok'] and agg['wind_ok'] and agg['rain_ok']:
                    payload = {
                        'temperature': agg['temp'],
                        'humidity': agg['humidity'],
                        'wind_speed': agg['wind_avg'],
                        'wind_average_speed': agg['wind_avg'],
                        'wind_min_speed': agg['wind_avg'],
                        'wind_max_speed': agg['wind_gust'],
                        'wind_grades': agg['wind_dir'],
                        'rain': agg['rain'],
                        'rain_intensity': agg['rain_intensity'],
                        'rain_month': agg['rain_month'],
                    }
                    _set_upload_payload(payload)
                    # Reiniciar flags y estado parcial
                    agg['temp_ok'] = False
                    agg['humidity_ok'] = False
                    agg['wind_ok'] = False
                    agg['rain_ok'] = False
                    agg['any_data'] = False
                    agg['partial_start_ms'] = 0
        except Exception as e:
            if env.DEBUG:
                try:
                    print('Error procesando lote:', e)
                except Exception:
                    pass

        # Timeout de datos parciales: si llevamos más de PARTIAL_UPLOAD_TIMEOUT_MS
        # sin completar el conjunto, subir lo que haya con None en los campos ausentes.
        if not FIND_MODE_LOCAL and agg['any_data']:
            has_all = agg['temp_ok'] and agg['humidity_ok'] and agg['wind_ok'] and agg['rain_ok']
            if not has_all:
                elapsed = ticks_diff(ticks_ms(), agg['partial_start_ms'])
                if elapsed >= PARTIAL_UPLOAD_TIMEOUT_MS:
                    payload_partial = {
                        'temperature':        agg['temp']          if agg['temp_ok']     else None,
                        'humidity':           agg['humidity']      if agg['humidity_ok'] else None,
                        'wind_speed':         agg['wind_avg']      if agg['wind_ok']     else None,
                        'wind_average_speed': agg['wind_avg']      if agg['wind_ok']     else None,
                        'wind_min_speed':     agg['wind_avg']      if agg['wind_ok']     else None,
                        'wind_max_speed':     agg['wind_gust']     if agg['wind_ok']     else None,
                        'wind_grades':        agg['wind_dir']      if agg['wind_ok']     else None,
                        'rain':               agg['rain']          if agg['rain_ok']     else None,
                        'rain_intensity':     agg['rain_intensity'] if agg['rain_ok']    else None,
                        'rain_month':         agg['rain_month']    if agg['rain_ok']     else None,
                    }
                    if env.DEBUG:
                        try:
                            print('(hilo2) Timeout parcial — subiendo datos incompletos:', payload_partial)
                        except Exception:
                            pass
                    _set_upload_payload(payload_partial)
                    # Reiniciar ciclo (mantener últimos valores para siguiente ciclo)
                    agg['temp_ok'] = False
                    agg['humidity_ok'] = False
                    agg['wind_ok'] = False
                    agg['rain_ok'] = False
                    agg['any_data'] = False
                    agg['partial_start_ms'] = 0

        # Pequeño respiro
        sleep_ms(1)

# Lanzar el hilo de procesado (core 1)
try:
    _thread.start_new_thread(processor_thread, (None,))
    if DEBUG:
        print('Hilo de procesado iniciado')
except Exception as e:
    if DEBUG:
        print('No se pudo iniciar el hilo de procesado:', e)


def thread0 ():
    """
    Primer hilo, flujo principal de la aplicación.
    En este hilo colocamos toda la lógica principal de funcionamiento.
    """
    pass


# Heartbeat del bucle principal — definido aquí (nivel de módulo) para evitar
# el frágil patrón  if 'service_heartbeat' not in globals()  dentro del while.
def service_heartbeat():
    """Parpadea el LED integrado cada HEARTBEAT_MS ms sin bloquear.
    led_on (GPIO15) es un indicador fijo (no parpadea) y no se toca aquí."""
    global heartbeat_next_ms, heartbeat_state, upload_in_progress
    if heartbeat_led is None:
        return
    if upload_in_progress:
        return
    now = ticks_ms()
    if ticks_diff(now, heartbeat_next_ms) >= 0:
        heartbeat_state ^= 1
        try:
            heartbeat_led.value(heartbeat_state)
        except Exception:
            pass
        heartbeat_next_ms = now + HEARTBEAT_MS


# Inicializar Watchdog Hardware (timeout 8000ms) para autorrecuperacion
ENABLE_WDT = getattr(env, 'ENABLE_WDT', True)
if ENABLE_WDT and hasattr(rpi, 'init_wdt'):
    rpi.init_wdt(timeout_ms=8000)

while True:
    # 0) Alimentar Watchdog por hardware
    if hasattr(rpi, 'feed_wdt'):
        rpi.feed_wdt()

    # 0.1) Supervision de salud de Core 1 cada 15 segundos
    if 'last_core1_check_ms' not in globals():
        last_core1_check_ms = ticks_ms()
    now_c1 = ticks_ms()
    if ticks_diff(now_c1, last_core1_check_ms) >= 15000:
        last_core1_check_ms = now_c1
        if 'core1_last_alive_ms' in globals() and ticks_diff(now_c1, core1_last_alive_ms) > 120000:
            if DEBUG:
                print('CRITICO: Core 1 bloqueado (>120s sin pulso). Reiniciando microcontrolador...')
            import machine
            machine.reset()

    # 0.2) Recoleccion periodica de basura en el heap (cada 30 segundos)
    if 'next_gc_ms' not in globals():
        next_gc_ms = ticks_ms() + 30000
    now_gc = ticks_ms()
    if ticks_diff(now_gc, next_gc_ms) >= 0:
        next_gc_ms = now_gc + 30000
        try:
            gc.collect()
        except Exception:
            pass

    # 0.3) Sincronizacion horaria periodica RTC cada 24 horas
    if 'next_rtc_sync_ms' not in globals():
        next_rtc_sync_ms = ticks_ms() + (24 * 3600 * 1000)
    now_rtc = ticks_ms()
    if WIFI_ENABLED and ticks_diff(now_rtc, next_rtc_sync_ms) >= 0:
        next_rtc_sync_ms = now_rtc + (24 * 3600 * 1000)
        try:
            if DEBUG:
                print('Sincronizacion periodica RTC...')
            rpi.sync_rtc_time()
        except Exception as e:
            if DEBUG:
                print('Error en sincronizacion periodica de RTC:', e)

    # Inicializar agregador de lecturas una sola vez
    if 'state' not in globals():
        state = {
            'first_read': True,
            'temp': 0.0, 'temp_ok': False,
            'humidity': 0.0, 'humidity_ok': False,
            'wind_avg': 0.0, 'wind_gust': 0.0, 'wind_dir': 0.0, 'wind_ok': False,
            'rain_month': 0.0, 'rain': 0.0, 'rain_intensity': 0.0, 'rain_ok': False,
            'last_rain_ts_ms': ticks_ms(),
            'last_sensor_id': None,
        }

    # Radio diagnostics (DEBUG): every 5s print status
    if DEBUG and ws is not None:
        if 'next_radio_diag_ms' not in globals():
            next_radio_diag_ms = ticks_ms() + 30000
        now = ticks_ms()
        if ticks_diff(now, next_radio_diag_ms) >= 0:
            try:
                st = ws.radio.get_status() if ws and ws.radio else None
                if st:
                    print('CC1101 status:', st)
            except Exception as e:
                if DEBUG:
                    print('Diag radio error:', e)
            next_radio_diag_ms = now + 30000

    # 1) Si el hilo de procesado ha marcado payload para subir, SUBIR ahora
    payload = _take_upload_payload()
    if payload is not None:
        # Datos recibidos: apagar LED ON (ya no está esperando datos)
        if led_on:
            try:
                led_on.value(0)
            except Exception:
                pass
        if not API_ENABLED:
            if DEBUG:
                print('API_ENABLED=False — payload descartado:', payload)
        else:
            # Pausar lecturas durante la subida
            upload_in_progress = True
            if led_read:
                try:
                    led_read.value(1)
                except Exception:
                    pass
            ok = False
            try:
                ok = api.send_to_api(payload)
            except Exception as e:
                if DEBUG:
                    print('Excepción al subir a la API:', e)
            if led_read:
                try:
                    led_read.value(0)
                except Exception:
                    pass
            upload_in_progress = False
            if ok and DEBUG:
                print('Subida correcta')
            elif DEBUG and not ok:
                print('Fallo al subir a la API')
        # Efecto visual de confirmación (tanto si subió como si API está desactivada)
        schedule_random_blink()
        # Volver a encender LED ON: el sistema regresa al bucle esperando nuevos datos
        if led_on:
            try:
                led_on.value(1)
            except Exception:
                pass
        # Tras subir, continuar a siguiente iteración (lecturas pausadas sólo mientras dura el POST)
        sleep_ms(5)
        gc.collect()
        continue

    # 2) Bombear la radio rápidamente (polling sin bloqueo) y escribir en el buffer activo
    if ws is not None:
        try:
            # Inicializar modo búsqueda de IDs y alternadores si no existen
            if 'FIND_MODE' not in globals():
                FIND_MODE = bool(getattr(env, 'FIND_STATION_IDS', False))
            # Alternar automáticamente el modo de sincronización durante la búsqueda de IDs
            if FIND_MODE and getattr(env, 'CC1101_AUTO_SYNC_PROBE', False):
                if 'NEXT_SYNC_TOGGLE_MS' not in globals():
                    NEXT_SYNC_TOGGLE_MS = ticks_ms() + int(getattr(env, 'CC1101_SYNC_PROBE_PERIOD_MS', 30000))
                now_probe = ticks_ms()

            # Asegurar RX y recuperarse de overflow
            if ws.radio:
                try:
                    ws.radio.ensure_rx()
                except Exception:
                    pass

            drained = 0
            for _ in range(8):  # lotes pequeños para minimizar latencia
                pkt = ws.receive(timeout_ms=0)

                if not pkt:
                    break

                drained += 1
                noww = ticks_ms()
                # Escribir en buffer activo de forma protegida y rotar si toca
                with lock:
                    n = PKT_LEN_BUF if len(pkt) >= PKT_LEN_BUF else len(pkt)
                    if active_buf == 0:
                        if write_idx < BATCH_SIZE:
                            bufA[write_idx][:n] = pkt[:n]
                            lenA[write_idx] = n
                            batch_count[0] = write_idx + 1
                            write_idx += 1
                    else:
                        if write_idx < BATCH_SIZE:
                            bufB[write_idx][:n] = pkt[:n]
                            lenB[write_idx] = n
                            batch_count[1] = write_idx + 1
                            write_idx += 1
                    _rotate_batch_if_needed(noww)
        except Exception as e:
            if DEBUG:
                print('Error bombeando radio:', e)
            try:
                if ws and ws.radio:
                    ws.radio.enter_rx()
            except Exception:
                pass

    # 2) Servicio de parpadeo no bloqueante
    service_blink()
    # Consumir peticiones de parpadeo generadas por el hilo 2
    if _consume_blink_request():
        schedule_random_blink()

    # 2.1) Latido (heartbeat) no bloqueante para ver que el bucle está vivo
    service_heartbeat()

    # 3) Si tenemos todos los datos necesarios, SUBIR inmediatamente a la API
    if state['temp_ok'] and state['humidity_ok'] and state['wind_ok'] and state['rain_ok']:
            # Si estamos en modo búsqueda de IDs, no subir ni agregar nada
            if 'FIND_MODE' in globals() and FIND_MODE:
                if DEBUG:
                    print('FIND_STATION_IDS activo: conjunto completo recibido, pero se omite subida a la API')
                # Reiniciar flags para esperar un nuevo conjunto si se desea
                state['temp_ok'] = state['humidity_ok'] = state['wind_ok'] = state['rain_ok'] = False
                sleep_ms(5)
            else:
                # Preparar payload similar al proyecto antiguo
                payload = {
                    'temperature': state['temp'],
                    'humidity': state['humidity'],
                    'wind_speed': state['wind_avg'],
                    'wind_average_speed': state['wind_avg'],
                    'wind_min_speed': state['wind_avg'],  # sin histórico, usar avg como aproximación
                    'wind_max_speed': state['wind_gust'],
                    'wind_grades': state['wind_dir'],
                    'rain': state['rain'],
                    'rain_intensity': state['rain_intensity'],
                    'rain_month': state['rain_month'],
                }
                if DEBUG:
                    print('Payload listo para API:', payload)
                # Datos recibidos: apagar LED ON (ya no está esperando datos)
                if led_on:
                    try:
                        led_on.value(0)
                    except Exception:
                        pass
                ok = False
                if not API_ENABLED:
                    if DEBUG:
                        print('API_ENABLED=False — payload descartado (legacy path):', payload)
                else:
                    # LED de subida (rojo) ON y pausar heartbeat
                    try:
                        upload_in_progress = True
                        if led_read:
                            try:
                                led_read.value(1)
                            except Exception:
                                pass
                        ok = api.send_to_api(payload)
                    except Exception as e:
                        if DEBUG:
                            print('Excepción al subir a la API:', e)
                    # LED rojo OFF
                    if led_read:
                        try:
                            led_read.value(0)
                        except Exception:
                            pass
                    upload_in_progress = False
                # Volver a encender LED ON: sistema regresa al bucle esperando datos
                if led_on:
                    try:
                        led_on.value(1)
                    except Exception:
                        pass
                if ok:
                    if DEBUG:
                        print('Subida correcta. Reiniciando flags de lectura...')
                    # Reiniciar solo los OK para requerir nuevo conjunto
                    state['temp_ok'] = False
                    state['humidity_ok'] = False
                    state['wind_ok'] = False
                    state['rain_ok'] = False
                    # Mantener últimos valores/rain_month para siguientes cálculos
                    # Efecto visual: otro parpadeo alterno
                    schedule_random_blink()
                else:
                    if DEBUG:
                        print('Fallo al subir a la API')

    # 4) Pequeña pausa cooperativa
    sleep_ms(15)
    #gc.collect()
