#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import urequests
import ujson

try:
    from time import sleep_ms  # type: ignore
except ImportError:
    def sleep_ms(ms):
        import time
        time.sleep(ms / 1000)


class Api:
    """
    A class representing an API connection with methods to interact with the endpoint.

    :param controller: The controller object for raspberry pi pico.
    :param url: The base URL of the API.
    :param path: The specific path for the API endpoint.
    :param token: The authentication token for accessing the API.
    :param device_id: The unique identifier of the device.
    :param debug: Optional boolean flag for debugging mode.
    """

    # Número de reintentos en caso de fallo de conexión (ECONNABORTED, OSError, etc.)
    MAX_RETRIES = 3
    # Espera entre reintentos (ms). Aumenta con cada intento: 2s, 4s, 6s
    RETRY_DELAY_MS = 2000

    def __init__ (self, controller, url, path, token, device_id, debug=False):
        self.URL = url
        self.TOKEN = token
        self.DEVICE_ID = device_id
        self.URL_PATH = path
        self.CONTROLLER = controller
        self.DEBUG = debug

    def _build_url(self):
        return self.URL.rstrip('/') + '/' + self.URL_PATH.lstrip('/')

    def _reconnect_wifi(self):
        """Intenta reconectar el WiFi si está disponible en el controlador."""
        try:
            if self.CONTROLLER and not self.CONTROLLER.wifi_is_connected():
                if self.DEBUG:
                    print('API: WiFi caído, intentando reconectar...')
                self.CONTROLLER.wifi_connect()
                sleep_ms(1500)
                if self.DEBUG:
                    connected = self.CONTROLLER.wifi_is_connected()
                    print('API: WiFi reconectado:', connected)
        except Exception as e:
            if self.DEBUG:
                print('API: error al reconectar WiFi:', e)

    def get_data_from_api(self):
        try:
            headers = {
                "Authorization": "Bearer " + self.TOKEN,
                "Content-Type": "application/json",
                "Device-Id": str(self.DEVICE_ID)
            }

            url = self._build_url()
            response = urequests.get(url, headers=headers)

            if self.DEBUG:
                print('API HTTP', response.status_code, url)

            if response.status_code == 200:
                data = ujson.loads(response.text)
                if self.DEBUG:
                    print('API json:', data)
                try:
                    response.close()
                except Exception:
                    pass
                return data

            if self.DEBUG:
                try:
                    print('API body:', response.text[:300])
                except Exception:
                    pass
                print('API fallo — código esperado 200, recibido', response.status_code)

            try:
                response.close()
            except Exception:
                pass
            return False

        except Exception as e:
            if self.DEBUG:
                print('API excepción al obtener:', e)
            return False

    def send_to_api(self, data={}) -> bool:
        """
        Envía los datos a la API mediante una petición POST con reintentos.

        En caso de error de conexión (ECONNABORTED, OSError, etc.) reintenta
        hasta MAX_RETRIES veces, esperando RETRY_DELAY_MS * intento entre cada
        uno y reconectando el WiFi si es necesario.

        Args:
            data: Diccionario con los datos a enviar.

        Returns:
            bool: True si la petición fue exitosa (HTTP 201), False en caso contrario.
        """
        url = self._build_url()
        headers = {
            "Authorization": "Bearer " + self.TOKEN,
            "Content-Type": "application/json"
        }
        # Filtra None de data antes de construir el payload
        clean_data = {k: v for k, v in data.items() if v is not None} if isinstance(data, dict) else data
        # Añade moisture=0.0 si la estación no tiene ese sensor
        if isinstance(clean_data, dict):
            clean_data['moisture'] = clean_data.get('moisture', 0.0)
        payload = {"data": clean_data, "hardware_device_id": self.DEVICE_ID, "moisture": 0.0}
        if isinstance(clean_data, dict):
            payload.update(clean_data)

        if self.DEBUG:
            print('API payload:', payload)

        for attempt in range(1, self.MAX_RETRIES + 1):
            response = None
            try:
                if self.DEBUG and attempt > 1:
                    print('API reintento', attempt, '/', self.MAX_RETRIES)

                response = urequests.post(url, headers=headers, json=payload)

                if self.DEBUG:
                    print('API HTTP', response.status_code, '(intento', attempt, ')', url)
                    try:
                        body = response.text
                        print('API body:', body[:400] if len(body) > 400 else body)
                    except Exception as e_body:
                        print('API body (error leyendo):', e_body)

                ok = response.status_code in (200, 201)

                # TODO: eliminar aceptación de 200 cuando la API devuelva 201 correctamente
                if self.DEBUG and response.status_code == 200:
                    print('API ADVERTENCIA: respuesta 200 aceptada temporalmente (la API debería devolver 201)')

                if self.DEBUG and not ok:
                    print('API fallo — código esperado 201, recibido', response.status_code)

                try:
                    response.close()
                except Exception:
                    pass

                if ok:
                    return True

                # Error HTTP (4xx/5xx): no tiene sentido reintentar con los mismos datos
                return False

            except OSError as e:
                # ECONNABORTED=103, ECONNRESET=104, ETIMEDOUT=110, etc.
                err_num = e.args[0] if e.args else 0
                if self.DEBUG:
                    print('API OSError errno={} intento={}: {}'.format(err_num, attempt, e))
                try:
                    if response:
                        response.close()
                except Exception:
                    pass
                if attempt < self.MAX_RETRIES:
                    self._reconnect_wifi()
                    sleep_ms(self.RETRY_DELAY_MS * attempt)
                else:
                    if self.DEBUG:
                        print('API: máximo de reintentos alcanzado, descartando payload')

            except Exception as e:
                if self.DEBUG:
                    print('API excepción al enviar (intento {}): {}'.format(attempt, e))
                try:
                    if response:
                        response.close()
                except Exception:
                    pass
                if attempt < self.MAX_RETRIES:
                    sleep_ms(self.RETRY_DELAY_MS * attempt)
                else:
                    if self.DEBUG:
                        print('API: máximo de reintentos alcanzado, descartando payload')

        return False
