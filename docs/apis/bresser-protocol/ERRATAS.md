# Erratas: Protocolo Bresser RF

> **Fuentes**: Análisis de paquetes reales capturados por CC1101 y repositorio `old_c_project/`.  
> **Fecha de verificación real**: 2026-09-06

## 1. Byte de sincronismo capturado como payload (5-en-1)
- **Problema**: Dependiendo de si el receptor CC1101 sincroniza con `0xAA 0x2D` o con `0x2D 0xD4`, el byte `0xD4` aparece con frecuencia como el primer byte del payload de 27 bytes en el buffer.
- **Corrección verificada**: El decodificador comprueba si el primer byte es `0xD4` y el tamaño es 27 bytes; de ser así, toma la porción `packet[1:27]` para analizar los 26 bytes canónicos.

## 2. Rango de temperatura negativa en 6-en-1
- **Problema**: Varios documentos públicos afirman que la temperatura en 6-en-1 utiliza un bit de signo estándar en el bit más significativo.
- **Corrección verificada**: Si el valor desempaquetado BCD (`raw`) es superior a 600 (por ejemplo 950 para -5.0°C), el cálculo real es `(raw - 1000) * 0.1`.

## 3. Escala del pluviómetro en 5-en-1
- **Problema**: Algunos pluviómetros Bresser profesionales con sensor tipo `0x39`, `0x3A` o `0x3B` emiten pasos mecánicos de balancín correspondientes a 0.25 mm y no a 0.1 mm.
- **Corrección verificada**: Se debe aplicar un multiplicador de 2.5 al valor BCD deserializado en dichos tipos de estación.

---
> Creado: 2026-09-06 · Última revisión: 2026-09-06
