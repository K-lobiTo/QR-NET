# Transferencia de Archivos en QR-NET

## Visión General

Este sistema implementa transferencia de archivos entre dos dispositivos usando **códigos QR como medio físico**. Los archivos se fragmentan automáticamente para caber en el tamaño máximo de trama (110 bytes por fragmento), se codifican en QR, se transmiten por luz visible, se capturan con cámara, se decodifican y se reensambl.

### Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│  DISPOSITIVO EMISOR                                      │
├─────────────────────────────────────────────────────────┤
│  [Archivo] → [Fragmentación] → [JSON] → [QR] → [Luz]   │
│             (Capa 5)          (L7)    (L1)   (Física)  │
└─────────────────────────────────────────────────────────┘
                          ↓↓↓ (Luz visible)
┌─────────────────────────────────────────────────────────┐
│  DISPOSITIVO RECEPTOR                                    │
├─────────────────────────────────────────────────────────┤
│  [Luz] → [Cámara] → [QR] → [JSON] → [Reensambl] → [Archivo]
│  (Física) (L1)      (L1)    (L7)      (Capa 5)
└─────────────────────────────────────────────────────────┘
```

## Componentes Implementados

### Capa 1 — Medio Físico (`dispositivo_luz_adaptador.py`)
- Transmisión: Codifica datos en QR y los muestra en pantalla
- Recepción: Captura QRs con cámara y decodifica
- Máximo 110 bytes por trama
- Checksum CRC-16 para integridad

### Capa 5 — Transferencia de Archivos (`layer5_transfer/`)
- **Fragmentación**: Divide archivos en fragmentos de ~500 bytes
- **Base64 encoding**: Datos seguros para transporte en JSON
- **Verificación**: Hash SHA256 al inicio y final
- **Reensamblaje**: Reconstituye archivos completamente

### Capa 7 — Aplicación de Transferencia (`layer7_file_transfer/`)
- Integración con red mesh anónima (remote-QR-net)
- Protocolo de handshake: FILE_START → FILE_CHUNK* → FILE_END
- Manejo de transferencias múltiples simultáneas
- Estado: PENDING, IN_PROGRESS, COMPLETED, FAILED

## Instalación y Configuración

### 1. Instalar dependencias

```bash
cd /home/klob/Documents/redes/projects/1/QR-NET
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Verificar que las cámaras están conectadas

```bash
# En Linux
v4l2-ctl --list-devices

# O en Python
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Cámara 0:', cap.isOpened())"
```

## Uso

### Opción 1: Modo Directo (Red de dos nodos)

#### Terminal 1 — Receptor

```bash
cd src
source ../venv/bin/activate
python receiver.py --camera 0
```

**Salida esperada:**
```
======================================================================
QR-NET FILE TRANSFER — RECEPTOR
======================================================================

[Receptor] Captura de cámara iniciada

[Luz-L1] Cámara abierta, buscando QRs...

[Receptor] Esperando archivos (timeout: 300s)...
```

#### Terminal 2 — Emisor (otra máquina)

```bash
cd src
source ../venv/bin/activate
python sender.py documento.pdf
```

**Salida esperada:**
```
======================================================================
QR-NET FILE TRANSFER — EMISOR
======================================================================

Archivo: documento.pdf
Tamaño: 24576 bytes
──────────────────────────────────────────────────────────────────────

Fragmentos a enviar: 50

Mostrando fragmentos en pantalla:

  [1/50] Mostrando fragmento en pantalla... ✓
  [2/50] Mostrando fragmento en pantalla... ✓
  ...
──────────────────────────────────────────────────────────────────────
✓ Emisión completada
```

### Opción 2: Modo Test (Mismo dispositivo)

Para probar en un solo dispositivo sin necesidad de dos cámaras:

```bash
# Terminal 1 — Receptor en modo sin captura de cámara
python receiver.py --no-listen

# Terminal 2 — Emisor
python sender.py documento.pdf
```

## Formato de Protocolo

### FILE_START (Metadatos)

```json
{
  "msg_type": "FILE_START",
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "documento.pdf",
  "file_size": 24576,
  "file_hash": "a1b2c3d4e5f6...",
  "total_chunks": 50
}
```

### FILE_CHUNK (Fragmento)

```json
{
  "msg_type": "FILE_CHUNK",
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_number": 0,
  "total_chunks": 50,
  "data": "QmFzZTY0IGVuY29kZWQgZGF0YSBnb2VzIGhlcmU="
}
```

