# Guía Paso a Paso: Transferencia de Archivos con QR-NET

## 🎯 Objetivo
Enviar un archivo de una máquina a otra usando códigos QR como medio de transmisión.

## ✋ Requisitos Previos

### Hardware
- 2 computadoras conectadas a la misma red (o simuladas en localhost)
- 1 cámara web (en la máquina receptora)
- Monitor/pantalla (en la máquina emisora)

### Software
- Python 3.9+
- OpenCV, qrcode, pyzbar
- Dependencias (ya instaladas en venv)

## 📍 Ubicación del Proyecto

```bash
/home/klob/Documents/redes/projects/1/QR-NET/
```

---

## PARTE 1: VERIFICACIÓN DE DEPENDENCIAS

### Paso 1.1: Entrar al directorio

```bash
cd /home/klob/Documents/redes/projects/1/QR-NET
```

### Paso 1.2: Activar entorno virtual

```bash
source venv/bin/activate
```

**Debes ver:**
```
(venv) user@machine:~/QR-NET$
```

### Paso 1.3: Verificar dependencias

```bash
./quickstart.sh check
```

**Salida esperada:**
```
✓ Python 3 encontrado
✓ OpenCV instalado
✓ qrcode instalado
✓ Todas las dependencias instaladas correctamente
```

Si algo falla, instala lo faltante:
```bash
pip install opencv-python qrcode pyzbar pillow
```

---

## PARTE 2: SETUP (UNA SOLA VEZ)

### Paso 2.1: Encontrar dirección IP de la máquina receptora

```bash
# En Linux/Mac
hostname -I
# O
ifconfig | grep "inet " | grep -v 127.0.0.1

# En Windows
ipconfig
```

**Anota esta IP, ej: `192.168.1.101`**

### Paso 2.2: Crear archivo de ejemplo (opcional)

```bash
# Crear archivo de prueba de 1MB
dd if=/dev/urandom of=test_file.bin bs=1M count=1

# O usar un archivo existente
#   test_file.bin (archivo que quieres enviar)
```

---

## PARTE 3: EJECUCIÓN (DOS MÁQUINAS)

### MÁQUINA A — RECEPTOR (con cámara)

#### Paso 3A.1: Abrir terminal en carpeta del proyecto

```bash
cd /home/klob/Documents/redes/projects/1/QR-NET
source venv/bin/activate
```

#### Paso 3A.2: Iniciar como receptor

```bash
python src/receiver.py --host 192.168.1.101 --port 9000
```

**Salida esperada:**
```
======================================================================
QR-NET FILE TRANSFER — RECEPTOR
======================================================================

[Receptor] Nodo iniciado en 192.168.1.101:9000
[Receptor] ID del nodo: a7c3f2d8e1b4a9c6...

[Receptor] Captura de cámara iniciada

[Luz-L1] Cámara abierta, buscando QRs...

[Receptor] Esperando archivos (timeout: 300s)...
```

✅ **DEJA ESTE TERMINAL ABIERTO** — El receptor está listening

⚠️ **Anota el ID del nodo** (primeros 8+ caracteres)

---

### MÁQUINA B — EMISOR

#### Paso 3B.1: Abrir terminal EN OTRA MÁQUINA (o nueva terminal)

```bash
cd /home/klob/Documents/redes/projects/1/QR-NET
source venv/bin/activate
```

#### Paso 3B.2: Iniciar como emisor

```bash
python src/sender.py test_file.bin a7c3f2d8 192.168.1.100
```

**Reemplazar:**
- `test_file.bin` → tu archivo a enviar
- `a7c3f2d8` → ID del nodo receptor (primeros 8 caracteres del paso 3A.2)
- `192.168.1.100` → IP de ESTA máquina

**Salida esperada:**
```
======================================================================
QR-NET FILE TRANSFER — EMISOR
======================================================================

[Emisor] Nodo iniciado en 192.168.1.100:9000
[Emisor] ID del nodo: x1y2z3w4...

──────────────────────────────────────────────────────────────────────
Archivo: test_file.bin
Tamaño: 1048576 bytes
Destino: a7c3f2d8
──────────────────────────────────────────────────────────────────────

Fragmentos a enviar: 5

Mostrando fragmentos en pantalla:

  [1/5] Mostrando fragmento... ✓
  [2/5] Mostrando fragmento... ✓
  [3/5] Mostrando fragmento... ✓
  [4/5] Mostrando fragmento... ✓
  [5/5] Mostrando fragmento... ✓

──────────────────────────────────────────────────────────────────────
✓ Emisión completada
```

---

### MÁQUINA A — VIENDO RECEPCIÓN

Mientras el emisor está enviando, **en el receptor** deberías ver:

```
[Receptor] Recibiendo archivo: test_file.bin
  Transfer ID: a7c3f2d8-1234-5678...
  Tamaño: 1048576 bytes
  Fragmentos: 5
  Hash: a1b2c3d4e5f6...

  [1/5] Fragmento recibido
  [2/5] Fragmento recibido
  [3/5] Fragmento recibido
  [4/5] Fragmento recibido
  [5/5] Fragmento recibido

✓ Archivo guardado: received_test_file.bin
```

