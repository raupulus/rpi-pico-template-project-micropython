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
controller = RpiPico(ssid=env.AP_NAME, password=env.AP_PASS, debug=DEBUG,
                     alternatives_ap=env.ALTERNATIVES_AP, hostname=env.HOSTNAME)

# Ejemplo Mostrando temperatura de cpu tras 5 lecturas (+1 al instanciar modelo)
print('Leyendo temperatura por 1a vez:', str(controller.get_cpu_temperature()))
sleep_ms(100)
print('Leyendo temperatura por 2a vez:', str(controller.get_cpu_temperature()))
sleep_ms(100)
print('Leyendo temperatura por 3a vez:', str(controller.get_cpu_temperature()))
sleep_ms(100)
print('Leyendo temperatura por 4a vez:', str(controller.get_cpu_temperature()))
sleep_ms(100)
print('Leyendo temperatura por 5a vez:', str(controller.get_cpu_temperature()))
sleep_ms(100)
print('Mostrando estadisticas de temperatura para CPU:', str(controller.get_cpu_temperature_stats()))

sleep_ms(100)

# Ejemplo instanciando SPI en bus 0.
spi0 = controller.set_spi(2, 3, 4, 5, 0)

sleep_ms(100)

# Ejemplo instanciando I2C en bus 0.
i2c0 = controller.set_i2c(20, 21, 0, 400000)
address = 0x03 # Dirección de un dispositivo i2c
# Ya podemos usar nuestro sensor con la dirección almacenada en "address"

# Ejemplo escaneando todos los dispositivos encontrados por I2C.
print('Dispositivos encontrados por I2C:', i2c0.scan())

"""
TODO:
- Métodos para setear callback en un pin por alta y baja
- métodos para setear ADC
- Implementar métodos para calcular estado de una batería de 3,7V

En api:

- Implementar un get
- Implementar un post
"""

sleep_ms(200)

# Api
api = Api(controller=controller, url=env.API_URL, path=env.API_PATH,
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
