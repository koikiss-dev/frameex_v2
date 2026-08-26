"""
Extraccion de fotogramas.

Jorge Posadas (Yako)
"""

import cv2 as cv
import os
import pathlib

CONVERT_MINUTE_VALUE = 60
INSUMOS = f"{os.getcwd()}/videos"
DESTINO = f"{os.getcwd()}/imagenes"


PRUEBA = os.path.join(INSUMOS, "prueba.mp4")


def extract_frames(
    source: str, start_time: int, end_time: int, frame_interval_second: int
):
    if end_time < start_time:
        return

    cap = cv.VideoCapture(source)

    print(cap.get(cv.CAP_PROP_FRAME_COUNT))
    print(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    print(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

    FPS_COUNT = cap.get(cv.CAP_PROP_FPS)

    if FPS_COUNT <= 0:
        cap.release()
        return

    frame_start_minute = int(FPS_COUNT * (start_time * CONVERT_MINUTE_VALUE))
    frame_end_minute = int(FPS_COUNT * (end_time * CONVERT_MINUTE_VALUE))

    """ SE CAMBIA DONDE INICIA """
    cap.set(cv.CAP_PROP_POS_FRAMES, frame_start_minute)

    frame_count = 0
    current_frame_time = frame_start_minute

    frame_step = max(1, int(FPS_COUNT * frame_interval_second))

    print(frame_step)

    while cap.isOpened() and current_frame_time <= frame_end_minute:
        frame_exists, frame = cap.read()
        timestamp = convert_msc(int(cap.get(cv.CAP_PROP_POS_MSEC)))

        if not frame_exists:
            break

        if (current_frame_time - frame_start_minute) % frame_step == 0:

            write_frames_to_images(
                DESTINO, f"imagen-{frame_count}-{timestamp}.png", frame
            )

        frame_count += 1
        current_frame_time += 1

    cap.release()


def convert_msc(ms: int) -> str:
    horas, resto = divmod(ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos, milisegundos = divmod(resto, 1_000)

    if horas > 0:
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}:{milisegundos:03d}"

    return f"{minutos:02d}:{segundos:02d}:{milisegundos:03d}"


def write_frames_to_images(destine: str, title: str, frame: cv.typing.MatLike):
    destine_path = pathlib.Path(destine)
    if not os.path.exists(f"{destine_path}"):
        os.makedirs(f"{destine_path}", exist_ok=True)

    cv.imwrite(f"{destine_path.joinpath(title)}", frame)


if __name__ == "__main__":

    extract_frames(PRUEBA, 13, 14, 1)
