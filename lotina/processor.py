import os
import sys

import click
from dotenv import load_dotenv
import numpy as np
import paho.mqtt.client as mqtt
import sqlalchemy as sa

from . import db
from .model import extract_features_from_data

TOPIC_SUB = "/lotina/+/samples"

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
            samples = np.array(extract_features_from_data(msg.payload))
            prediction = self._model(samples)[0][0]
            prediction = int(255 * prediction)
        if prediction is not None:
            prediction_topic = msg.topic.replace("samples", "prediction")
            client.publish(prediction_topic, prediction.to_bytes(1, "little"))


@click.command()
@click.option("--label")
@click.option("--classify/--no-classify", default=False)
@click.option("--prediction", type=int)
def process(label, classify, prediction):
    """MQTT message processor"""
    recorder = Processor(label, classify, prediction)

    client = mqtt.Client()
    client.on_connect = recorder.on_connect
    client.on_message = recorder.on_message

    client.username_pw_set(os.getenv("MQTT_USER"), os.getenv("MQTT_PASSWD"))
    client.connect(os.getenv("MQTT_BROKER"))

    client.loop_forever()
