"""
Extraccion de fotogramas.

Jorge Posadas (Yako)
"""

import cv2 as cv
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog as fl, messagebox, IntVar
from threading import Thread, Event
from tkinter.constants import DISABLED, NORMAL
import queue

CONVERT_MINUTE_VALUE = 60
HOME_PATH = Path.home()


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
        self.root.geometry("800x750")
        self.root.title("Framex")

        self.logs = queue.Queue()
        self.stop_event = Event()

        self.createComponents()
        self.pollLogs()

    def log(self, message: str):
        self.logs.put(str(message))

    def pollLogs(self):
        try:
            while True:
                msg = self.logs.get_nowait()
                self.logText.configure(state="normal")
                self.logText.insert("end", msg + "\n")
                self.logText.see("end")
                self.logText.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.pollLogs)

    def getMaxMinute(self, source: str):
        cap = cv.VideoCapture(source)
        total_frames = cap.get(cv.CAP_PROP_FRAME_COUNT)

        fps = cap.get(cv.CAP_PROP_FPS)

        cap.release()
        print((total_frames / (fps * 60)))

        return total_frames / (fps * 60)

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

        try:
            if end_time < start_time:
                status_message = "El tiempo final no puede ser menor al inicial."
                self.log(status_message)
                return

            self.log(f"Abriendo archivo: {source}")
            cap = cv.VideoCapture(source)

            total_frames = cap.get(cv.CAP_PROP_FRAME_COUNT)
            width = cap.get(cv.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv.CAP_PROP_FPS)

            self.log(
                f"Resolucion: {int(width)}x{int(height)} | FPS: {fps:.2f} | Total frames: {int(total_frames)}"
            )

            if fps <= 0:
                cap.release()
                status_message = "No se pudieron calcular los FPS del video."
                self.log(status_message)
                return

            start_frame = int(fps * (start_time * CONVERT_MINUTE_VALUE))
            end_frame = int(fps * (end_time * CONVERT_MINUTE_VALUE))

            cap.set(cv.CAP_PROP_POS_FRAMES, start_frame)

            frame_count = 0
            current_frame = start_frame
            frame_step = max(1, int(fps * frame_interval_second))

            while cap.isOpened() and current_frame <= end_frame:
                if self.stop_event.is_set():
                    status = "cancelled"
                    status_message = "El proceso fue cancelado por el usuario."
                    self.log(status_message)
                    break

                frame_read_success, frame = cap.read()
                timestamp = format_timestamp(int(cap.get(cv.CAP_PROP_POS_MSEC)))

                if not frame_read_success:

                    break

                if (current_frame - start_frame) % frame_step == 0:
                    filename = f"imagen-{frame_count}-{timestamp.replace(':', '_')}.png"
                    write_frames_to_images(destine, filename, frame)
                    self.log(f"Guardado: {filename}")

                frame_count += 1
                current_frame += 1

            cap.release()

            if status != "cancelled":
                status = "success"
                status_message = f"Proceso finalizado con exito. Se procesaron {frame_count} frames analizados."
                self.log(status_message)

        except Exception as e:
            status = "error"
            status_message = f"Ocurrio un error inesperado: {e}"
            self.log(status_message)
        finally:
            self.root.after(0, lambda: self.onProcessFinished(status, status_message))

    def createComponents(self):
        containerInputs = ttk.Frame(self.root, padding=10)
        containerInputs.pack(anchor="w", fill="x")
        containerInputs.columnconfigure(1, weight=1)

        # -----------------------------------------------------
        # Control para seleccionar el video

        selectVideoLabel = ttk.Label(containerInputs, text="Seleccione el video")

        self.videoValueVar = tk.StringVar()
        self.videoValueVar.trace_add(["write"], self.traceVideoPath)
        self.videoValueVar.trace_add(["write"], self.addMaxTime)
        self.videoValueVar.trace_add(["write"], self.canStartProcess)
        self.videoValueVar.trace_add(["write"], self.resetVideoSlaves)
        self.entryVideo = ttk.Entry(
            containerInputs, state="readonly", textvariable=self.videoValueVar
        )

        buttonSelectVideo = ttk.Button(
            containerInputs, text="Seleccionar video", command=self.setVideoPath
        )

        selectVideoLabel.grid(row=0, column=0, sticky="w", pady=5)
        self.entryVideo.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        buttonSelectVideo.grid(row=0, column=2, sticky="ew", pady=5)

        # -----------------------------------------------------
        # Seleccionar la carpeta de destino

        selectFinalDirectoryLabel = ttk.Label(
            containerInputs, text="Seleccione la carpeta de destino"
        )

        self.directoryValueVar = tk.StringVar()
        self.directoryValueVar.trace_add(["write"], self.canStartProcess)
        self.directoryValueVar.trace_add(["write"], self.resetDirectorySlaves)
        self.entryDirectory = ttk.Entry(
            containerInputs, state="readonly", textvariable=self.directoryValueVar
        )

        self.buttonOpenDirectory = ttk.Button(
            containerInputs,
            text="Seleccionar carpeta de destino",
            state=DISABLED,
            command=self.setDirectory,
        )

        selectFinalDirectoryLabel.grid(row=1, column=0, sticky="w", pady=5)
        self.entryDirectory.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        self.buttonOpenDirectory.grid(row=1, column=2, sticky="ew", pady=5)

        # -----------------------------------------------------
        # Contenedor de configuracion

        containerCongif = ttk.Frame(self.root)
        containerCongif.pack()

        self.startAtVariable = tk.DoubleVar(value=0)
        self.formatTimeStart = tk.StringVar(value="00:00:00")
        self.formatTimeStart.trace_add(["write"], self.canStartProcess)
        self.startAtLabel = ttk.Label(
            containerCongif,
            text="Minuto inicial",
        )
        self.startAtInput = ttk.Spinbox(
            containerCongif,
            from_=0,
            to=100,
            wrap=True,
            width=3,
            textvariable=self.startAtVariable,
            command=lambda: self.formatTimeStart.set(
                format_timestamp(int(self.startAtVariable.get()) * 60000)
            ),
        )

        self.endAtVariable = tk.DoubleVar(value=0)
        self.endAtVariable.trace_add(["write"], self.canStartProcess)
        self.formatTimeEnd = tk.StringVar(value="00:00:00")
        self.endtAtLabel = ttk.Label(
            containerCongif,
            text="Minuto final",
        )
        self.endAtInput = ttk.Spinbox(
            containerCongif,
            from_=0,
            to=100,
            wrap=True,
            width=3,
            textvariable=self.endAtVariable,
            command=lambda: self.formatTimeEnd.set(
                format_timestamp(int(self.endAtVariable.get()) * 60000)
            ),
        )

        self.secondInterVariable = tk.IntVar(value=0)
        self.secondInterVariable.trace_add(["write"], self.canStartProcess)
        self.secondIntervalLabel = ttk.Label(
            containerCongif, text="Intervalo de extraccion en segundos"
        )
        self.intervalSecondInput = ttk.Spinbox(
            containerCongif,
            from_=0,
            to=100,
            wrap=True,
            width=3,
            textvariable=self.secondInterVariable,
        )

        self.startAtLabel.grid(row=1, column=0, padx=10)
        self.startAtInput.grid(row=2, column=0, sticky="we", padx=10)

        self.endtAtLabel.grid(row=1, column=1, padx=10)
        self.endAtInput.grid(row=2, column=1, sticky="we", padx=10)

        self.secondIntervalLabel.grid(row=1, column=2, padx=10)
        self.intervalSecondInput.grid(row=2, column=2, sticky="we", padx=10)

        containerValues = ttk.Frame(self.root)
        containerValues.pack(pady=10)

        formatInitTime = ttk.Entry(
            containerValues,
            textvariable=f"{self.formatTimeStart}",
            state="readonly",
        )
        formatInitTime.grid(row=0, column=0, padx=10)

        formatEndTime = ttk.Entry(
            containerValues,
            textvariable=f"{self.formatTimeEnd}",
            state="readonly",
        )
        formatEndTime.grid(row=0, column=2)

        # ----------------------------------------------
        # Acciones

        containerPo = ttk.Frame(self.root)
        containerPo.pack()
        self.startProcess = ttk.Button(
            containerPo,
            text="Empezar proceso",
            state=DISABLED,
            command=self.startExtractionProcess,
        )

        self.stateCancel = tk.StringVar(value=DISABLED)
        self.stateCancel.trace_add("write", self.canStartProcess)
        self.cancelProcess = ttk.Button(
            containerPo,
            text="Cancelar proceso",
            state=DISABLED,
            command=self.cancelExtractionProcess,
        )

        self.startProcess.grid(row=0, column=0, padx=5)
        self.cancelProcess.grid(row=0, column=1, padx=5)

        # ----------------------------------------------
        # Area de Logs

        containerLogs = ttk.LabelFrame(self.root, text="Logs del proceso", padding=10)
        containerLogs.pack(fill="both", expand=True, padx=10, pady=10)

        self.logText = tk.Text(containerLogs, height=12, state="disabled", wrap="word")
        logScroll = ttk.Scrollbar(
            containerLogs, orient="vertical", command=self.logText.yview
        )
        self.logText.configure(yscrollcommand=logScroll.set)

        self.logText.pack(side="left", fill="both", expand=True)
        logScroll.pack(side="right", fill="y")

    def resetVideoSlaves(self, *args):
        self.directoryValueVar.set("")
        self.startAtVariable.set(0)
        self.endAtVariable.set(0)
        self.secondInterVariable.set(0)
        self.formatTimeStart.set("00:00:00")
        self.formatTimeEnd.set("00:00:00")

    def resetDirectorySlaves(self, *args):
        self.startAtVariable.set(0)
        self.endAtVariable.set(0)
        self.secondInterVariable.set(0)
        self.formatTimeStart.set("00:00:00")
        self.formatTimeEnd.set("00:00:00")

    def addMaxTime(self, *args):
        self.startAtInput["to"] = self.getMaxMinute(self.videoValueVar.get())
        self.endAtInput["to"] = self.getMaxMinute(self.videoValueVar.get())

    def startExtractionProcess(self):
        self.stop_event.clear()
        self.startProcess["state"] = DISABLED
        self.cancelProcess["state"] = NORMAL
        self.stateCancel.set(NORMAL)

        t1 = Thread(
            target=self.extract_frames,
            args=(
                self.videoValueVar.get(),
                self.startAtVariable.get(),
                self.endAtVariable.get(),
                self.secondInterVariable.get(),
                self.directoryValueVar.get(),
            ),
            daemon=True,
        )
        t1.start()

    def cancelExtractionProcess(self):
        self.stop_event.set()
        self.cancelProcess["state"] = DISABLED

    def onProcessFinished(self, status: str, message: str):
        self.cancelProcess["state"] = DISABLED
        self.stateCancel.set(DISABLED)
        self.canStartProcess()

        if status == "success":
            messagebox.showinfo("Proceso finalizado", message)
        elif status == "cancelled":
            messagebox.showwarning("Proceso cancelado", message)
        else:
            messagebox.showerror("Error en el proceso", message)

    def setDirectory(self):
        askOpenDirectory = fl.askdirectory(initialdir=HOME_PATH)
        if askOpenDirectory:
            self.directoryValueVar.set(
                Path(
                    askOpenDirectory,
                    Path(self.videoValueVar.get()).name.removesuffix(".mp4"),
                )
            )

    def setVideoPath(self):
        askOpenFile = fl.askopenfilename(
            initialdir=HOME_PATH, filetypes=[("Video files", "*.mp4")]
        )
        if askOpenFile:
            self.videoValueVar.set(askOpenFile)

    def traceVideoPath(self, *args):
        if len(self.videoValueVar.get().strip()) == 0:
            self.buttonOpenDirectory["state"] = DISABLED
        else:
            self.buttonOpenDirectory["state"] = NORMAL

    def canStartProcess(self, *args):
        video = self.videoValueVar.get().strip()
        path = self.directoryValueVar.get().strip()
        end = self.endAtVariable.get()
        interval = self.secondInterVariable.get()

        if self.stateCancel.get() == NORMAL:
            return

        if len(video) != 0 and len(path) != 0 and end > 0 and interval > 0:
            self.startProcess["state"] = NORMAL
        else:
            self.startProcess["state"] = DISABLED

    def formatTime(self, value: IntVar):
        self.formatTimeEnd.set(format_timestamp(int(value.get()) * 60000))


if __name__ == "__main__":
    t = tk.Tk()
    a = App(t)
    a.root.mainloop()
