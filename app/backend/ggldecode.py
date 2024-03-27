import os

import cv2
from tqdm import tqdm

popplerpath = r".\backend\download\poppler-0.68.0\bin"
os.environ["PATH"] = os.environ["PATH"] + ":" + popplerpath
from google.cloud import vision
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"
] = "./backend/dsa3101-2210-12-math-0c5fbe8196aa.json"


digits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


def CloudVisionTextExtractor(handwritings):
    # convert image from numpy to bytes for submittion to Google Cloud Vision
    _, encoded_image = cv2.imencode(".png", handwritings)
    content = encoded_image.tobytes()
    image = vision.Image(content=content)

    # feed handwriting image segment to the Google Cloud Vision API
    client = vision.ImageAnnotatorClient()
    response = client.document_text_detection(image=image)

    return response


def getTextFromVisionResponse(response, handwritings):
    order = []
    for page in response.full_text_annotation.pages:
        for i, block in enumerate(page.blocks):
            for paragraph in block.paragraphs:
                texts = []
                pmaxX = 0
                pmaxY = 0
                pminX = 1000000
                pminY = 1000000
                for word in paragraph.words:
                    check = False
                    maxX = 0
                    maxY = 0
                    minX = 10000000
                    minY = 10000000
                    word_text = "".join([symbol.text for symbol in word.symbols])
                    for i in word_text:
                        if i in digits:
                            check = True

                    for symbol in word.symbols:
                        for i in symbol.bounding_box.vertices:
                            pmaxX = max(pmaxX, i.x)
                            pminX = min(pminX, i.x)
                            pmaxY = max(pmaxY, i.y)
                            pminY = min(pminY, i.y)
                    if check:
                        for symbol in word.symbols:
                            for i in symbol.bounding_box.vertices:
                                maxX = max(maxX, i.x)
                                minX = min(minX, i.x)
                                maxY = max(maxY, i.y)
                                minY = min(minY, i.y)
                        cv2.rectangle(
                            handwritings, (minX, minY), (maxX, maxY), (36, 255, 12), 2
                        )
                    texts.append(word_text)
                para = " ".join(texts)
                order.append((pminY, pminX, para))
    order.sort()

    ans = order[0][2]
    curY = order[0][0]
    for i in range(1, len(order)):
        if order[i][0] - curY > 10:
            ans += "\n"
            ans += order[i][2]
            curY = order[i][0]
        else:
            ans += " "
            ans += order[i][2]
    return ans, handwritings


def google_api_decode(img):
    responses = CloudVisionTextExtractor(img)
    handwrittenText, bbox_img = getTextFromVisionResponse(responses, img)
    return handwrittenText, bbox_img


"""
def Main():
    from solve import *
    # standard installation
    images = convert_from_path(r".\backend\download\ST2131_Tut1_T05_done.pdf")

    for i in tqdm(range(len(images))):
        
        # Save pages as images in the pdf
        images[i].save(f'backend\image\{i}.jpg', 'JPEG')
        handwriting = cv2.imread(f"backend/image/{i}.jpg")
        # decode text & identify 
        outputtext, outputImag = google_api_decode(handwriting)
        
        # save bboxed image - number highlighter on original image
        cv2.imwrite(f"backend/output/{i}.jpg", outputImag)
        # save parsed document as image
        font = ImageFont.truetype('arial.ttf', 20)
        base = Image.open('backend/blank.png').convert("RGBA")
        img = Image.new("RGB", base.size, (255, 255, 255))
        I1 = ImageDraw.Draw(img)
        counter = 0
        for line in outputtext.splitlines():
            if not solve_str(line):
                I1.text((100, 100+counter), line, font = font, fill = (255, 0, 0))
            else:
                I1.text((100, 100+counter), line, font = font, fill = (0, 0, 0))
            counter += 40
        img.save(f"backend/result/{i}.png")
        

Main()
"""
