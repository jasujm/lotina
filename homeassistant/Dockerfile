ARG BUILD_FROM
FROM $BUILD_FROM

RUN apt-get update && apt-get install -y python3-pip python3-wheel

WORKDIR /usr/src/lotina

RUN pip3 install click python-dotenv numpy paho-mqtt tensorflow-aarch64 scipy

# Copy data for add-on
COPY . /usr/src/lotina
RUN chmod a+x /usr/src/lotina/run.sh

CMD [ "/usr/src/lotina/run.sh" ]
