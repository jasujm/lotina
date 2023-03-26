from collections import defaultdict
import random
import functools

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sqlalchemy as sa
import scipy.signal
import tensorflow.keras as keras
from tensorflow.keras.utils import timeseries_dataset_from_array
from tensorflow.data import Dataset
from tensorflow import reshape

from . import db
from .model import get_input_shape, to_features


SEQUENCE_LENGTH = 10
SEQUENCE_STRIDE = SEQUENCE_LENGTH // 2


def load_dataset_for_training():
    datasets = []
    rows = list(db.engine.execute(sa.select([db.samples.c.label, db.samples.c.data])))
    random.shuffle(rows)
    for label, data in rows:
        features = timeseries_dataset_from_array(
            to_features(data),
            None,
            SEQUENCE_LENGTH,
            sequence_stride=SEQUENCE_STRIDE,
            batch_size=None,
        )
        labels = Dataset.from_tensors([label.startswith("tap")]).repeat()
        datasets.append(Dataset.zip((features, labels)))
    return (
        functools.reduce(lambda x, y: x.concatenate(y), datasets)
        .shuffle(1000)
        .batch(64)
    )


def split_dataset(dataset, *, split=0.2):
    N = int(int(dataset.cardinality()) * split)
    return dataset.take(N), dataset.skip(N)


def train_model(dataset, *, epochs, validation_split=0.2):
    validate_dataset, train_dataset = split_dataset(dataset, split=validation_split)

    model = keras.Sequential(
        [
            keras.layers.Input(get_input_shape()),
            keras.layers.BatchNormalization(),
            keras.layers.Conv1D(32, (3,), activation="relu"),
            keras.layers.MaxPooling1D(),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        loss="binary_crossentropy", optimizer="adam", metrics=["binary_accuracy"]
    )
    history = model.fit(
        train_dataset,
        epochs=epochs,
        validation_data=validate_dataset,
    )

    model.summary()

    return model, history


def plot_loss(history):
    plt.plot(history.history["loss"], label="Training")
    plt.plot(history.history["val_loss"], label="Validation")
    plt.xlabel("Epoch")
    plt.ylabel("Error")
    plt.legend()
    plt.grid(True)
    plt.show()


def train(evaluate, save):
    """Train model from audio samples"""
    dataset = load_dataset_for_training()
    if evaluate:
        test_dataset, train_dataset = split_dataset(dataset)
        model, history = train_model(train_dataset, epochs=200)
        plot_loss(history)
        test_results = model.evaluate(test_dataset, return_dict=True)
        click.echo(f"Error on test set: {test_results}")

    if save:
        model, _ = train_model(dataset, epochs=1000, validation_split=0.0)
        model.save("lotina.tf")
