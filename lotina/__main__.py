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
def process(label, classify):
    """MQTT message processor"""

    from .processor import process

    process(label, classify)


@cli.command()
@click.argument("id")
def play(id):
    """Play sample

    Play sample identified by ID.
    """

    from .play import play

    play(id)


if __name__ == "__main__":
    cli()
