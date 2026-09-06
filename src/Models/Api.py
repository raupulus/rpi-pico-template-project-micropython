#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import urequests
import ujson


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
