# Fundamentos: API Raupulus WeatherStation (V2)

> **Fuentes**: Contrato oficial API V2 `https://api.raupulus.dev/api/v2`.  
> **Fecha de verificación real**: 2026-09-06

## 1. Base URL y Envelope Común

- **Base URL**: `/api/v2` (típicamente `https://api.raupulus.dev/api/v2`).
- **Formato de respuesta universal**:
  ```json
  // Éxito
  { "success": true, "message": "Operación exitosa", "data": { ... } }
  // Error
  { "success": false, "message": "Descripción del error", "errors": { ... } }
  ```

## 2. Autenticación y Permisos

- **Mecanismo**: Laravel Sanctum, cabecera `Authorization: Bearer <token>`.
- **Lecturas (`GET`)**: Públicas, no requieren token.
- **Escrituras (`POST`)**: Requieren token de dispositivo IoT con la ability `weatherstation:write`, emitido desde `/auth/tokens/devices` y ligado a la estación (`device:{id}`).

## 3. Códigos de Estado HTTP

- `201 Created`: Inserción correcta de lecturas (tanto individual como lote multi-sensor). Devuelve `{"stored": <n>}`.
- `200 OK`: Peticiones de lectura exitosas.
- `401 Unauthorized`: Token ausente, caducado o inválido.
- `403 Forbidden`: Token sin la ability `weatherstation:write` o no asignado a la estación especificada en la ruta.
- `404 Not Found`: Endpoint inexistente o estación no encontrada (`{"success": false, "message": "API V2 - Endpoint no encontrado"}`).
- `422 Unprocessable Entity`: Error de validación (clave de sensor desconocida, campos requeridos faltantes, tipos incorrectos).
- `429 Too Many Requests`: Límite de tasa superado (por defecto 20 peticiones/min para el endpoint de lote).

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