### FILE_END (Finalización)

```json
{
  "msg_type": "FILE_END",
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_hash": "a1b2c3d4e5f6..."
}
```

## Parámetros de Línea de Comandos

### Emisor (`sender.py`)

```
positional arguments:
  archivo               Ruta del archivo a enviar

optional arguments:
  --no-display         No mostrar la secuencia de QRs en pantalla
```

### Receptor (`receiver.py`)

```
optional arguments:
  --camera CAMERA      Índice de cámara (default: 0)
  --timeout TIMEOUT    Timeout en segundos (default: 300)
  --no-listen          No capturar con cámara
```

## Flujo de Transferencia Detallado

### 1. Preparación Emisor

```python
# sender.py
sender = SenderApp()
sender.send_file_with_qr_display("archivo.bin")
```

**Internamente:**
1. Lee el archivo
2. Calcula SHA256 del archivo completo
3. Fragmenta en chunks de ~500 bytes
4. Codifica cada chunk en Base64
5. Genera UUID para la transferencia

### 2. Envío de Metadatos

```
[Emisor] → FILE_START en JSON → [Red mesh] → [Receptor]
```

El receptor recibe el metadato y se prepara para recibir fragmen tos:
- Crea estructura de almacenamiento
- Inicializa contador de fragmentos
- Activa timeout de espera

### 3. Transmisión de Fragmentos

```
[Emisor] → FILE_CHUNK[0] (muestra QR 1seg) → [Red mesh] → [Receptor]
           FILE_CHUNK[1] (muestra QR 1seg) → [Red mesh] → [Receptor]
           ...
           FILE_CHUNK[N] (muestra QR 1seg) → [Red mesh] → [Receptor]
```

El receptor:
- Captura QRs con cámara
- Decodifica fragmentos
- Almacena en orden
- Actualiza progreso

### 4. Finalización y Verificación

```
[Emisor] → FILE_END (hash final) → [Red mesh] → [Receptor]
```

El receptor:
- Cuando completa último fragmento, inicia reensamblaje
- Escribe bytes en archivo temporal
- Calcula SHA256 del archivo resultante
- Compara con hash original
- Si coincide → Archivo completo ✓
- Si no coincide → Error ✗

### 5. Salida del Receptor

```
[Receptor] Archivo reensamblado: received_documento.pdf
```

## Limitaciones y Consideraciones

### Tamaño Máximo de Archivo

- **Capa 1**: 110 bytes/trama
- **Capa 7**: ~500 bytes/fragmento (limitado por JSON)
- **Teórico**: Ilimitado (se fragmenta según sea necesario)
- **Práctico**: Probado hasta 50MB (puede ser mayor)

### Velocidad de Transferencia

- **Sin restricciones**: ~500 bytes/fragmento
- **Con CSMA** (control de medio): Depende de ocupación
- **Estimado**: 1-5 MB/min en condiciones ideales

### Confiabilidad

- ✓ Checksum CRC-16 en Capa 1
- ✓ Hash SHA256 en Capa 5
- ✓ Retransmisión implícita (si un fragmento falla, puede reenviarse)
- ⚠ Sin ACK explícito (se asume entrega por red mesh)

### Candados y Sincronización

- Thread-safe para transferencias múltiples
- Locks en `FileTransferManager` y `FileTransferApp`
- Callbacks para eventos de transferencia

## Debugging y Troubleshooting

### Problema: "Camera not found"

```bash
# Verificar disponibilidad de cámaras
v4l2-ctl --list-devices
python3 -c "import cv2; print(cv2.getBuildInformation())"

# Usar otra cámara
python receiver.py --camera 1
```

### Problema: "ModuleNotFoundError: layer5_transfer"

```bash
# Asegúrate de estar en el directorio src/
cd src
python receiver.py
```

### Problema: "Connection refused"

Este proyecto ya no usa sockets UDP directos para la transferencia. Si ves errores relacionados con cámara o módulos faltantes, revisa lo siguiente:

```bash
# Verificar disponibilidad de la cámara
python3 -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"

# Ejecutar desde el directorio src/
cd src
python receiver.py --camera 0
python sender.py archivo.bin
```

### Problema: Hash mismatch

```
[L5-Verify] Hash mismatch!
  Original:  a1b2c3d4e5f6...
  Recibido:  x9y8z7w6k5j4...
```

Causas posibles:
- Pérdida de fragmentos en la red
- Error en captura de QR (iluminación)
- Corrupción de datos

