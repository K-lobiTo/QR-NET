"""
Capa 5 — Transferencia de Archivos
===================================
Maneja fragmentación, reensamblaje y control de transferencias de archivo.
Envía fragmentos a través de la capa 7 (aplicación anónima).
"""

from .file_transfer import FileTransferManager, FileFragment, TransferState

__all__ = ["FileTransferManager", "FileFragment", "TransferState"]
