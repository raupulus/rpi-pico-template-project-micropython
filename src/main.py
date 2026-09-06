import gc
from time import sleep_ms
from Models.Api import Api
from Models.RpiPico import RpiPico

# Importo variables de entorno
import env

# Habilito recolector de basura
gc.enable()

DEBUG = env.DEBUG

# Rpi Pico Model Instance
rpi = RpiPico(ssid=env.AP_NAME, password=env.AP_PASS, debug=DEBUG,
                     alternatives_ap=env.ALTERNATIVES_AP, hostname=env.HOSTNAME)

sleep_ms(100)

# Debug para mostrar el estado del wifi
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

# Ejemplo instanciando SPI en bus 0.
spi0 = rpi.set_spi(2, 3, 4, 5, 0)

sleep_ms(100)

# Ejemplo instanciando I2C en bus 0.
i2c0 = rpi.set_i2c(20, 21, 0, 400000)
address = 0x03 # Dirección de un dispositivo i2c
# Ya podemos usar nuestro sensor con la dirección almacenada en "address"

# Ejemplo escaneando todos los dispositivos encontrados por I2C.
print('Dispositivos encontrados por I2C:', i2c0.scan())

# Ejemplo asociando un callback al recibir +3.3v en el gpio 2
#rpi.set_callback_to_pin(2, "LOW", tu_callback)
rpi.set_callback_to_pin(2, lambda p: print("Se ejecuta el callback"), "LOW")

# Ejemplo leyendo batería externa (¡Cuidado! usa divisor de tensión, max 3,3v)
rpi.set_external_battery(28)
rpi.read_external_battery()

sleep_ms(200)

# Preparo la instancia para la comunicación con la API
api = Api(controller=rpi, url=env.API_URL, path=env.API_PATH,
          token=env.API_TOKEN, device_id=env.DEVICE_ID, debug=env.DEBUG)


# Pausa preventiva al desarrollar (ajustar, pero si usas dos hilos puede ahorrar tiempo por bloqueos de hardware ante errores)
sleep_ms(3000)


def thread1 ():
    """
    Segundo hilo.

    En este hilo colocamos otras operaciones con cuidado frente a la
    concurrencia.

    Recomiendo utilizar sistemas de bloqueo y pruebas independientes con las
    funcionalidades que vayas a usar en paralelo. Se puede romper la ejecución.
    """

    if env.DEBUG:
        print('')
        print('Inicia hilo principal (thread1)')


def thread0 ():
    """
    Primer hilo, flujo principal de la aplicación.
    En este hilo colocamos toda la lógica principal de funcionamiento.
    """

    if env.DEBUG:
        print('')
        print('Inicia hilo principal (thread0)')


    #print("Batería externa:", rpi.read_external_battery())

    print('')
    print('Termina el primer ciclo del hilo 0')
    print('')

    sleep_ms(10000)


while True:
    try:
        thread0()
    except Exception as e:
        if env.DEBUG:
            print('Error: ', e)
    finally:
        if env.DEBUG:
            print('Memoria antes de liberar: ', gc.mem_free())

        gc.collect()

        if env.DEBUG:
            print("Memoria después de liberar:", gc.mem_free())

        sleep_ms(5000)
