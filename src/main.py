import gc
from time import sleep_ms
from Models.Api import Api
from Models.RpiPico import RpiPico

# Importo variables de entorno
import env
from machine import I2C, Pin, SPI

# Habilito recolector de basura
gc.enable()

DEBUG = env.DEBUG

# Rpi Pico Model
controller = RpiPico(ssid=env.AP_NAME, password=env.AP_PASS, debug=DEBUG,
                     alternatives_ap=env.ALTERNATIVES_AP,
                     hostname=env.HOSTNAME)




"""
TODO:
- métodos para setear spi 0,1,2... los que tenga
- métodos para setear i2c 1,2... los que tenga
- métodos para setear ADC
- Métodos para setear callback en un pin por alta y baja

En api:

- Implementar un get
- Implementar un post

"""







sleep_ms(20)

#i2c = I2C(0, scl=Pin(20), sda=Pin(21))
#address = 0x03 # Dirección del dispositivo i2c

#spi = SPI(0, baudrate=2000000, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
address = 5 # CS Pin en el caso de SPI

sleep_ms(500)
sensor = Lightning(spi=spi, address=address, pin_irq=22, debug=env.DEBUG,
                   indoor=True)

sleep_ms(200)

# Api
api = Api(controller=controller, url=env.API_URL, path=env.API_PATH,
          token=env.API_TOKEN, device_id=env.DEVICE_ID, debug=env.DEBUG)

sleep_ms(3000)


def thread1 ():
    """
    Primer hilo, flujo principal de la aplicación.
    """

    if env.DEBUG:
        print('Inicia hilo principal (thread1)')

def thread0 ():
    """
    Primer hilo, flujo principal de la aplicación.
    """

    if env.DEBUG:
        print('Inicia hilo principal (thread0)')


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
