import ujson
import urequests
import time

try:
    from time import sleep_ms
except ImportError:
    def sleep_ms(ms):
        time.sleep(ms / 1000)

# Configurar timeout predeterminado para sockets de red (evita cuelgues indefinidos)
try:
    import usocket as socket
    socket.setdefaulttimeout(6.0)
except Exception:
    try:
        import socket
        socket.setdefaulttimeout(6.0)
    except Exception:
        pass


def degrees_to_cardinal(deg):
    """Convierte grados (0-360) a dirección cardinal de 16 rumbos."""
    if deg is None:
        return "N"
    try:
        val = int((float(deg) + 11.25) / 22.5) % 16
        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ]
        return directions[val]
    except Exception:
        return "N"


class Api:
    """
    Cliente HTTP para la API V2 de la estación meteorológica.

    :param controller: Objeto controlador de Raspberry Pi Pico (RpiPico).
    :param url: URL base de la API (ej: https://api.raupulus.dev/api/v2).
    :param path: Ruta del endpoint (ej: weather-stations/{station}/readings).
    :param token: Token Bearer con ability weatherstation:write.
    :param device_id: Identificador numérico de la estación en la API.
    :param debug: Flag booleano para trazas de depuración.
    """

    MAX_RETRIES = 3
    RETRY_DELAY_MS = 2000

    def __init__(self, controller, url, path, token, device_id, debug=False):
        self.URL = url
        self.TOKEN = token
        self.DEVICE_ID = device_id
        self.URL_PATH = path
        self.CONTROLLER = controller
        self.DEBUG = debug

    def _build_url(self):
        path = self.URL_PATH.replace('{station}', str(self.DEVICE_ID)).replace('{device_id}', str(self.DEVICE_ID))
        return self.URL.rstrip('/') + '/' + path.lstrip('/')

    def _build_station_url(self):
        return self.URL.rstrip('/') + '/weather-stations/' + str(self.DEVICE_ID)

    def _feed_wdt(self):
        """Alimenta el watchdog del controlador si está disponible."""
        if self.CONTROLLER and hasattr(self.CONTROLLER, 'feed_wdt'):
            self.CONTROLLER.feed_wdt()

    def _reconnect_wifi(self):
        """Intenta reconectar el WiFi si está disponible en el controlador sin bloquear indefinidamente."""
        if not self.CONTROLLER:
            return
        try:
            if hasattr(self.CONTROLLER, 'wifi_is_connected') and not self.CONTROLLER.wifi_is_connected():
                if self.DEBUG:
                    print('API: WiFi desconectado, intentando reconectar...')
                if hasattr(self.CONTROLLER, 'wifi_connect'):
                    self.CONTROLLER.wifi_connect(max_retries=2)
        except Exception as e:
            if self.DEBUG:
                print('API: error al reconectar WiFi:', e)

    def _build_hardware_device_info(self):
        """Recopila telemetría de hardware del controlador para hardware_device_info."""
        if not self.CONTROLLER:
            return None
        info = {}
        try:
            temp = self.CONTROLLER.get_cpu_temperature()
            if temp is not None:
                info['temp'] = round(float(temp), 2)
        except Exception:
            pass
        try:
            wip = self.CONTROLLER.get_wireless_ip()
            if wip and wip != '0.0.0.0':
                info['ip_local'] = wip
        except Exception:
            pass
        try:
            uptime = self.CONTROLLER.get_uptime()
            if uptime is not None:
                info['uptime'] = int(uptime)
        except Exception:
            pass
        try:
            disk = self.CONTROLLER.get_disk_usage()
            if disk is not None:
                info['disk'] = round(float(disk), 1)
        except Exception:
            pass
        try:
            if hasattr(self.CONTROLLER, 'get_ram_usage'):
                ram = self.CONTROLLER.get_ram_usage()
            else:
                import gc
                alloc = gc.mem_alloc()
                free = gc.mem_free()
                total = alloc + free
                ram = round((alloc / total) * 100.0, 1) if total > 0 else 0.0
            if ram is not None:
                info['ram'] = round(float(ram), 1)
        except Exception:
            pass
        try:
            extra = {}
            rssi = self.CONTROLLER.get_wireless_rssi()
            if rssi:
                extra['rssi'] = int(rssi)
            mac = self.CONTROLLER.get_wireless_mac()
            if mac and mac != '00:00:00:00:00:00':
                extra['mac'] = mac
            try:
                import machine
                extra['cpu_freq_mhz'] = int(machine.freq() // 1000000)
                if hasattr(machine, 'reset_cause'):
                    extra['reset_cause'] = int(machine.reset_cause())
            except Exception:
                pass
            if extra:
                info['extra'] = extra
        except Exception:
            pass

        return info if info else None

    def _build_v2_payload(self, data):
        """
        Transforma el diccionario de lecturas del agregador al contrato V2
        del endpoint multi-sensor: POST /weather-stations/{station}/readings.
        """
        sensors_data = {}

        # 1. Temperatura
        if data.get('temperature') is not None:
            sensors_data['temperature'] = [{'value': round(float(data['temperature']), 2)}]

        # 2. Humedad
        if data.get('humidity') is not None:
            sensors_data['humidity'] = [{'value': round(float(data['humidity']), 2)}]

        # 3. Viento (velocidad)
        w_speed = data.get('wind_speed')
        w_avg = data.get('wind_average_speed')
        if w_speed is not None or w_avg is not None:
            speed = max(0.0, float(w_speed if w_speed is not None else w_avg))
            average = max(0.0, float(w_avg if w_avg is not None else speed))
            min_speed = max(0.0, float(data.get('wind_min_speed', average) if data.get('wind_min_speed') is not None else average))
            max_speed = max(0.0, float(data.get('wind_max_speed', speed) if data.get('wind_max_speed') is not None else speed))
            sensors_data['wind'] = [{
                'speed': round(speed, 2),
                'average': round(average, 2),
                'min': round(min_speed, 2),
                'max': round(max_speed, 2)
            }]

        # 4. Dirección del viento
        w_grades = data.get('wind_grades')
        if w_grades is not None:
            grades = float(w_grades) % 360.0
            direction = degrees_to_cardinal(grades)
            sensors_data['wind_direction'] = [{
                'direction': direction,
                'grades': round(grades, 1)
            }]

        # 5. Precipitación / Lluvia
        rain_val = data.get('rain')
        if rain_val is not None:
            rain_entry = {
                'rain': max(0.0, round(float(rain_val), 2)),
                'moisture': round(float(data.get('moisture', 0.0) or 0.0), 2)
            }
            if data.get('rain_intensity') is not None:
                rain_entry['rain_intensity'] = max(0.0, round(float(data['rain_intensity']), 2))
            if data.get('rain_month') is not None:
                rain_entry['rain_month'] = max(0.0, round(float(data['rain_month']), 2))
            sensors_data['rain'] = [rain_entry]

        payload = {'data': sensors_data}

        # Información opcional del dispositivo en la raíz
        hw_info = self._build_hardware_device_info()
        if hw_info:
            payload['hardware_device_info'] = hw_info

        return payload

    def get_data_from_api(self):
        """Consulta el estado de la estación en GET /weather-stations/{station}."""
        try:
            self._feed_wdt()
            headers = {
                "Authorization": "Bearer " + self.TOKEN,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            url = self._build_station_url()
            response = urequests.get(url, headers=headers)

            if self.DEBUG:
                print('API GET status:', response.status_code)

            if response.status_code == 200:
                data = response.json()
                response.close()
                return data
            else:
                response.close()
                return None
        except Exception as e:
            if self.DEBUG:
                print('API GET error:', e)
            return None

    def send_to_api(self, data={}) -> bool:
        """
        Envía las lecturas a la API V2 mediante POST /weather-stations/{station}/readings con reintentos.

        :param data: Diccionario con las lecturas agregadas de los sensores.
        :return: True si la petición fue exitosa (HTTP 201), False en caso contrario.
        """
        self._feed_wdt()
        url = self._build_url()
        headers = {
            "Authorization": "Bearer " + self.TOKEN,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = self._build_v2_payload(data)

        # Si no hay ningún sensor con datos válidos, descartar envío
        if not payload.get('data'):
            if self.DEBUG:
                print('API: payload sin lecturas válidas, se omite envío')
            return False

        if self.DEBUG:
            print('API V2 endpoint:', url)
            print('API V2 payload:', payload)

        for attempt in range(1, self.MAX_RETRIES + 1):
            self._feed_wdt()
            response = None
            try:
                # Comprobar estado WiFi antes de enviar; si está caído, intentar reconectar
                if self.CONTROLLER and hasattr(self.CONTROLLER, 'wifi_is_connected') and not self.CONTROLLER.wifi_is_connected():
                    if self.DEBUG:
                        print('API: detectada caída de WiFi antes de POST, reconectando...')
                    self._reconnect_wifi()

                self._feed_wdt()
                response = urequests.post(
                    url,
                    headers=headers,
                    data=ujson.dumps(payload)
                )

                self._feed_wdt()
                ok = response.status_code in (200, 201)

                if self.DEBUG and not ok:
                    print('API fallo — código esperado 201, recibido', response.status_code)

                try:
                    response.close()
                except Exception:
                    pass

                if ok:
                    return True

                # Error 4xx/5xx: no reintentar el mismo payload inválido
                return False

            except OSError as e:
                err_num = e.args[0] if e.args else 0
                if self.DEBUG:
                    print('API OSError errno={} intento={}: {}'.format(err_num, attempt, e))

                if response is not None:
                    try:
                        response.close()
                    except Exception:
                        pass

                if attempt < self.MAX_RETRIES:
                    self._reconnect_wifi()
                    delay = self.RETRY_DELAY_MS * attempt
                    # Pausa progresiva alimentando el watchdog
                    slept = 0
                    while slept < delay:
                        chunk = min(500, delay - slept)
                        sleep_ms(chunk)
                        slept += chunk
                        self._feed_wdt()

            except Exception as e:
                if self.DEBUG:
                    print('API error inesperado en intento {}: {}'.format(attempt, e))
                if response is not None:
                    try:
                        response.close()
                    except Exception:
                        pass
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY_MS * attempt
                    slept = 0
                    while slept < delay:
                        chunk = min(500, delay - slept)
                        sleep_ms(chunk)
                        slept += chunk
                        self._feed_wdt()

        return False
