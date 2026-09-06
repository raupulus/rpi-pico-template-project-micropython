# Iniciativa Aplazada: Integración de Pantalla ST7735 y Botones de Usuario

> **Estado**: Decidido pero aplazado (no es deuda técnica ni bug).  
> **Área**: Hardware / Interfaz local

## 1. Contexto y Motivo
El código fuente contiene comentarios preparatorios para incorporar una pantalla TFT a color ST7735 por bus SPI y un pulsador de control en `GPIO2`. El objetivo planteado es poder visualizar la última lectura de temperatura, humedad, ráfaga y lluvia directamente en el chasis físico del receptor sin necesidad de acceder a la web.

## 2. Decisiones Aplazadas
- **Compartición de Bus SPI**: Evaluar si la pantalla compartirá `SPI0` con el transceptor CC1101 alternando las líneas de Chip Select (`CS`), o si se utilizará el controlador secundario `SPI1` para aislar el tráfico de la radio.
- **Mapeo de Pines del Botón 1**: `GP2` con interrupción por flanco de bajada para alternar entre diferentes pantallas de estadísticas (resumen actual, máximos/mínimos, estado de conexión Wi-Fi).

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
