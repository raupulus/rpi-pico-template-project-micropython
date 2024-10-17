from machine import ADC, Pin, SPI, I2C
import network
from time import sleep_ms

# Constants
WIFI_DISCONNECTED = 0
WIFI_CONNECTING = 1
WIFI_CONNECTED = 3


class RpiPico:
    # Corrección de temperatura interna para ajustar lecturas.
    INTEGRATED_TEMP_CORRECTION = 27

    # Corrección de voltaje ADC.
    adc_voltage_correction = 0.706

    # Voltaje de trabajo.
    voltage_working = 3.3

    # Estadísticas para la temperatura del procesador.
    cpu_temp_stats = {
        "max": 0.0,
        "min": 0.0,
        "avg": 0.0,
        "current": 0.0,
        "num_of_measurements": 0, # Veces que se ha medido
        "sum_of_temps": 0.0, # Suma de todas las temperaturas medidas
    }

    # Número de mediciones de temperatura.
    num_of_measurements = 0

    max = 0
    min = 0
    avg = 0
    current = 0
    sum_of_temps = 0  # Suma de todas las lecturas de temperatura.

    # Indica si el microcontrolador está bloqueado con una operación delicada.
    locked = False

    # Instancia que representa el Wireless si estuviera establecido.
    wifi = None

    # Configuración de Buses I2C.
    i2c0 = None
    i2c1 = None

    # Configuración de Buses SPI.
    spi0 = None
    spi0_cs = None
    spi1 = None
    spi1_cs = None

    # Lista con todos los callbacks asociados.
    callbacks = []

    # Almaceno batería externa si la configuramos
    external_battery = None

    def __init__ (self, ssid=None, password=None, debug=False, country="ES",
                  alternatives_ap=None, hostname="Rpi-Pico-W"):
        """
        Constructor de la clase para Raspberry Pi Pico W.

        Args:
            ssid (str): ID de red para la conexión Wi-Fi. Por defecto None.
            password (str): Contraseña para la conexión Wi-Fi. Por defecto None.
            debug (bool): Indica si se muestran los mensajes de debug. Por defecto False.
            country (str): Código del país. Por defecto 'ES'.
            alternatives_ap (tuple): Puedes pasar una tupla con redes adicionales.
            hostname (str): Nombre del dispositivo en la red.
        """
        self.locked = True
        self.DEBUG = debug
        self.SSID = ssid
        self.PASSWORD = password
        self.COUNTRY = country
        self.hostname = hostname
        self.alternatives_ap = alternatives_ap

        # Sensor interno de Raspberry Pi Pico para temperatura de CPU.
        self.TEMP_SENSOR = ADC(4)

        # Defino Pin para el LED integrado
        self.LED_INTEGRATED = Pin("LED", Pin.OUT)

        # Factor de conversión de 16 bits para corregir ADC.
        self.adc_conversion_factor = self.voltage_working / 65535

        # Si se proporcionan credenciales del AP intenta la conexión
        if ssid and password:
            if self.DEBUG:
                print('Iniciando la conexión inalámbrica')

            self.wifi_connect(ssid, password)

        sleep_ms(100)

        self.cpu_temperature_reset_stats()
        self.locked = False

    def set_callback_to_pin(self, pin_number, callback, event="HIGH") -> None:
        """
        Configura un callback para un evento de cambio de estado en un pin.

        Args:
            pin_number: Número del pin que representa GPIO.
            callback: Función a ejecutar cuando se detecte el evento.
            event: Estado del pin que activará el callback ("HIGH" o "LOW").

        Raises:
            ValueError: Si ya existe un callback configurado para el pin.
        """

        self.locked = True
        sleep_ms(100)

        # Verifico si ya existe un callback para el pin
        for cb_data in self.callbacks:
            if cb_data["pin"] == pin_number:
                raise ValueError(
                    f"Ya existe un callback configurado para el pin {str(pin_number)}")

        # Configura el pin como entrada con pull-up
        pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        trigger = Pin.IRQ_RISING if event == "HIGH" else Pin.IRQ_FALLING
        pin.irq(trigger=trigger, handler=callback)

        # Agrega el callback a la lista
        self.callbacks.append({
            "pin": pin,
            "callback": callback
        })

        self.locked = False

    def disable_all_callbacks (self):
        """
        Deshabilita todos los callbacks que existan asociados a IRQ.
        :return:
        """
        self.locked = True
        sleep_ms(100)

        for callback_data in self.callbacks:
            callback_data["pin"].irq(trigger=Pin.IRQ_DISABLE)

        self.callbacks.clear()
        self.locked = False

    def set_i2c(self, pin_sda, pin_scl, bus=0, frequency=400000):
        """
        Crea una instancia I2C para la comunicación I2C.

        Args:
            pin_sda: Pin de datos serie (SDA).
            pin_scl: Pin de reloj serie (SCL).
            bus: Bus I2C (0 o 1).
            frequency: Frecuencia de reloj en Hz (por defecto 400000 Hz).

        Returns:
            Instancia I2C configurada.
        """
        if bus > 1:
            return None

        self.locked = True
        sleep_ms(100)

        try:
            i2c = I2C(bus, sda=Pin(pin_sda), scl=Pin(pin_scl), freq=frequency)

            if bus == 0:
                self.i2c0 = i2c
            elif bus == 1:
                self.i2c1 = i2c
        except Exception as e:
            if self.DEBUG:
                print('Error en set_i2c:', e)

            self.locked = False

            return None

        self.locked = False

        return i2c

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
        sleep_ms(100)

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

    def cpu_temperature_reset_stats (self, temp=0.0) -> None:
        """
        Reinicia las estadísticas de temperatura.

        Args:
            temp (float): Valor inicial con el que resetear las estadísticas. Por defecto 0.0.
        """
        temp = temp if temp else self.cpu_temperature_read_sensor()

        self.cpu_temp_stats["num_of_measurements"] = 1
        self.cpu_temp_stats["sum_of_temps"] = temp
        self.cpu_temp_stats["max"] = temp
        self.cpu_temp_stats["min"] = temp
        self.cpu_temp_stats["avg"] = temp
        self.cpu_temp_stats["current"] = temp

    def cpu_temperature_read_sensor (self) -> float:
        """
        Lee la temperatura actual del sensor.

        Returns:
            float: Temperatura leída.
        """
        # Continúa si no está bloqueado
        if self.locked:
            return self.cpu_temp_stats["current"]

        self.locked = True

        reading = (self.TEMP_SENSOR.read_u16() * self.adc_conversion_factor) - self.adc_voltage_correction
        value = self.INTEGRATED_TEMP_CORRECTION - reading / 0.001721

        cpu_temp = round(float(value), 1)
        self.cpu_temp_stats["current"] = cpu_temp

        # Comprueba si supera la máxima registrada.
        if cpu_temp > self.cpu_temp_stats["max"]:
            self.cpu_temp_stats["max"] = cpu_temp

        # Comprueba si es inferior a la mínima registrada.
        if cpu_temp < self.cpu_temp_stats["min"]:
            self.cpu_temp_stats["min"] = cpu_temp

        self.cpu_temp_stats["num_of_measurements"] += 1
        self.cpu_temp_stats["sum_of_temps"] += cpu_temp
        self.cpu_temp_stats["avg"] = round(self.cpu_temp_stats["sum_of_temps"] / self.cpu_temp_stats["num_of_measurements"], 1)

        self.locked = False

        return cpu_temp

    def get_cpu_temperature (self) -> float:
        """
        Obtiene la temperatura actual.

        Returns:
            float: Temperatura actual.
        """
        return self.cpu_temperature_read_sensor()

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

    def get_cpu_temperature_stats (self) -> dict:
        """
        Obtiene las estadísticas actuales de temperatura.

        Returns:
            dict: Contiene la temperatura máxima, mínima, promedio y actual.
        """
        return self.cpu_temp_stats

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

            sleep_ms(1000)

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

    def read_external_battery (self):
        min_voltage = self.external_battery["threshold_voltage_min"]
        max_voltage = self.external_battery["threshold_voltage_max"]
        adc = self.external_battery["adc"]
        adc_value = adc.read_u16()

        # Convierto la lectura a voltaje
        voltage = adc_value * (max_voltage / 65535)

        percentage_raw = ((voltage - min_voltage) / (max_voltage -  min_voltage)* 100)

        percentage =  max(0.0, min(percentage_raw, 100.0))

        self.external_battery["voltage_current"] = voltage
        self.external_battery["voltage_percentage"] = percentage

        if self.external_battery["voltage_min"] is None or voltage < self.external_battery["voltage_min"]:
            self.external_battery["voltage_min"] = voltage
            self.external_battery["voltage_percentage_min"] = percentage

        if (self.external_battery["voltage_max"] is None or voltage > self.external_battery["voltage_max"]):
            self.external_battery["voltage_max"] = voltage
            self.external_battery["voltage_percentage_max"] = percentage

        return self.external_battery

    def set_external_battery(self, pin, threshold_voltage_min=2.5, threshold_voltage_max=4.2):
        self.external_battery = {
            "pin": pin,
            "adc": ADC(pin),
            "threshold_voltage_min": threshold_voltage_min,
            "threshold_voltage_max": threshold_voltage_max,
            "voltage_current": None,
            "voltage_min": None,
            "voltage_max": None,
            "voltage_percentage": None,
            "voltage_percentage_min": None,
            "voltage_percentage_max": None,
        }

        self.read_external_battery()