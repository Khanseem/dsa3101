# dsa3101-2210-12-math

## Project background

Math Handwriting Recognition

Data description
The dataset consists of scanned tutorial worksheets from ST2131/MA2216 tutorials from some years
back. The names and matriculation numbers have been redacted. The worksheets consist of
handwritten answers to probability questions.

Problem statement
To develop an interface/system that can assist with grading handwritten math questions. The interface
could be for the students, or for the instructors who are grading.

Persona
Asoka is a 53-year old professor from the Department of Statistics. She has been teaching courses that
involve proofs (e.g. probability, math-stat) for 25 years. Teaching is her passion, but as class sizes
become bigger, she feels she has to sacrifice handwritten assessments for MCQs due to grading time, to
the detriment of the learning experience and quality to students.

Final Presentation Videos
The front end team should present their product to the faculty member grading (e.g. Asoka)
The modeling team should target the presentation to fellow data scientists.

Additional Information

1. https://github.com/falvaro/seshat  
   a. This repository is for a handwriting parser (it does not work that well, but the paper and
   the code are good starting points).
2. https://mathpix.com/  
   a. A commercial software for recognising math handwriting
3. https://github.com/DPRL/CROHME_2014  
   a. CROHME stands for Competition on Recognition of Handwritten Mathematical
   Expressions. This repository contains code for one of the entries for the 2014
   competition. (Look for others!)
4. Although the data is provided in pdf format, this is not ideal, and you may want to use some
   other language/software that captures the order of the strokes e.g MathML or Xournal++

Demo video showing how the parsers work:

[demo-vid-compressed.zip](https://github.com/Khanseem/dsa3101-2210-12-math/files/9926872/demo-vid-compressed.zip)

## Deployment

The application is containerized via the provided [`Dockerfile`](https://github.com/Khanseem/dsa3101-2210-12-math/blob/main/Dockerfile).

Sample commands to run the container:

```bash
# BUILD
docker build -t 12-math-fe .

# RUN
docker run --name math-fe -d -p 8080:8080 12-math-fe
```

This exposes the application on `http://localhost:8080` (or `http://127.0.0.1:8080` if localhost is re-mapped).
