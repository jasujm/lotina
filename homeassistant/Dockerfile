ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /usr/src/lotina

RUN apt-get update && apt-get install -y python3-pip python3-wheel
RUN pip3 install click python-dotenv numpy paho-mqtt tensorflow-aarch64

# Copy data for add-on
COPY . /usr/src/lotina
RUN chmod a+x /usr/src/lotina/run.sh

CMD [ "/usr/src/lotina/run.sh" ]
