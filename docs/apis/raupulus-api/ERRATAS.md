# Erratas y Compatibilidad: API Raupulus WeatherStation

> **Fuentes**: Verificación de respuestas del servidor con `urequests`.  
> **Fecha de verificación real**: 2026-09-06

## 1. Claves duplicadas en nivel raíz y bajo `data`
- **Comportamiento**: Versiones anteriores de la API requerían que todas las métricas estuvieran bajo la clave `"data"`. Las revisiones modernas aceptan las variables a nivel de raíz.
- **Solución implementada**: El firmware suministra ambos esquemas simultáneamente en el mismo JSON para mantener compatibilidad total sin requerir adaptaciones en el backend.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
