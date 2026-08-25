import cv2 as cv
import os
import pathlib


def extract_frames():
    cap = cv.VideoCapture("./prueba.mp4")

    print(cap.get(cv.CAP_PROP_FRAME_COUNT))
    print(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    print(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

    frame_count = 0
    frame_interval = 1  # 1 IMAGEN CADA SEGUNDO

    while cap.isOpened():
        frame_exists, frame = cap.read()
        actual_second = cap.get(cv.CAP_PROP_POS_MSEC) / 1000

        if not frame_exists:
            break

        """ CADA SEGUNDO SE SACA UNA IMAGEN """
        if actual_second % frame_interval == 0:
            cv.imwrite(
                f"{os.getcwd()}/imagenes/imagen-{frame_count}-{int(cap.get(cv.CAP_PROP_POS_MSEC))}.png",
                frame,
            )

        frame_count += 1

    cap.release()


if __name__ == "__main__":
    if not os.path.exists(f"{os.getcwd()}/imagenes"):
        os.mkdir(f"{os.getcwd()}/imagenes")
        
    extract_frames()
