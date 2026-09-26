"""
Extracción de fotogramas desde grabaciones de Teams.
Aplicación interna.

Jorge Posadas
"""

import math
import os
import queue
import re
from datetime import datetime
from pathlib import Path
from threading import Event, Thread

from tkinter import filedialog as fl, messagebox

import cv2 as cv
import customtkinter as ctk




def formatTime(ms: int) -> str:
    horas, resto = divmod(ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos, milisegundos = divmod(resto, 1_000)

    if horas > 0:
        return f"{horas:02d}_{minutos:02d}_{segundos:02d}"

    return f"{horas:02d}_{minutos:02d}_{segundos:02d}"


CONVERT_MINUTE_VALUE = 60
HOME_PATH = Path.home()
VIDEO_MAX_MINUTES = 120
DEFAULT_INTERVAL_SECONDS = 10


def getMaxMinute(source: str) -> float:
    """Obtiene la duración exacta del video en minutos."""
    cap = None
    try:
        cap = cv.VideoCapture(source)
        if not cap.isOpened():
            raise Exception(f"No se pudo abrir el video: {source}")

        total_frames = cap.get(cv.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv.CAP_PROP_FPS)
        if fps <= 0:
            raise Exception("No se pudieron calcular los FPS del video.")

        return total_frames / (fps * CONVERT_MINUTE_VALUE)
    finally:
        if cap is not None:
            cap.release()


class App:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.geometry("920x820")
        self.root.minsize(840, 720)
        self.root.title("Framex | Extracción de fotogramas")

        self.ui_events: queue.Queue[tuple] = queue.Queue()
        self.stop_event = Event()
        self.is_processing = False
        self.video_duration_minutes = 0.0
        self.saved_images = 0

        self.video_value = ctk.StringVar()
        self.directory_value = ctk.StringVar()
        self.until_end_value = ctk.BooleanVar(value=False)
        self.interval_value = ctk.StringVar(value=str(DEFAULT_INTERVAL_SECONDS))
        self.status_value = ctk.StringVar(value="Seleccione una grabación para comenzar.")
        self.progress_value = ctk.StringVar(value="0 %")
        self.duration_value = ctk.StringVar(value="Duración: sin calcular")
        self.summary_value = ctk.StringVar(value="Complete los pasos para ver el resumen.")

        self.start_time_vars = self.create_time_variables()
        self.end_time_vars = self.create_time_variables()

        self.create_components()
        self.attach_traces()
        self.update_form_state()
        self.poll_ui_events()

    @staticmethod
    def create_time_variables() -> dict[str, ctk.StringVar]:
        return {
            "hours": ctk.StringVar(value="00"),
            "minutes": ctk.StringVar(value="00"),
            "seconds": ctk.StringVar(value="00"),
        }

    def attach_traces(self):
        for variable in (*self.start_time_vars.values(), *self.end_time_vars.values()):
            variable.trace_add("write", self.on_form_change)
        self.interval_value.trace_add("write", self.on_form_change)
        self.until_end_value.trace_add("write", self.on_until_end_change)

    def create_components(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.main_scroll = ctk.CTkScrollableFrame(
            self.root,
            fg_color="transparent",
            corner_radius=0,
        )
        self.main_scroll.grid(row=0, column=0, sticky="nsew")
        self.main_scroll.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Extracción de fotogramas",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(
            header,
            text="Seleccione una grabación, configure el rango y genere las imágenes.",
            text_color=("gray35", "gray70"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        ctk.CTkButton(
            header, text="Ayuda", width=90, command=self.show_help
        ).grid(row=0, column=1, rowspan=2, padx=(10, 0))

        selection = self.create_section(1, "1. Seleccione la grabación y la carpeta de destino")
        selection.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(selection, text="Grabación de Teams").grid(
            row=1, column=0, sticky="w", padx=16, pady=7
        )
        
        self.video_entry = ctk.CTkEntry(
            selection, textvariable=self.video_value, state="readonly"
        )
        
        self.video_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=7)
        
        self.video_button = ctk.CTkButton(
            selection, text="Seleccionar grabación", command=self.set_video_path
        )
        
        self.video_button.grid(row=1, column=2, padx=(0, 16), pady=7)

        ctk.CTkLabel(selection, textvariable=self.duration_value).grid(
            row=2, column=1, sticky="w", padx=10, pady=(0, 6)
        )

        ctk.CTkLabel(selection, text="Carpeta donde se guardarán").grid(
            row=3, column=0, sticky="w", padx=16, pady=7
        )
        
        self.directory_entry = ctk.CTkEntry(
            selection, textvariable=self.directory_value, state="readonly"
        )
        
        self.directory_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=7)
        self.directory_button = ctk.CTkButton(
            selection, text="Seleccionar carpeta", command=self.set_directory
        )
        
        self.directory_button.grid(row=3, column=2, padx=(0, 16), pady=7)
        
        ctk.CTkLabel(
            selection,
            text="Se creará una carpeta nueva para no sobrescribir resultados anteriores.",
            text_color=("gray35", "gray70"),
        ).grid(row=4, column=1, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        configuration = self.create_section(2, "2. Configure la extracción")
        configuration.grid_columnconfigure((0, 1), weight=1)

        self.start_time_frame = self.create_time_input(
            configuration, 1, 0, "Extraer desde"
        )
        self.end_time_frame = self.create_time_input(
            configuration, 1, 1, "Extraer hasta"
        )

        self.until_end_checkbox = ctk.CTkCheckBox(
            configuration,
            text="Extraer hasta el final del video",
            variable=self.until_end_value,
        )
        self.until_end_checkbox.grid(row=2, column=1, sticky="w", padx=16, pady=(0, 12))

        interval_frame = ctk.CTkFrame(configuration, fg_color="transparent")
        interval_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkLabel(interval_frame, text="Extraer una imagen cada").pack(side="left")
        self.interval_entry = ctk.CTkEntry(
            interval_frame, width=75, textvariable=self.interval_value, justify="center"
        )
        self.interval_entry.pack(side="left", padx=8)
        ctk.CTkLabel(interval_frame, text="segundos").pack(side="left")

        summary = self.create_section(3, "3. Revise e inicie")
        summary.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            summary,
            textvariable=self.summary_value,
            anchor="w",
            justify="left",
            wraplength=800,
        ).grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(2, 12))

        self.start_button = ctk.CTkButton(
            summary, text="Iniciar extracción", command=self.start_extraction_process
        )
        self.start_button.grid(row=2, column=0, sticky="e", padx=8, pady=(0, 14))
        self.cancel_button = ctk.CTkButton(
            summary,
            text="Detener extracción",
            fg_color="#B42318",
            hover_color="#8F1C13",
            command=self.cancel_extraction_process,
        )
        self.cancel_button.grid(row=2, column=1, padx=8, pady=(0, 14))
        self.new_button = ctk.CTkButton(
            summary, text="Nueva extracción", command=self.reset_all
        )
        self.new_button.grid(row=2, column=2, sticky="w", padx=8, pady=(0, 14))

        results = ctk.CTkFrame(self.main_scroll)
        results.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 20))
        results.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            results, textvariable=self.status_value, font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        self.progress = ctk.CTkProgressBar(results)
        self.progress.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=5)
        self.progress.set(0)
        ctk.CTkLabel(results, textvariable=self.progress_value, width=55).grid(
            row=1, column=1, padx=(0, 16)
        )

        self.details_button = ctk.CTkButton(
            results, text="Ver detalles técnicos", width=160, command=self.toggle_details
        )
        self.details_button.grid(row=2, column=0, sticky="w", padx=16, pady=8)

        self.log_text = ctk.CTkTextbox(results, height=150, state="disabled", wrap="word")
        self.details_visible = False

    def create_section(self, row: int, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_scroll)
        frame.grid(row=row, column=0, sticky="ew", padx=24, pady=7)
        ctk.CTkLabel(
            frame, text=title, font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(12, 6))
        return frame

    def create_time_input(self, parent, row: int, column: int, title: str):
        variables = self.start_time_vars if column == 0 else self.end_time_vars
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=column, sticky="ew", padx=16, pady=6)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 5)
        )

        labels = (("hours", "Hora"), ("minutes", "Minuto"), ("seconds", "Segundo"))
        for index, (key, label) in enumerate(labels):
            entry = ctk.CTkEntry(frame, width=70, justify="center", textvariable=variables[key])
            entry.grid(row=1, column=index * 2, sticky="w")
            ctk.CTkLabel(frame, text=label, text_color=("gray35", "gray70")).grid(
                row=2, column=index * 2, sticky="w"
            )
            if index < 2:
                ctk.CTkLabel(frame, text=":").grid(row=1, column=index * 2 + 1, padx=5)

        frame.entries = [child for child in frame.winfo_children() if isinstance(child, ctk.CTkEntry)] # type: ignore
        return frame

    def on_form_change(self, *_):
        self.update_summary()
        self.update_form_state()

    def on_until_end_change(self, *_):
        enabled = not self.until_end_value.get() and not self.is_processing
        self.set_time_frame_enabled(self.end_time_frame, enabled)
        if self.until_end_value.get() and self.video_duration_minutes > 0:
            self.set_time_variables_from_minutes(self.end_time_vars, self.video_duration_minutes)
        self.update_summary()
        self.update_form_state()

    @staticmethod
    def set_time_frame_enabled(frame, enabled: bool):
        state = "normal" if enabled else "disabled"
        for entry in frame.entries:
            entry.configure(state=state)

    @staticmethod
    def time_to_minutes(variables: dict[str, ctk.StringVar]) -> float:
        hours = int(variables["hours"].get() or 0)
        minutes = int(variables["minutes"].get() or 0)
        seconds = int(variables["seconds"].get() or 0)
        if hours < 0 or minutes not in range(60) or seconds not in range(60):
            raise ValueError("Use horas positivas y valores entre 0 y 59 para minutos y segundos.")
        return hours * 60 + minutes + seconds / 60

    @staticmethod
    def set_time_variables_from_minutes(variables, total_minutes: float):
        total_seconds = max(0, round(total_minutes * 60))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        variables["hours"].set(f"{hours:02d}")
        variables["minutes"].set(f"{minutes:02d}")
        variables["seconds"].set(f"{seconds:02d}")

    @staticmethod
    def display_time(total_minutes: float) -> str:
        total_seconds = max(0, round(total_minutes * 60))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def validate_form(self) -> tuple[bool, str]:
        if not self.video_value.get().strip():
            return False, "Seleccione una grabación."
        if not self.directory_value.get().strip():
            return False, "Seleccione la carpeta donde se guardarán las imágenes."
        try:
            start = self.time_to_minutes(self.start_time_vars)
            end = self.time_to_minutes(self.end_time_vars)
            interval = int(self.interval_value.get())
        except ValueError:
            return False, "Revise el formato de tiempo y el intervalo."
        if interval <= 0:
            return False, "El intervalo debe ser mayor que cero."
        if end <= start:
            return False, "El tiempo final debe ser mayor que el tiempo inicial."
        if end > self.video_duration_minutes + (1 / 60):
            return False, "El tiempo final supera la duración del video."
        return True, ""

    def update_summary(self):
        try:
            start = self.time_to_minutes(self.start_time_vars)
            end = self.time_to_minutes(self.end_time_vars)
            interval = int(self.interval_value.get())
            self.summary_value.set(
                f"Se extraerá una imagen cada {interval} segundos, desde "
                f"{self.display_time(start)} hasta {self.display_time(end)}."
            )
        except (ValueError, TypeError):
            self.summary_value.set("Ingrese valores válidos para generar el resumen.")

    def update_form_state(self):
        has_video = bool(self.video_value.get().strip())
        has_directory = bool(self.directory_value.get().strip())
        ready, reason = self.validate_form()

        self.directory_button.configure(state="normal" if has_video and not self.is_processing else "disabled")
        configuration_enabled = has_video and has_directory and not self.is_processing
        self.set_time_frame_enabled(self.start_time_frame, configuration_enabled)
        self.set_time_frame_enabled(
            self.end_time_frame, configuration_enabled and not self.until_end_value.get()
        )
        self.interval_entry.configure(state="normal" if configuration_enabled else "disabled")
        self.until_end_checkbox.configure(state="normal" if configuration_enabled else "disabled")
        self.video_button.configure(state="disabled" if self.is_processing else "normal")
        self.start_button.configure(state="normal" if ready and not self.is_processing else "disabled")
        self.cancel_button.configure(state="normal" if self.is_processing else "disabled")
        self.new_button.configure(state="disabled" if self.is_processing else "normal")

        if not self.is_processing and not ready and has_video and has_directory:
            self.status_value.set(reason)

    def set_video_path(self):
        selected = fl.askopenfilename(
            initialdir=HOME_PATH, filetypes=[("Archivos de video MP4", "*.mp4")]
        )
        if not selected:
            return
        try:
            duration = getMaxMinute(selected)
            if duration > VIDEO_MAX_MINUTES:
                raise Exception("La grabación no debe superar las 2 horas.")
            self.video_duration_minutes = duration
            self.video_value.set(selected)
            self.duration_value.set(f"Duración detectada: {self.display_time(duration)}")
            self.directory_value.set("")
            self.reset_configuration()
            self.set_time_variables_from_minutes(self.end_time_vars, duration)
            self.status_value.set("Grabación válida. Ahora seleccione la carpeta de destino.")
        except Exception as error:
            self.video_value.set("")
            self.video_duration_minutes = 0
            self.duration_value.set("Duración: no disponible")
            messagebox.showerror("No se pudo abrir la grabación", str(error))
        self.update_form_state()

    def set_directory(self):
        selected = fl.askdirectory(initialdir=HOME_PATH)
        if not selected:
            return
        video_name = Path(self.video_value.get()).stem
        safe_name = re.sub(r"[^a-zA-Z0-9 _-]", "_", video_name)
        timestamp = f"{datetime.now():%Y_%m_%d_%H%M%S}"
        self.directory_value.set(str(Path(selected, f"{safe_name[:100]}_{timestamp}")))
        self.status_value.set("Configuración disponible. Revise el rango de extracción.")
        self.update_form_state()

    def reset_configuration(self):
        self.set_time_variables_from_minutes(self.start_time_vars, 0)
        self.set_time_variables_from_minutes(self.end_time_vars, 0)
        self.interval_value.set(str(DEFAULT_INTERVAL_SECONDS))
        self.until_end_value.set(False)
        self.progress.set(0)
        self.progress_value.set("0 %")
        self.saved_images = 0

    def reset_all(self):
        if self.is_processing:
            return
        self.video_value.set("")
        self.directory_value.set("")
        self.video_duration_minutes = 0
        self.duration_value.set("Duración: sin calcular")
        self.reset_configuration()
        self.clear_logs()
        self.status_value.set("Seleccione una grabación para comenzar.")
        self.summary_value.set("Complete los pasos para ver el resumen.")
        self.update_form_state()

    def set_running_state(self, running: bool):
        self.is_processing = running
        self.update_form_state()

    def start_extraction_process(self):
        valid, reason = self.validate_form()
        if not valid:
            messagebox.showwarning("Revise la configuración", reason)
            return

        start_time = self.time_to_minutes(self.start_time_vars)
        end_time = self.time_to_minutes(self.end_time_vars)
        interval = int(self.interval_value.get())

        self.stop_event.clear()
        self.saved_images = 0
        self.progress.set(0)
        self.progress_value.set("0 %")
        self.status_value.set("Preparando la grabación...")
        self.set_running_state(True)

        worker = Thread(
            target=self.extract_frames,
            args=(
                self.video_value.get(),
                start_time,
                end_time,
                interval,
                self.directory_value.get(),
            ),
            daemon=True,
        )
        worker.start()

    def cancel_extraction_process(self):
        self.stop_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_value.set("Cancelando el proceso...")

    def emit(self, event_type: str, *payload):
        self.ui_events.put((event_type, *payload))

    def log(self, message: str):
        self.emit("log", str(message))

    def poll_ui_events(self):
        try:
            while True:
                event_type, *payload = self.ui_events.get_nowait()
                if event_type == "log":
                    self.append_log(payload[0])
                elif event_type == "progress":
                    value, total_images = payload
                    self.progress.set(value)
                    self.progress_value.set(f"{round(value * 100)} %")
                    self.status_value.set(f"Extrayendo imágenes... {total_images} guardadas")
                elif event_type == "finished":
                    self.on_process_finished(payload[0], payload[1])
        except queue.Empty:
            pass
        self.root.after(100, self.poll_ui_events)

    def append_log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_logs(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def toggle_details(self):
        if self.details_visible:
            self.log_text.grid_forget()
            self.details_button.configure(text="Ver detalles técnicos")
        else:
            self.log_text.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=16, pady=(0, 12))
            self.details_button.configure(text="Ocultar detalles técnicos")
        self.details_visible = not self.details_visible

    def write_frames_to_images(self, destine: str, title: str, frame: cv.typing.MatLike):
        
        destine_path = Path(destine)
        if not os.path.exists(f"{destine_path}"):
            os.makedirs(f"{destine_path}")
        cv.imwrite(str(Path(destine_path, title)), frame)

    def extract_frames(
        self,
        source: str,
        start_time: float,
        end_time: float,
        frame_interval_second: int,
        destine: str,
    ):
        
        status = "error"
        status_message = "Error desconocido."
        cap_video = None

        try:
            if start_time < 0 or end_time < 0:
                raise Exception("Los tiempos de inicio no pueden ser negativos")
            if math.isinf(start_time) or math.isinf(end_time):
                raise Exception("No se permiten valores infinitos")
            if end_time < start_time:
                raise Exception("El tiempo final no puede ser menor al inicial.")

            self.log(f"Abriendo archivo: {source}")
            cap_video = cv.VideoCapture(source)
            if not cap_video.isOpened():
                raise Exception(f"No se pudo abrir el video: {source}")

            total_frames = cap_video.get(cv.CAP_PROP_FRAME_COUNT)
            width = cap_video.get(cv.CAP_PROP_FRAME_WIDTH)
            height = cap_video.get(cv.CAP_PROP_FRAME_HEIGHT)
            fps = cap_video.get(cv.CAP_PROP_FPS)

            if fps <= 0:
                status_message = "No se pudieron calcular los FPS del video."
                self.log(status_message)
                return
            if total_frames / (fps * 60) > VIDEO_MAX_MINUTES:
                raise Exception("La grabación no debe superar las 2 horas.")

            start_frame = int(fps * (start_time * CONVERT_MINUTE_VALUE))
            end_frame = int(fps * (end_time * CONVERT_MINUTE_VALUE))
            cap_video.set(cv.CAP_PROP_POS_FRAMES, start_frame)
            self.log(
                f"Resolución: {int(width)}x{int(height)} | "
                f"FPS: {fps:.2f} | Total frames: {int(total_frames)}"
            )

            frame_count = 0
            total_images = 0
            current_frame = start_frame
            frame_step = max(1, int(fps * frame_interval_second))
            extraction_length = max(1, end_frame - start_frame)

            while cap_video.isOpened() and current_frame <= end_frame:
                if self.stop_event.is_set():
                    status = "cancelled"
                    status_message = "El proceso fue cancelado por el usuario."
                    self.log(status_message)
                    break

                frame_read_success, frame = cap_video.read()
                timestamp: str = formatTime(
                    int(cap_video.get(cv.CAP_PROP_POS_MSEC))
                )
                if not frame_read_success:
                    break

                if (current_frame - start_frame) % frame_step == 0:
                    filename = f"{timestamp}.png"
                    self.write_frames_to_images(destine, filename, frame)
                    self.log(f"Guardado: {filename}")
                    total_images += 1
                    progress = min(1, (current_frame - start_frame) / extraction_length)
                    self.emit("progress", progress, total_images)

                frame_count += 1
                current_frame += 1

            if status != "cancelled":
                status = "success"
                status_message = (
                    f"Proceso finalizado con éxito. Se procesaron {total_images} imágenes."
                )
                self.log(status_message)
                self.emit("progress", 1.0, total_images)
        except Exception as error:
            status = "error"
            status_message = f"Ocurrió un error inesperado: {error}"
            self.log(status_message)
        finally:
            if cap_video is not None:
                cap_video.release()
            self.emit("finished", status, status_message)

    def on_process_finished(self, status: str, message: str):
        self.set_running_state(False)
        if status == "success":
            self.progress.set(1)
            self.progress_value.set("100 %")
            self.status_value.set(message)
            messagebox.showinfo("Proceso finalizado", message)
        elif status == "cancelled":
            self.status_value.set(message)
            messagebox.showwarning("Proceso cancelado", message)
        else:
            self.status_value.set("No se pudo completar la extracción.")
            messagebox.showerror("Error en el proceso", message)

    def show_help(self):
        window = ctk.CTkToplevel(self.root)
        window.title("Ayuda de Framex")
        window.geometry("690x500")
        window.transient(self.root)
        window.grab_set()

        text = ctk.CTkTextbox(window, wrap="word", font=("Segoe UI", 12))
        text.pack(fill="both", expand=True, padx=16, pady=16)
        text.insert(
            "1.0",
            """CÓMO USAR FRAMEX

1. Seleccione una grabación de Teams en formato MP4.
2. Seleccione la carpeta principal donde desea guardar el resultado.
3. Indique la hora, minuto y segundo de inicio y final.
4. También puede activar “Extraer hasta el final del video”.
5. Indique cada cuántos segundos desea guardar una imagen.
6. Revise el resumen y presione “Iniciar extracción”.

EJEMPLO DE TIEMPO
Para comenzar en 1 minuto con 30 segundos, escriba:
Hora: 00 | Minuto: 01 | Segundo: 30

La aplicación crea una carpeta nueva automáticamente para evitar que se sobrescriban resultados anteriores. Si detiene el proceso, se conservarán las imágenes generadas hasta ese momento.
""",
        )
        text.configure(state="disabled")
        ctk.CTkButton(window, text="Cerrar", command=window.destroy).pack(pady=(0, 16))


if __name__ == "__main__":
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = App(root)
    root.mainloop()
