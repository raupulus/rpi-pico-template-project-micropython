#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import urequests
#import ujson


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

    def send_to_api (self) -> bool:
        """
        Guarda los datos en la API.
        :return:
        """
        try:

            headers = {
                "Authorization": "Bearer " + self.TOKEN,
                "Device-Id": str(self.DEVICE_ID)
            }

            url = self.URL + self.URL_PATH

            # TODO: esto tiene que hacerse POST y enviar hardware_device_id

            response = urequests.get(url, headers=headers)

            #data = ujson.loads(response.text)

            if self.DEBUG:
                print('Respuesta de la API:', response)
            if response.status_code == 201:
                return True

        except Exception as e:
            if self.DEBUG:
                print("Error al obtener los datos de la api: ", e)
            return False
