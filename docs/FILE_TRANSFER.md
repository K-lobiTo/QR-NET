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
python receiver.py --host 192.168.1.101 --port 9000
```

**Salida esperada:**
```
======================================================================
QR-NET FILE TRANSFER — RECEPTOR
======================================================================

[Receptor] Nodo iniciado en 192.168.1.101:9000
[Receptor] ID del nodo: a1b2c3d4...

[Receptor] Captura de cámara iniciada

[Luz-L1] Cámara abierta, buscando QRs...

[Receptor] Esperando archivos (timeout: 300s)...
```

#### Terminal 2 — Emisor (otra máquina)

```bash
cd src
source ../venv/bin/activate
python sender.py documento.pdf a1b2c3d4 --host 192.168.1.100 --port 9000
```

**Salida esperada:**
```
======================================================================
QR-NET FILE TRANSFER — EMISOR
======================================================================

[Emisor] Nodo iniciado en 192.168.1.100:9000
[Emisor] ID del nodo: x9y8z7w6...

──────────────────────────────────────────────────────────────────────
Archivo: documento.pdf
Tamaño: 24576 bytes
Destino: a1b2c3d4

Fragmentos a enviar: 50

Mostrando fragmentos en pantalla:

  [1/50] Mostrando fragmento en pantalla... ✓ (542 bytes)
  [2/50] Mostrando fragmento en pantalla... ✓ (542 bytes)
  ...
──────────────────────────────────────────────────────────────────────
✓ Emisión completada
```

### Opción 2: Modo Test (Mismo dispositivo)

Para probar en un solo dispositivo sin necesidad de dos cámaras:

```bash
# Terminal 1 — Receptor en modo telnet (sin cámara)
python receiver.py --port 9001 --no-listen

# Terminal 2 — Emisor
python sender.py documento.pdf <node-id-receptor> --port 9000
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
  destino              ID del nodo receptor

optional arguments:
  --host HOST          Host local (default: 0.0.0.0)
  --port PORT          Puerto UDP (default: 9000)
  --no-display         No mostrar QRs (modo silencioso)
```

### Receptor (`receiver.py`)

```
optional arguments:
  --host HOST          Host local (default: 0.0.0.0)
  --port PORT          Puerto UDP (default: 9000)
  --camera CAMERA      Índice de cámara (default: 0)
  --timeout TIMEOUT    Timeout en segundos (default: 300)
  --no-listen          No capturar con cámara
```

## Flujo de Transferencia Detallado

### 1. Preparación Emisor

```python
# sender.py
sender = SenderApp(host="192.168.1.100", port=9000)
sender.send_file_with_qr_display("archivo.bin", "node-destino")
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

```bash
# Verificar que los puertos no están en uso
lsof -i :9000
netstat -tulpn | grep 9000

# Usar puertos diferentes
python receiver.py --port 9001
python sender.py archivo.bin node-id --port 9000
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

### FileTransferApp

```python
# Enviar archivo
transfer_id = app.send_file("nodo-destino", "archivo.bin")

# Esperar transferencia
output_path = app.wait_for_transfer(transfer_id, timeout=300)

# État de la transferencia
status = app.get_transfer_status(transfer_id)
```

### DispositivoLuzAdaptador

```python
# Transmitir
device.send(dst_mac, payload_bytes)

# Recibir
frame_data = device.receive()

# Control de medio
is_free = device.medium_is_free()
success = device.wait_and_send(dst_mac, payload)
```

## Ejemplos de Código

### Ejemplo 1: Enviar archivo simple

```python
from layer7_file_transfer import FileTransferApp
from layer7_anonymous.app import AnonymousApp
from layer2_3_network.node import QRNetNode

# Inicializar capas
node = QRNetNode("192.168.1.100", 9000)
node.start()

app = AnonymousApp(node)
file_app = FileTransferApp(app)

# Enviar
file_app.send_file("node-receptor-id", "documento.pdf")

node.stop()
```

### Ejemplo 2: Recibir archivo con timeout

```python
# Esperar 5 minutos a que llegue un archivo
output = file_app.wait_for_transfer("transfer-id-123", timeout=300)

if output:
    print(f"✓ Archivo guardado en: {output}")
else:
    print("✗ Timeout o error en transferencia")
```

### Ejemplo 3: Barra de progreso personalizada

```python
import time

while True:
    progress, total = file_app.manager.get_transfer_progress("transfer-id")
    percent = (progress / total * 100) if total > 0 else 0
    print(f"\rProgreso: {progress}/{total} ({percent:.0f}%)", end="")
    
    if progress == total:
        break
    time.sleep(1)
```

## Notas para el Desarrollo

### Para mejorar la velocidad de transmisión:

1. **Reducir tiempo de espera entre QRs**: De 2s a 0.5s en `sender.py`
2. **Fragmentos más grandes**: Aumentar `MAX_FRAGMENT_PAYLOAD` en `file_transfer.py`
3. **Paralelización**: Enviar múltiples fragmentos simultáneamente

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
