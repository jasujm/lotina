import click
import logging


@click.group()
def cli():
    """The machine learning powered musical soap dispenser"""


@cli.command()
@click.option("--evaluate/--no-evaluate", default=True, help="Evaluate model")
@click.option("--save/--no-save", default=False, help="Save model")
def train(evaluate, save):
    """Train model from audio samples"""

    from .modeltraining import train

    train(evaluate, save)


@cli.command()
@click.option("--label")
@click.option("--classify/--no-classify", default=False)
@click.option("--prediction", type=int)
def process(label, classify, prediction):
    """MQTT message processor"""

    from .processor import process

    process(label, classify, prediction)


if __name__ == "__main__":
    cli()