✅ **¡TRANSFERENCIA COMPLETADA!**

---

## PARTE 4: VERIFICACIÓN

### Paso 4.1: Verificar archivo recibido

```bash
# En máquina A (receptor)
ls -lh received_test_file.bin

# Comparar con original (si fue enviado desde A)
sha256sum test_file.bin
sha256sum received_test_file.bin
# Deben ser idénticas
```

### Paso 4.2: Verificar contenido

```bash
# Mostrar primeros 100 caracteres
head -c 100 received_test_file.bin | strings

# Comparar bytes
cmp test_file.bin received_test_file.bin && echo "✓ Archivos idénticos"
```

---

## PARTE 5: ALTERNATIVAS Y VARIACIONES

### Opción A: Usar script bash (más simple)

```bash
# Receptor
./quickstart.sh receive --host 192.168.1.101

# Emisor
./quickstart.sh send test_file.bin a7c3f2d8 192.168.1.100
```

### Opción B: Usar ejemplo interactivo (menú)

```bash
python example_file_transfer.py
```

Luego responde las preguntas interactivas.

### Opción C: Usar Python directo (código)

```python
from src.layer7_file_transfer import FileTransferApp
from src.layer2_3_network.node import QRNetNode
from src.layer7_anonymous.app import AnonymousApp

# Inicializar
node = QRNetNode("192.168.1.100", 9000)
node.start()
app = AnonymousApp(node)
file_app = FileTransferApp(app)

# Enviar archivo
file_app.send_file("a7c3f2d8", "test_file.bin")
```

---

## ⚠️ TROUBLESHOOTING

### Problema: "Camera not found"

```bash
# Verificar cámaras disponibles
v4l2-ctl --list-devices

# Usar otra cámara (índice 1, 2, etc)
python src/receiver.py --camera 1
```

### Problema: "Connection refused"

```bash
# Puerto está en uso
lsof -i :9000

# Usar otro puerto
python src/receiver.py --port 9001
python src/sender.py archivo.pdf id --port 9000
```

### Problema: "Hash mismatch"

```bash
# Archivo corrupto en tránsito
# Reintentar la transferencia
# Verificar red e iluminación
```

### Problema: "ModuleNotFoundError"

```bash
# Estar en directorio correcto
cd /home/klob/Documents/redes/projects/1/QR-NET

# Entorno virtual activado
source venv/bin/activate
```

---

## 📊 EJEMPLO COMPLETO

### Escenario: Transferir documento.pdf entre dos PCs

```bash
# ========== MÁQUINA 1 (Receptora, IP: 192.168.1.101) ==========
$ cd /home/klob/Documents/redes/projects/1/QR-NET
$ source venv/bin/activate

(venv) $ python src/receiver.py --host 192.168.1.101 --port 9000

# [Receptor] ID del nodo: a7c3f2d8e1b4a9c6...
# [Receptor] Esperando archivos...
# (Deja esto abierto)

# ========== MÁQUINA 2 (Emisora, IP: 192.168.1.100) ==========
$ cd /home/klob/Documents/redes/projects/1/QR-NET
$ source venv/bin/activate

(venv) $ python src/sender.py documento.pdf a7c3f2d8 192.168.1.100

# [Emisor] Mostrando fragmentos...
# [1/15] ✓
# [2/15] ✓
# ...
# ✓ Emisión completada

# ========== MÁQUINA 1 (Receptor - Auto) ==========
# [Receptor] [1/15] Fragmento recibido
# [Receptor] [2/15] Fragmento recibido
# ...
# ✓ Archivo guardado: received_documento.pdf

# El usuario puede ahora ver received_documento.pdf en el receptor
```

---

## 🎓 CONCEPTOS CLAVE

### Fragmentación
- Archivo se divide en ~500 bytes
- Cada fragmento → QR
- Receptor decodifica cada QR
- Algoritmo ordena automáticamente

### Transmisión
- QR se muestra en pantalla (~2 seg)
- Luz visible (pantalla)
- Cámara captura luz reflejada
- OpenCV decodifica QR

### Verificación
- SHA256 del archivo completo
- Se verifica origen vs destino
- Si falla: error de transferencia

---

## 📚 MÁS INFORMACIÓN

Ver documentos completos:
- `docs/FILE_TRANSFER.md` — Guía detallada
- `IMPLEMENTATION_SUMMARY.md` — Resumen técnico
- `STRUCTURE.md` — Arquitectura

---

## 🚀 TIPS Y TRUCOS

### Para acelerar:
1. Reduce tiempo entre QRs → edita `sender.py` línea ~100
2. Aumenta fragmentos → edita `MAX_FRAGMENT_PAYLOAD` en `file_transfer.py`
3. Cámara en buena luz y distancia ~20cm

### Para depurar:
```bash
# Ver logs detallados
python src/receiver.py 2>&1 | tee logs.txt

# Test offline (sin cámara)
python src/receiver.py --no-listen
```

### Para producción:
1. Encripta con Fernet (opcional)
2. Comprime con gzip antes de enviar
3. Implementa ACK explícito
4. Monitorea velocidad

---

¡Disfruta tu transferencia de archivos con QR-NET! 🎉

Fecha: 7 de Mayo 2026 | Versión: 1.0
