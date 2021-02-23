FROM ubuntu:bionic
ARG BUILD_VERSION

# install Python
RUN apt-get update
RUN apt-get install -y python3.8 python3.8-distutils wget
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 2

# create source folder
RUN mkdir /app
WORKDIR /app

# install source code
ADD run.py .

ENTRYPOINT ["python3", "run.py"]