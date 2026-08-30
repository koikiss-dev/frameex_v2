"""
Extraccion de fotogramas.

Jorge Posadas (Yako)
"""

import os
import pathlib
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2 as cv

CONVERT_MINUTE_VALUE = 60


def convert_msc(ms: int) -> str:
    horas, resto = divmod(ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos, milisegundos = divmod(resto, 1_000)

    if horas > 0:
        return f"{horas:02d}-{minutos:02d}-{segundos:02d}-{milisegundos:03d}"

    return f"{minutos:02d}-{segundos:02d}-{milisegundos:03d}"


def write_frames_to_images(destine: str, title: str, frame: cv.typing.MatLike):
    destine_path = pathlib.Path(destine)
    if not os.path.exists(f"{destine_path}"):
        os.makedirs(f"{destine_path}", exist_ok=True)

    cv.imwrite(str(destine_path.joinpath(title)), frame)


def extract_frames(
    source: str,
    destination: str,
    start_time: int,
    end_time: int,
    frame_interval_second: int,
    progress_callback=None,
):
    if end_time < start_time:
        raise ValueError("El tiempo final no puede ser menor que el tiempo inicial.")

    cap = cv.VideoCapture(source)

    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir el archivo de video.")

    FPS_COUNT = cap.get(cv.CAP_PROP_FPS)

    if FPS_COUNT <= 0:
        cap.release()
        raise RuntimeError("FPS inválido o no detectado en el video.")

    frame_start_minute = int(FPS_COUNT * (start_time * CONVERT_MINUTE_VALUE))
    frame_end_minute = int(FPS_COUNT * (end_time * CONVERT_MINUTE_VALUE))

    cap.set(cv.CAP_PROP_POS_FRAMES, frame_start_minute)

    frame_count = 0
    current_frame_time = frame_start_minute
    frame_step = max(1, int(FPS_COUNT * frame_interval_second))
    total_frames_to_process = max(1, frame_end_minute - frame_start_minute)

    print("/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/")
    print(cap.get(cv.CAP_PROP_FRAME_COUNT))
    print(source)
    print(destination)
    print(start_time)
    print(end_time)
    print(frame_interval_second)
    print(frame_step)
    print(total_frames_to_process)
    print("/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/\n")

    while cap.isOpened() and current_frame_time <= frame_end_minute:
        frame_exists, frame = cap.read()
        if not frame_exists:
            break

        timestamp = convert_msc(int(cap.get(cv.CAP_PROP_POS_MSEC)))

        if (current_frame_time - frame_start_minute) % frame_step == 0:
            write_frames_to_images(
                destination, f"imagen-{frame_count}-{timestamp}.png", frame
            )

        frame_count += 1
        current_frame_time += 1

        if progress_callback:
            progress = (
                (current_frame_time - frame_start_minute) / total_frames_to_process
            ) * 100
            progress_callback(min(100.0, progress))

    cap.release()


class VideoFrameExtractorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Extractor de Frames")
        self.root.geometry("900x600")
        self.root.resizable(False, False)

        self.source_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.start_var = tk.IntVar(value=0)
        self.end_var = tk.IntVar(value=1)
        self.interval_var = tk.IntVar(value="1")

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="15 15 15 15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Video origen
        ttk.Label(main_frame, text="Video de origen:").grid(
            row=0, column=0, sticky=tk.W, pady=4
        )
        ttk.Entry(main_frame, textvariable=self.source_var, width=38).grid(
            row=0, column=1, padx=5, pady=4
        )
        ttk.Button(main_frame, text="Examinar...", command=self._select_source).grid(
            row=0, column=2, pady=4
        )

        # Carpeta destino
        ttk.Label(main_frame, text="Carpeta destino:").grid(
            row=1, column=0, sticky=tk.W, pady=4
        )
        ttk.Entry(main_frame, textvariable=self.dest_var, width=38).grid(
            row=1, column=1, padx=5, pady=4
        )
        ttk.Button(main_frame, text="Examinar...", command=self._select_dest).grid(
            row=1, column=2, pady=4
        )

        # Separador
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=10
        )

        # Parámetros numéricos
        ttk.Label(main_frame, text="Minuto inicial:").grid(
            row=3, column=0, sticky=tk.W, pady=4
        )
        ttk.Entry(main_frame, textvariable=self.start_var, width=15).grid(
            row=3, column=1, sticky=tk.W, padx=5, pady=4
        )

        ttk.Label(main_frame, text="Minuto final:").grid(
            row=4, column=0, sticky=tk.W, pady=4
        )
        ttk.Entry(main_frame, textvariable=self.end_var, width=15).grid(
            row=4, column=1, sticky=tk.W, padx=5, pady=4
        )

        ttk.Label(main_frame, text="Intervalo (segundos):").grid(
            row=5, column=0, sticky=tk.W, pady=4
        )
        ttk.Entry(main_frame, textvariable=self.interval_var, width=15).grid(
            row=5, column=1, sticky=tk.W, padx=5, pady=4
        )

        # Barra de progreso y estado
        self.progress_bar = ttk.Progressbar(
            main_frame, orient=tk.HORIZONTAL, mode="determinate"
        )
        self.progress_bar.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(15, 5))

        self.status_label = ttk.Label(
            main_frame, text="Listo para procesar.", font=("TkDefaultFont", 9, "italic")
        )
        self.status_label.grid(row=7, column=0, columnspan=3, sticky=tk.W)

        # Botón de acción
        self.btn_process = ttk.Button(
            main_frame, text="Iniciar Extracción", command=self._start_thread
        )
        self.btn_process.grid(row=8, column=0, columnspan=3, pady=(15, 0))

    def _select_source(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[
                ("Archivos de video", "*.mp4 *.avi *.mkv *.mov *.flv"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if file_path:
            self.source_var.set(file_path)

    def _select_dest(self):
        folder_path = filedialog.askdirectory(title="Seleccionar Carpeta de Destino")
        if folder_path:
            self.dest_var.set(folder_path)

    def _start_thread(self):
        # Validaciones de entrada
        source = self.source_var.get().strip()
        dest = self.dest_var.get().strip()

        if not source or not os.path.isfile(source):
            messagebox.showerror("Error", "Selecciona un archivo de video válido.")
            return

        if not dest:
            messagebox.showerror("Error", "Especifica una carpeta de destino.")
            return

        try:
            start_time = float(self.start_var.get())
            end_time = float(self.end_var.get())
            interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror(
                "Error",
                "Los campos de tiempo e intervalo deben contener valores numéricos válidos.",
            )
            return

        if start_time < 0 or end_time < 0 or interval <= 0:
            messagebox.showerror(
                "Error", "Los valores de tiempo e intervalo deben ser positivos."
            )
            return

        if end_time < start_time:
            messagebox.showerror(
                "Error", "El minuto final no puede ser menor al inicial."
            )
            return

        self.btn_process.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.status_label.config(text="Procesando video...")

        # Ejecución en segundo plano
        thread = threading.Thread(
            target=self._run_extraction,
            args=(source, dest, start_time, end_time, interval),
            daemon=True,
        )
        thread.start()

    def _run_extraction(self, source, dest, start_time, end_time, interval):
        try:
            extract_frames(
                source=source,
                destination=dest,
                start_time=start_time,
                end_time=end_time,
                frame_interval_second=interval,
                progress_callback=self._update_progress,
            )
            self.root.after(0, self._on_success)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _update_progress(self, percent: float):
        self.root.after(0, lambda: self.progress_bar.configure(value=percent))

    def _on_success(self):
        self.btn_process.config(state=tk.NORMAL)
        self.status_label.config(text="Proceso finalizado con éxito.")
        messagebox.showinfo("Completado", "La extracción de fotogramas ha finalizado.")

    def _on_error(self, err_msg: str):
        self.btn_process.config(state=tk.NORMAL)
        self.status_label.config(text="Error durante el procesamiento.")
        messagebox.showerror("Error de Ejecución", err_msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoFrameExtractorApp(root)
    root.mainloop()
