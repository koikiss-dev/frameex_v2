import cv2 as cv


def formatTime(ms: int) -> str:
    horas, resto = divmod(ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos, _ = divmod(resto, 1_000)

    if horas > 0:
        return f"{horas:02d}_{minutos:02d}_{segundos:02d}"

    return f"{horas:02d}_{minutos:02d}_{segundos:02d}"




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

        return total_frames / (fps * 60)
    finally:
        if cap is not None:
            cap.release()
    
