# Fundamentos: API Raupulus WeatherStation

> **Fuentes**: API REST `https://api.raupulus.dev`.  
> **Fecha de verificación real**: 2026-09-06

## 1. Autenticación

El servicio requiere autenticación mediante token de portador (Bearer Token):
```http
Authorization: Bearer <API_TOKEN>
```

## 2. Formato de Envío

- **Protocolo**: HTTPS (TLS 1.2 / 1.3).
- **Content-Type**: `application/json`.
- **Accept**: `application/json`.

## 3. Códigos de Respuesta

- `201 Created`: Telemetría guardada satisfactoriamente en base de datos.
- `200 OK`: Aceptado.
- `401 Unauthorized`: Token no proporcionado o inválido.
- `422 Unprocessable Entity`: Error de validación en los campos del JSON.
- `500 Internal Server Error`: Fallo interno del backend.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
