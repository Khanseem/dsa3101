# grpcio dependency requires C++ compiler
FROM python:3.11

# poppler-utils required for Python pdf2image package
RUN apt-get update && apt-get install -y poppler-utils
RUN apt-get install -y libgl1-mesa-glx

# Install Rust for Python orjson
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN mkdir /app
COPY /app /app
WORKDIR /app
RUN pip install -r requirements.txt

CMD python3 app.py

# BUILD
# docker build -t 12-math-fe .

# RUN (access at localhost:8080)
# docker run --name math-fe -d -p 8080:8080 12-math-fe