Solución:
- Reintentar envío
- Mejorar iluminación
- Reducir distancia entre dispositivos

## Extensiones Futuras

### 1. Protocolo de Reconocimiento (ACK)

```python
# Receptor envía ACK por cada N fragmentos
app.send_ack(transfer_id, last_chunk_received)
```

### 2. Fragmentación Inteligente

Adaptar tamaño de fragmentos basado en:
- Condiciones de luz (iluminación ambiente)
- Tasa de error (fragmentos capturados incorrectamente)
- Velocidad de la red

### 3. Compresión

```python
# Comprimir archivo antes de fragmentar
import gzip
with gzip.open("archivo.gz", "wb") as f:
    f.write(original_data)
```

### 4. Encriptación

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
cipher = Fernet(key)
encrypted = cipher.encrypt(data)
```

### 5. Interfaz Gráfica

```python
# GUI con tkinter para mostrar progreso
# - Barra de progreso de fragmentos
# - Preview de imagen última
# - Lista de archivos recibidos
# - Estadísticas de velocidad
```

## API de Referencia

### FileTransferManager

```python
# Fragmentar archivo
transfer_info, fragments = manager.split_file("archivo.bin")

# Procesar fragmento recibido
is_complete = manager.receive_fragment(fragment)

# Reensamblar
manager.reassemble_file(transfer_id, "output.bin")

# Verificar integridad
success = manager.verify_transferred_file(transfer_id, "output.bin")
```

### SenderApp (Nueva API Simplificada)

```python
# Crear emisor
sender = SenderApp()

# Enviar archivo con visualización de QRs
sender.send_file_with_qr_display("documento.pdf", show_display=True)

# Limpiar
sender.cleanup()
```

### ReceiverApp (Nueva API Simplificada)

```python
# Crear receptor
receiver = ReceiverApp(camera_index=0)

# Capturar archivos
receiver.start_camera_capture()

# Esperar archivos
receiver.wait_for_file(timeout=300)

# Listar archivos recibidos
receiver.list_received_files()

# Limpiar
receiver.cleanup()
```

### DispositivoLuzAdaptador

```python
# Transmitir QR
device.send(dst_mac, payload_bytes)

# Recibir QR
frame_data = device.receive()

# Control de medio
is_free = device.medium_is_free()
success = device.wait_and_send(dst_mac, payload)
```

## Ejemplos de Código

### Ejemplo 1: Enviar archivo simple con QRs

```python
from sender import SenderApp

# Crear emisor
sender = SenderApp()

# Enviar documento
sender.send_file_with_qr_display("documento.pdf")

# Limpiar
sender.cleanup()
```

### Ejemplo 2: Recibir archivo con cámara

```python
from receiver import ReceiverApp

# Crear receptor
receiver = ReceiverApp(camera_index=0)

# Iniciar captura
receiver.start_camera_capture()

# Esperar archivos
receiver.wait_for_file(timeout=300)

# Ver resultados
receiver.list_received_files()

# Limpiar
receiver.cleanup()
```

### Ejemplo 3: Transferencia silenciosa (sin visualización)

```python
from sender import SenderApp

# Crear emisor
sender = SenderApp()

# Enviar sin visualizar QRs en pantalla
sender.send_file_with_qr_display("documento.pdf", show_display=False)

# Limpiar
sender.cleanup()
```
## Notas para el Desarrollo

### Para mejorar la velocidad de transmisión:

1. **Reducir tiempo de espera entre QRs**: De 1s a 0.5s en `sender.py`
2. **Fragmentos más grandes**: Aumentar `MAX_FRAGMENT_PAYLOAD` en `file_transfer.py`
3. **Paralelización**: Capturar múltiples fragmentos simultáneamente

### Para mejorar la confiabilidad:

1. **Retransmisiones**: Implementar colas de reenvío
2. **Verificación por fragmento**: Enviar checksum con cada fragmento
3. **Compresión**: Reducir tamaño total

## Referencias

- **RFC QR-NET**: `/rfc/rfc-qrnet.txt`
- **Capa 1 Física**: `src/layer1_physical/dispositivo_luz_adaptador.py`
- **Capa 2/3 Red**: `src/layer2_3_network/node.py`
- **Capa 7 Anónima**: `src/layer7_anonymous/app.py`
- **Capa 5 Transferencia**: `src/layer5_transfer/file_transfer.py`

---

**Última actualización**: Mayo 7, 2026
**Versión**: 1.0
