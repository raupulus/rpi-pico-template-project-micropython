#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import urequests
import ujson


def get_time_utc ():
    """Obtiene la hora actual en formato UTC desde la API 'worldtimeapi.org'."""
    try:
        response = urequests.get('http://worldtimeapi.org/api/timezone/Etc/UTC.json')
        data = response.json()
        response.close()

        # Extraer la fecha y hora en formato 'YYYY-MM-DDTHH:MM:SS.ssssss+00:00'
        datetime_str = data['datetime']
        # El formato es '2024-11-11T06:20:25.522376+00:00'
        datetime_parts = datetime_str.split('T')  # Divide 'YYYY-MM-DD' y 'HH:MM:SS.ssssss+00:00'
        date_part = datetime_parts[0]  # '2024-11-11'
        time_part = datetime_parts[1].split('+')[0]  # '06:20:25.522376' (ignoramos la zona horaria)

        # Desglosar la fecha
        year, month, day = map(int, date_part.split('-'))

        # Desglosar la hora (tomando solo hora, minuto y segundo)
        time_parts = time_part.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(float(time_parts[2]))  # Convertimos la parte de los segundos en entero

        # Información adicional
        day_of_week = data['day_of_week']
        day_of_year = data['day_of_year']
        week_number = data['week_number']

        return year, month, day, hour, minute, second, day_of_week, day_of_year, week_number

    except Exception as e:
        print("Error obtaining the time from the API:", e)
        return None


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

    def __init__ (self, controller, url, path, token, device_id, debug=False):
        self.URL = url
        self.TOKEN = token
        self.DEVICE_ID = device_id
        self.URL_PATH = path
        self.CONTROLLER = controller
        self.DEBUG = debug

    def get_data_from_api (self):
        try:

            headers = {
                "Authorization": "Bearer " + self.TOKEN,
                "Content-Type": "application/json",
                "Device-Id": str(self.DEVICE_ID)
            }

            url = self.URL + self.URL_PATH

            response = urequests.get(url, headers=headers)

            data = ujson.loads(response.text)

            if self.DEBUG:
                print('Respuesta de la API:', response)
                print('Respuesta de la API en json:', data)

            if response.status_code == 201:
                return data

        except Exception as e:
            if self.DEBUG:
                print("Error al obtener los datos de la api: ", e)
            return False

    def send_to_api (self, data={}) -> bool:
        """
        Envía los datos a la API mediante una petición POST.

        Args:
            data: Diccionario con los datos a enviar.

        Returns:
            bool: True si la petición fue exitosa, False en caso contrario.
        """
        try:
            headers = {
                "Authorization": "Bearer " + self.TOKEN,
                "Content-Type": "application/json"
            }

            url = self.URL + self.URL_PATH

            payload = {
                "data": data,
                "hardware_device_id": self.DEVICE_ID
            }

            response = urequests.post(url, headers=headers, json=payload)
            #data = ujson.loads(response.text)

            if self.DEBUG:
                print('Respuesta de la API:', response)

            if response.status_code == 201:
                return True

        except Exception as e:
            if self.DEBUG:
                print("Error al obtener los datos de la api: ", e)

            return False
