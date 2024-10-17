from machine import ADC, Pin, SPI
import network
from time import sleep

# Constants
WIFI_DISCONNECTED = 0
WIFI_CONNECTING = 1
WIFI_CONNECTED = 3


class RpiPico:
    INTEGRATED_TEMP_CORRECTION = 27  # Corrección de temperatura interna para ajustar lecturas
    adc_voltage_correction = 0.706
    voltage_working = 3.3
    num_of_measurements = 0  # Número de mediciones de temperatura

    max = 0
    min = 0
    avg = 0
    current = 0
    sum_of_temps = 0  # Suma de todas las lecturas de temperatura
    locked = False

    # Inalámbrico
    wifi = None

    i2c0 = None
    i2c1 = None
    spi0 = None
    spi0_cs = None
    spi1 = None
    spi1_cs = None

    def __init__ (self, ssid=None, password=None, debug=False, country="ES",
                  alternatives_ap=None,
                  hostname="Rpi-Pico-W"):
        """
        Constructor de la clase para Raspberry Pi Pico W.

        Args:
            ssid (str): ID de red para la conexión Wi-Fi. Por defecto None.
            password (str): Contraseña para la conexión Wi-Fi. Por defecto None.
            debug (bool): Indica si se muestran los mensajes de debug. Por defecto False.
            alternatives_ap (tuple): Puedes pasar una tupla con redes adicionales.
            country (str): Código del país. Por defecto 'ES'.
        """
        self.locked = True
        self.DEBUG = debug
        self.SSID = ssid
        self.PASSWORD = password
        self.COUNTRY = country
        self.hostname = hostname
        self.alternatives_ap = alternatives_ap

        self.TEMP_SENSOR = ADC(4)  # Sensor interno de Raspberry Pi Pico.

        self.LED_INTEGRATED = Pin("LED",
                                  Pin.OUT)  # Definición del GPIO para el LED integrado

        self.adc_conversion_factor = self.voltage_working / 65535  # Factor de conversión de 16 bits

        # Si se proporcionan credenciales del AP intenta la conexión
        if ssid and password:
            if self.DEBUG:
                print('Iniciando la conexión inalámbrica')

            self.wifi_connect(ssid, password)

        sleep(0.100)

        self.reset_stats()
        self.locked = False

    def set_spi(self, pin_sck, pin_mosi, pin_miso, pin_cs, bus=0):
        """
        Crea una instancia SPI para el bus especificado.

        Args:
            pin_sck: Pin de reloj (SCK).
            pin_mosi: Pin de datos de salida (MOSI).
            pin_miso: Pin de datos de entrada (MISO).
            pin_cs: Pin para cable select (CS).
            bus: Número de bus SPI (0 o 1).

        Returns:
            Instancia SPI configurada or None.
        """

        if bus > 1:
            return None

        self.locked = True

        try:
            spi = SPI(bus, sck=Pin(pin_sck), mosi=Pin(pin_mosi), miso=Pin(pin_miso))
            spi_cs = Pin(pin_cs, Pin.OUT)

            if bus == 0:
                self.spi0 = spi
                self.spi0_cs = spi_cs
            elif bus == 1:
                self.spi1 = spi
                self.spi1_cs = spi_cs
        except Exception as e:
            if self.DEBUG:
                print('Error en set_spi:', e)

            self.locked = False

            return None

        self.locked = False

        return spi

    def get_spi_cs(self, bus=0):
        """
        Devuelve la instancia del pin CS para un bus SPI.
        :param bus: Número de bus SPI (0 o 1).
        :return: SPI instance or None
        """
        if bus == 0:
            return self.spi0_cs
        elif bus == 1:
            return self.spi1_cs

        return None

    def reset_stats (self, temp=None) -> None:
        """
        Reinicia las estadísticas de temperatura.

        Args:
            temp (float): Valor inicial con el que resetear las estadísticas. Por defecto None.
        """
        temp = temp if temp else self.read_sensor_temp()
        self.max = temp
        self.min = temp
        self.avg = temp
        self.current = temp

    def read_sensor_temp (self) -> float:
        """
        Lee la temperatura actual del sensor.

        Returns:
            float: Temperatura leída.
        """
        # Continúa si no está bloqueado
        if self.locked:
            return self.current

        reading = (
                              self.TEMP_SENSOR.read_u16() * self.adc_conversion_factor) - self.adc_voltage_correction
        value = self.INTEGRATED_TEMP_CORRECTION - reading / 0.001721

        cpu_temp = round(float(value), 1)
        self.current = cpu_temp

        # Actualiza las estadísticas
        if cpu_temp > self.max:
            self.max = cpu_temp
        if cpu_temp < self.min:
            self.min = cpu_temp

        self.num_of_measurements += 1
        self.sum_of_temps += cpu_temp
        self.avg = round(self.sum_of_temps / self.num_of_measurements, 1)

        return cpu_temp

    def get_temp (self) -> float:
        """
        Obtiene la temperatura actual.

        Returns:
            float: Temperatura actual.
        """
        return self.read_sensor_temp()

    def led_on (self) -> None:
        """
        Enciende el LED integrado.

        :return: None
        """
        self.LED_INTEGRATED.on()

    def led_off (self) -> None:
        """
        Apaga el LED integrado.

        :return: None
        """
        self.LED_INTEGRATED.off()

    def get_temp_stats (self) -> dict:
        """
        Obtiene las estadísticas actuales de temperatura.

        Returns:
            dict: Contiene la temperatura máxima, mínima, promedio y actual.
        """
        return {
            'max': self.max,
            'min': self.min,
            'avg': self.avg,
            'current': self.current
        }

    def wifi_status (self) -> int:
        """
        Obtiene el estado de la conexión Wi-Fi.

        Returns:
            int: Constante que indica el estado de la conexión Wi-Fi.
        """
        return self.wifi.status() if self.wifi else WIFI_DISCONNECTED

    def wifi_is_connected (self) -> bool:
        """
        Comprueba si el Wi-Fi está conectado.

        Returns:
            bool: True si está conectado, False en caso contrario.
        """
        return bool(
            self.wifi and self.wifi.isconnected() and self.wifi.status() == WIFI_CONNECTED)

    def get_wireless_mac(self) -> str:
        """
        Convierte la dirección MAC a formato legible y la devuelve.
        :return:
        """
        import ubinascii

        return ubinascii.hexlify(network.WLAN().config('mac'), ':').decode()

    def get_wireless_ssid(self) -> str:
        """
        Devuelve el SSID al que se ha conectado.
        :return:
        """
        return self.wifi.config('essid')

    def get_wireless_ip(self) -> str:
        """
        Devuelve la ip de la conexión actual.
        :return:
        """
        return self.wifi.ifconfig()[0]

    def get_wireless_hostname(self) -> str:
        """
        Devuelve el nombre de host en la red.
        :return:
        """
        return self.wifi.config('hostname')

    def get_wireless_txpower(self) -> int:
        """
        Devuelve la potencia de transmisión configurada actualmente por la rpi.
        :return:
        """
        return self.wifi.config('txpower')

    def get_wireless_rssi(self) -> int:
        """
        Devuelve la potencia de transmisión del router.
        :return:
        """
        return self.wifi.status('rssi')

    def get_wireless_channel(self) -> int:
        """
        Devuelve el canal de comunicación con el router.
        :return:
        """
        return self.wifi.config('channel')

    def wifi_debug (self) -> None:
        """
        Muestra información de debug de la conexión Wi-Fi.
        """
        print('Conectado a wifi:', self.wifi_is_connected())
        print('Estado del wi-fi:', self.wifi_status())
        print('Hostname:', self.get_wireless_hostname())
        print('Dirección MAC: ', self.get_wireless_mac())
        print('Dirección IP Wi-fi:', self.get_wireless_ip())
        print('Potencia de transmisión (TXPOWER):', self.get_wireless_txpower())
        print('SSID: ', self.get_wireless_ssid())
        print('Canal de Wi-fi: ', self.get_wireless_channel())
        print('RSSI: ', self.get_wireless_rssi())

    def wifi_connect (self, ssid=None, password=None) -> bool:
        """
        Intenta conectar a Wi-Fi con las credenciales dadas.

        Args:
            ssid (str): ID de red para la conexión Wi-Fi.
            password (str): Contraseña para la conexión Wi-Fi.

        Retorno:
            bool: True si se logra conectarse, False en caso contrario.
        """
        if ssid is None and password is None:
            ssid, password = self.SSID, self.PASSWORD

        self.wifi = network.WLAN(network.STA_IF)
        self.wifi.active(True)

        # Establezco el nombre del host
        network.hostname(self.hostname)

        # Desactivo el ahorro de energía
        self.wifi.config(pm=0xa11140)

        while not self.wifi_is_connected():
            # Escaneo las redes disponibles
            available_ssids = self.wifi.scan()
            available_ssids = [ap[0].decode('utf-8') for ap in available_ssids]

            # Si la red principal se encuentra disponible, intenta conectar a ella
            if self.SSID in available_ssids:
                self.wifi.connect(self.SSID, self.PASSWORD)
            else:
                # Si no esta la red principal, intenta conectar a las redes secundarias disponibles
                for ap in self.alternatives_ap:
                    if ap['ssid'] in available_ssids:
                        self.wifi.connect(ap['ssid'], ap['password'])

            sleep(1)

            if self.wifi_is_connected():
                if self.DEBUG:
                    self.wifi_debug()

                return True

        return False

    def wireless_info (self):
        info_client = [
            {
                "name": 'Connected:',
                "value": 'Yes' if self.wifi_is_connected() else 'No',
            },
            {
                "name": 'Hostname:',
                "value": self.get_wireless_hostname(),
            },
            {
                "name": 'MAC:',
                "value": self.get_wireless_mac(),
            },
            {
                "name": 'TXPOWER:',
                "value": self.get_wireless_txpower(),
            },
            {
                "name": 'IP:',
                "value": self.get_wireless_ip(),
            },
        ]

        info_ap = [
            {
                "name": 'SSID:',
                "value": self.get_wireless_ssid(),
            },
            {
                "name": 'RSSI',
                "value": self.get_wireless_rssi(),
            },
            {
                "name": 'Channel',
                "value": self.get_wireless_channel(),
            },
        ]

        return info_client, info_ap

    def wifi_disconnect (self) -> None:
        """
        Desconecta el wi-fi.

        :return: None
        """
        self.wifi.disconnect()

    def read_analog_input (self, pin) -> float:
        """
        Lee una entrada analógica.

        Args:
            pin (int): Número del pin del que leer.

        Returns:
            float: Lectura analógica.
        """
        reading = ADC(pin).read_u16()

        return self.voltage_working - ((reading / 65535) * self.voltage_working)
