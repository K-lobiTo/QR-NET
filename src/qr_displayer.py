import os
import re
import time
import tkinter as tk

from PIL import Image, ImageTk


QR_DIR = "temp-qr"
DISPLAY_MS = 500


def extract_chunk_number(filename):
    match = re.search(r"qr-(\d+)\.png", filename)
    return int(match.group(1)) if match else -1


class QRDisplayer:

    def __init__(self):

        self.root = tk.Tk()

        self.root.title("QR-NET")

        # Fullscreen
        self.root.attributes("-fullscreen", True)

        # ESC para salir
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.label = tk.Label(self.root, bg="black")
        self.label.pack(expand=True)

    def show_sequence(self, cant_fragments):

        files = [
            f for f in os.listdir(QR_DIR)
            if f.endswith(".png")
        ]

        files.sort(key=extract_chunk_number)
        files = files[:cant_fragments]
        index = 1
        for filename in files:

            path = os.path.join(QR_DIR, filename)

            img = Image.open(path)

            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()

            # Mantener proporción
            img.thumbnail((screen_w, screen_h))

            photo = ImageTk.PhotoImage(img)

            self.label.config(image=photo)
            self.label.image = photo

            self.root.update()

            print(f"  [{index}/{len(files)}] Mostrando QR en pantalla...")
            index = index + 1
            time.sleep(DISPLAY_MS / 50)

        self.root.destroy()


if __name__ == "__main__":

    viewer = QRDisplayer()

    viewer.show_sequence()