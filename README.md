# QR-NET

> Proyecto 1 — Redes de Computadoras  
> Tecnológico de Costa Rica | Prof. Kevin Moraga | Abril 2026

Re-implementación de capas del modelo OSI usando luz (códigos QR) como medio físico, sobre una red mesh anónima llamada **remote-QR-net**.

---

## Estructura del Proyecto

```
qr-net/
├── src/
│   ├── layer1_physical/        # Capa 1: Dispositivo de Transmisión (QR)
│   ├── layer2_3_network/       # Capas 2 y 3: remote-QR-net (mesh anónima)
│   ├── layer7_anonymous/       # Capa 7: Microblogging / Chat anónimo
│   ├── layer7_clearnet/        # Capa 7: IRC bot + NNTP (clearnet)
│   └── common/                 # Utilidades compartidas
├── rfc/                        # RFC del protocolo remote-QR-net (ASCII)
├── docs/                       # Documentación (Markdown + LaTeX → PDF)
├── tests/                      # Pruebas unitarias e integración
├── scripts/                    # Scripts de setup y ejecución
└── README.md
```

## Capas Implementadas

| Capa OSI | Módulo | Descripción |
|----------|--------|-------------|
| Capa 1 | `layer1_physical` | Transmisión via códigos QR (luz) con trama de 128 bytes |
| Capa 2/3 | `layer2_3_network` | Red mesh anónima sobre TCP/IP (remote-QR-net) |
| Capa 5 | `layer5_transfer` | Fragmentación y reensamblaje de archivos |
| Capa 7 | `layer7_anonymous` | Microblogging / chat dentro de remote-QR-net |
| Capa 7 | `layer7_clearnet` | Servidor IRC + bot + NNTP (clearnet) |
| Capa 7 | `layer7_file_transfer` | Transferencia de archivos fragmentados |

## Requisitos

```bash
pip install -r requirements.txt
```

## Ejecución Rápida

```bash
# Nodo completo
python src/main.py

# Solo Dispositivo de Transmisión
python src/layer1_physical/main.py

# Solo nodo de red
python src/layer2_3_network/main.py
```

## ⚡ Transferencia de Archivos Entre Dispositivos

Nuevo: **Transferencia de archivos fragmentados vía QR con captura por cámara**

### Uso Rápido

```bash
# En máquina receptora (con cámara):
./quickstart.sh receive --host 192.168.1.101

# En máquina emisora:
./quickstart.sh send archivo.pdf abc123def456 192.168.1.100
```

### Características

✓ Fragmentación automática (máx 500 bytes/fragmento)  
✓ Transmisión de fragmentos como QRs  
✓ Captura con cámara y decodificación  
✓ Reensamblaje automático  
✓ Verificación SHA256  
✓ Transferencias múltiples simultáneas  

### Documentación Completa

Ver [docs/FILE_TRANSFER.md](docs/FILE_TRANSFER.md) para guía detallada.

## Evaluación

| Componente | Peso |
|-----------|------|
| Capa 1 — Dispositivo de Transmisión | 20% |
| Capas 2 y 3 — remote-QR-net | 30% |
| Capa 7 — Aplicación anónima | 10% |
| Capa 7 — Clearnet | 10% |
| RFC | 10% |
| Documentación | 20% |
| Extra (datacasting) | 10% |

## Integrantes

- Caleb Alfaro
- Joshua Jiménez
- Sebastián Quesada
