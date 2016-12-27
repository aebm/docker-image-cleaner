FROM python:2.7.12-alpine
MAINTAINER Alejandro Brito Monedero <alejandro.monedero@gmail.com>

WORKDIR /usr/src/app
COPY ["di_cleaner.py", "test_di_cleaner.py", "requirements.txt", "/usr/src/app/"]
RUN ["/usr/local/bin/pip", "install", "--requirement", "requirements.txt"]

ENTRYPOINT ["/usr/src/app/di_cleaner.py"]
