import random

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sqlalchemy as sa

from . import db
from .model import extract_features_from_data


def load_and_prepare_recordings():
    rows = [
        {
            "is_tap": row.label.startswith("tap"),
            **{
                f"features_{n}": sample
                for (n, sample) in enumerate(extract_features_from_data(row.data))
            },
        }
        for row in db.engine.execute(sa.select([db.samples.c.label, db.samples.c.data]))
    ]
    random.shuffle(rows)
    return pd.DataFrame(rows)


def split_dataset_to_features_and_labels(dataset):
    features = dataset.copy()
    labels = features["is_tap"]
    features.drop("is_tap", axis=1, inplace=True)
    return features, labels


def get_train_and_test_sets(dataset):
    train_dataset = dataset.sample(frac=0.9)
    test_dataset = dataset.drop(train_dataset.index)
    return [
        *split_dataset_to_features_and_labels(train_dataset),
        *split_dataset_to_features_and_labels(test_dataset),
    ]


def train_model(features, labels, *, epochs=2000, validation_split=0.2):
    import tensorflow.keras as keras

    normalizer = keras.layers.Normalization()
    normalizer.adapt(np.array(features))

    model = keras.Sequential(
        [
            normalizer,
            keras.layers.Dense(60, activation="relu"),
            keras.layers.Dense(40, activation="relu"),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        loss="binary_crossentropy", optimizer="adam", metrics=["binary_accuracy"]
    )
    history = model.fit(
        features,
        labels,
        epochs=epochs,
        validation_split=validation_split,
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


@click.command()
@click.option("--evaluate/--no-evaluate", default=True, help="Evaluate model")
@click.option("--save/--no-save", default=False, help="Save model")
def train(evaluate, save):
    """Train model from audio samples"""
    dataset = load_and_prepare_recordings()
    if evaluate:
        (
            train_features,
            train_labels,
            test_features,
            test_labels,
        ) = get_train_and_test_sets(dataset)
        model, history = train_model(train_features, train_labels)
        plot_loss(history)
        test_results = model.evaluate(test_features, test_labels)
        click.echo(f"Error on test set: {test_results}")
        predictions = model.predict(test_features).flatten()
        prediction_comparison = pd.DataFrame(
            {
                "prediction_raw": predictions,
                "prediction": predictions > 0.5,
                "actual": test_labels.to_numpy().flatten(),
            }
        )
        click.echo(prediction_comparison.to_string())

    if save:
        all_features, all_labels = split_dataset_to_features_and_labels(dataset)
        model, _ = train_model(
            all_features, all_labels, epochs=5000, validation_split=0.0
        )
        model.save("lotina.tf")
