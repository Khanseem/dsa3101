# download files for app
import os
import zipfile

import numpy as np
import PIL
import wget
from backend.ggldecode import *
from backend.solve import *
import textwrap


# if no parser is chosen:
# util available - number highlighter
def num_highlighter(img):
    if isinstance(img, PIL.Image.Image):
        img = np.asarray(img)
    # img in numpy array format
    outputtext, outputImag = google_api_decode(img)
    # output image in numpy array format
    return outputImag


# if parser chosen:
# google api parser
# util available - solver
def gglapi_parse(img, enable_solver=False):
    if isinstance(img, PIL.Image.Image):
        img = np.asarray(img)
    # img in numpy array format
    outputtext, outputImag = google_api_decode(img)
    font = ImageFont.truetype("backend/arial.ttf", 40)
    base = Image.open("backend/blank.png").convert("RGBA")
    img = Image.new("RGB", base.size, (255, 255, 255))
    I1 = ImageDraw.Draw(img)
    if enable_solver:
        counter = 0
        for line in outputtext.splitlines():
            if not solve_str(line):
                for lin in textwrap.wrap(line, width=100):
                    I1.text((100, 100 + counter), lin, font=font, fill=(255, 0, 0))
                    counter += 40
                #I1.text((100, 100 + counter), line, font=font, fill=(255, 0, 0))
            else:
                for lin in textwrap.wrap(line, width=100):
                    I1.text((100, 100 + counter), lin, font=font, fill=(0, 0, 0))
                    counter += 40
                #I1.text((100, 100 + counter), line, font=font, fill=(0, 0, 0))
            counter += 40
    else:
        counter = 0
        for line in outputtext.splitlines():
            for lin in textwrap.wrap(line, width=100):
                    I1.text((100, 100 + counter), lin, font=font, fill=(0, 0, 0))
                    counter += 40
            counter += 40
    return np.array(img)


def setup_env():
    # create storage folder for backend output
    if not os.path.isdir("./backend/output"):
        os.mkdir("./backend/output")

    if not os.path.isdir("./backend/download"):
        os.mkdir("./backend/download")
    if not os.path.isdir("./backend/download/poppler-22.04.0"):
        url = "https://github.com/oschwartz10612/poppler-windows/releases/download/v22.04.0-0/Release-22.04.0-0.zip"
        wget.download(url, out="./backend/download")
        with zipfile.ZipFile(
            "./backend/download/Release-22.04.0-0.zip", "r"
        ) as zip_ref:
            zip_ref.extractall("backend/download")
    popplerpath = "./backend/download/poppler-22.04.0/Library/bin"
    if os.name == "nt":
        os.environ["PATH"] = popplerpath
    else:
        os.environ["PATH"] = os.environ["PATH"] + ":" + popplerpath
