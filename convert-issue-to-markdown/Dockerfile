FROM ubuntu:bionic

# create source folder
RUN mkdir /app
WORKDIR /app

# install source code
ADD run.py .
ADD entrypoint.sh .

ENTRYPOINT ["./entrypoint.sh"]