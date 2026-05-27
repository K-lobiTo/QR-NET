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
# O ver todas las IPs
ip addr show

# En Windows
ipconfig
```

### Paso 2.2: Crear archivo de ejemplo (opcional)

```bash
# Crear archivo de prueba de 1MB
dd if=/dev/urandom of=test_file.bin bs=1M count=1

# O usar un archivo existente
#   test_file.bin (archivo que quieres enviar)
```

---

## PARTE 3: EJECUCIÓN (DOS DISPOSITIVOS)

### DISPOSITIVO A — RECEPTOR (con cámara)

#### Paso 3A.1: Abrir terminal en carpeta del proyecto

```bash
cd /home/klob/Documents/redes/projects/1/QR-NET
source venv/bin/activate
```



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
./quickstart.sh receive --camera 0

# Emisor
./quickstart.sh send test_file.bin
```

### Opción B: Usar ejemplo interactivo (menú)

```bash
python example_file_transfer.py
```

Luego responde el menú interactivo:
- Opción 1: Emisor (enviar archivo)
- Opción 2: Receptor (recibir archivo con cámara)
- Opción 3: Salir

---

## ⚠️ TROUBLESHOOTING

### Problema: "Camera not found"

```bash
# Verificar cámaras disponibles
v4l2-ctl --list-devices

# Usar otra cámara (índice 1, 2, etc)
python src/receiver.py --camera 1
```

### Problema: Transferencia lenta o sin reconocimiento

La transferencia usa QR broadcast — no requiere conexión de red. Si hay problemas:

```bash
# Verificar que la cámara ve los QRs
# - Mejorar iluminación de pantalla emisor
# - Aumentar proximidad entre dispositivos
# - Usar cámara de mejor calidad

# Reintentar
python src/receiver.py --camera 0
python src/sender.py archivo.pdf
```

### Problema: "Hash mismatch"

```bash
# Archivo corrupto en tránsito
# Causas: pérdida de fragmentos, mala iluminación, captura incorrecta
# Solución: reintentar la transferencia
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
# ========== MÁQUINA 1 (Receptora) ==========
$ cd /home/klob/Documents/redes/projects/1/QR-NET
$ source venv/bin/activate

(venv) $ python src/receiver.py --camera 0

# [Receptor] Captura de cámara iniciada
# [Receptor] Esperando archivos...
# (Deja esto abierto)

# ========== MÁQUINA 2 (Emisora) ==========
$ cd /home/klob/Documents/redes/projects/1/QR-NET
$ source venv/bin/activate

(venv) $ python src/sender.py documento.pdf

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
