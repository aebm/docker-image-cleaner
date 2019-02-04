FROM python:3.7.2-alpine3.8
MAINTAINER Alejandro Brito Monedero <alejandro.monedero@gmail.com>

WORKDIR /usr/src/app
COPY ["di_cleaner.py", "test_di_cleaner.py", "requirements.txt", "/usr/src/app/"]
RUN ["/usr/local/bin/pip", "install", "--requirement", "requirements.txt"]

ENTRYPOINT ["/usr/src/app/di_cleaner.py"]
