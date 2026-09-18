"""
Extraccion de fotogramas.

Jorge Posadas (Yako)
"""

import cv2 as cv
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog as fl

CONVERT_MINUTE_VALUE = 60
INSUMOS = Path(os.getcwd(), "videos")
DESTINO = Path(os.getcwd(), "imagenes")


PRUEBA = Path(INSUMOS, "prueba.mp4")


def extract_frames(
    source: str, start_time: int, end_time: int, frame_interval_second: int
):
    if end_time < start_time:
        return

    cap = cv.VideoCapture(source)

    print(cap.get(cv.CAP_PROP_FRAME_COUNT))
    print(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    print(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

    fps = cap.get(cv.CAP_PROP_FPS)

    if fps <= 0:
        cap.release()
        return

    # frame inicial
    start_frame = int(fps * (start_time * CONVERT_MINUTE_VALUE))

    # frame final
    end_frame = int(fps * (end_time * CONVERT_MINUTE_VALUE))

    """ SE CAMBIA DONDE INICIA """
    cap.set(cv.CAP_PROP_POS_FRAMES, start_frame)

    frame_count = 0
    current_frame = start_frame

    # cada cuantos frames se genera una imagen
    frame_step = max(1, int(fps * frame_interval_second))

    print(frame_step)

    while cap.isOpened() and current_frame <= end_frame:
        frame_read_success, frame = cap.read()
        timestamp = format_timestamp(int(cap.get(cv.CAP_PROP_POS_MSEC)))

        if not frame_read_success:
            break

        if (current_frame - start_frame) % frame_step == 0:

            write_frames_to_images(
                DESTINO, f"imagen-{frame_count}-{timestamp}.png", frame
            )

        frame_count += 1
        current_frame += 1

    cap.release()


def format_timestamp(ms: int) -> str:
    horas, resto = divmod(ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos, milisegundos = divmod(resto, 1_000)

    if horas > 0:
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def write_frames_to_images(destine: str, title: str, frame: cv.typing.MatLike):
    destine_path = Path(destine)
    if not os.path.exists(f"{destine_path}"):
        os.makedirs(f"{destine_path}", exist_ok=True)

    cv.imwrite(f"{destine_path.joinpath(title)}", frame)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.geometry("800x700")
        self.root.title("Framex")

        self.root.columnconfigure(1, weight=1)

        self.createComponents()

    # e: derecha, w: izquierda, n: arriba, s: abajo
    def createComponents(self):
        # Seleccionar un video
        selectVideo = ttk.Label(self.root, text="Seleccione el video")
        self.videoValueVar = tk.StringVar()
        self.entryVideo = ttk.Entry(
            self.root, state="readonly", textvariable=self.videoValueVar
        )
        buttonSelectVideo = ttk.Button(
            self.root, text="Seleccionar video", command=self.getVideo
        )

        # posiocionar select video
        selectVideo.grid(row=0, column=0, sticky="w")
        self.entryVideo.grid(row=0, column=1, sticky="ew", padx=20)
        buttonSelectVideo.grid(row=0, column=3, sticky="ew")

        # Seleccionar la carpeta de destino
        selectDirectory = ttk.Label(self.root, text="Seleccione la carpeta de destino")
        self.directoryValueVar = tk.StringVar()
        self.entryDirectory = ttk.Entry(
            self.root, state="readonly", textvariable=self.directoryValueVar
        )
        buttonOpenDirectory = ttk.Button(
            self.root, text="Seleccionar carpeta de destino", command=self.getDirectory
        )

        selectDirectory.grid(row=1, column=0, sticky="w")
        self.entryDirectory.grid(row=1, column=1, sticky="ew", padx=20)
        buttonOpenDirectory.grid(row=1, column=3, sticky="ew")

        # horas
        self.minutesVar = tk.IntVar(value=0)
        self.k = tk.StringVar(value="00:00:00")
        self.minutesInput = ttk.Spinbox(
            self.root,
            from_=0,
            to=99999,
            wrap=True,
            width=3,
            textvariable=self.minutesVar,
            command=lambda: self.k.set(format_timestamp(self.minutesVar.get() * 60000)),
        )
        self.minutesInput.grid(row=2, column=1)

        self.m = ttk.Label(self.root, textvariable=self.k)
        self.m.grid(row=2, column=2)

    def getDirectory(self):
        dialog = fl.askdirectory()

        self.directoryValueVar.set(dialog)
        print(dialog)

    def getVideo(self):
        dialog = fl.askopenfilename()

        self.videoValueVar.set(dialog)
        print(dialog)


if __name__ == "__main__":
    t = tk.Tk()
    a = App(t)
    a.root.mainloop()
    """ extract_frames(PRUEBA, 13, 14, 1) """
