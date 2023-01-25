import click

from .processor import process
from .modeltraining import train


@click.group()
def cli():
    """The machine learning powered musical soap dispenser"""


cli.add_command(process)
cli.add_command(train)

if __name__ == "__main__":
    cli()
