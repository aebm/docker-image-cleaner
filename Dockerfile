FROM python:2.7.9-onbuild
MAINTAINER Eduardo Ferro <eferro@alea-soluciones.com>


ENTRYPOINT ["/usr/src/app/di_cleaner.py"]
