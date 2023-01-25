import json
import os
import sys

import click
from dotenv import load_dotenv
import numpy as np
import paho.mqtt.client as mqtt
import sqlalchemy as sa

from model import prepare_samples
import db

TOPIC_SUB = "/lotina/audio/samples"
TOPIC_PREDICTION = "/lotina/audio/prediction"

load_dotenv()


def load_model():
    import tensorflow.keras as keras

    return keras.models.load_model("lotina.tf")


class Processor:
    def __init__(self, label, classify, prediction):
        self._label = label
        self._model = load_model() if classify else None
        self._prediction = prediction

    def on_connect(self, client, userdata, flags, rc):
        click.echo(f"Connected with result code: {rc}")
        client.subscribe(TOPIC_SUB)

    def on_message(self, client, userdata, msg):
        if self._label:
            db.engine.execute(
                sa.insert(db.samples).values(label=self._label, data=msg.payload)
            )
        prediction = self._prediction
        if self._model:
            samples = np.array(prepare_samples(msg.payload))
            prediction = self._model(samples)[0][0]
            prediction = int(255 * prediction)
        if prediction is not None:
            client.publish(TOPIC_PREDICTION, prediction.to_bytes(1, "little"))


def load_config():
    with open("lotina.conf") as f:
        return json.load(f)


@click.command()
@click.option("--label")
@click.option("--classify/--no-classify", default=False)
@click.option("--prediction", type=int)
def main(label, classify, prediction):
    config = load_config()
    recorder = Processor(label, classify, prediction)

    client = mqtt.Client()
    client.on_connect = recorder.on_connect
    client.on_message = recorder.on_message

    client.username_pw_set(os.getenv("MQTT_USER"), os.getenv("MQTT_PASSWD"))
    client.connect(os.getenv("MQTT_BROKER"))

    client.loop_forever()


if __name__ == "__main__":
    main()
