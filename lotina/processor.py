import os
import sys

import click
from dotenv import load_dotenv
import numpy as np
import paho.mqtt.client as mqtt

from .model import to_features

TOPIC_SUB = "lotina/+/samples"
N_SAMPLES_FOR_PREDICTION = 3

load_dotenv()


def load_model():
    import tensorflow.keras as keras

    return keras.models.load_model("lotina.tf")


class Processor:
    def __init__(self, label, classify, prediction):
        self._label = label
        self._model = load_model() if classify else None
        self._prediction = prediction
        self._data = bytearray()
        self._samples = []

    def init_mqtt_client(self, client):
        client.on_connect = self.on_connect
        client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        click.echo(f"Connected with result code: {rc}")
        client.subscribe(TOPIC_SUB)

    def on_message(self, client, userdata, msg):
        if self._label:
            self._data += msg.payload
        prediction = self._prediction
        if not msg.payload:
            self._samples.clear()
        elif self._model:
            self._samples.append(to_features(msg.payload))
            if len(self._samples) >= N_SAMPLES_FOR_PREDICTION:
                prediction = self._make_prediction()
                self._samples.pop(0)
        if prediction is not None:
            prediction_topic = msg.topic.replace("/samples", "/prediction")
            client.publish(prediction_topic, prediction)

    def save_sample(self):
        if self._label:
            from sqlalchemy import insert
            from . import db

            click.echo(
                f"Saving sample, label {self._label}, sample size {len(self._data)}"
            )
            db.engine.execute(
                insert(db.samples).values(label=self._label, data=self._data)
            )

    def _make_prediction(self):
        from tensorflow.math import reduce_mean

        prediction = self._model(np.stack(self._samples))
        prediction_mean = reduce_mean(prediction)
        return int(255 * float(prediction_mean))


def process(label, classify, prediction):
    """MQTT message processor"""
    recorder = Processor(label, classify, prediction)

    client = mqtt.Client()
    recorder.init_mqtt_client(client)

    client.username_pw_set(os.getenv("MQTT_USER"), os.getenv("MQTT_PASSWD"))
    client.connect(os.getenv("MQTT_BROKER"))

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        recorder.save_sample()
