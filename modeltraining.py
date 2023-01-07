import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sqlalchemy as sa

import db
from model import prepare_samples


def load_and_prepare_recordings():
    return pd.DataFrame(
        [
            {
                "is_tap": row.label == "tap",
                **{
                    f"samples_bin_{n}": sample
                    for (n, sample) in enumerate(prepare_samples(row.data))
                },
            }
            for row in db.engine.execute(
                sa.select([db.samples.c.label, db.samples.c.data])
            )
        ]
    )


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


def train_model(features, labels):
    import tensorflow.keras as keras

    normalizer = keras.layers.Normalization()
    normalizer.adapt(np.array(features))

    model = keras.Sequential(
        [
            normalizer,
            keras.layers.Dense(64, activation="relu"),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        loss="binary_crossentropy", optimizer="adam", metrics=["binary_accuracy"]
    )
    history = model.fit(
        features,
        labels,
        epochs=500,
        validation_split=0.2,
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
@click.option("--evaluate/--no-evaluate", default=True)
@click.option("--save/--no-save", default=False)
def main(evaluate, save):
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
        click.echo(prediction_comparison)

    if save:
        all_features, all_labels = split_dataset_to_features_and_labels(dataset)
        model, _ = train_model(all_features, all_labels)
        model.save("lotina.tf")


if __name__ == "__main__":
    main()
