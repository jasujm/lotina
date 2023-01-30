import click
import logging

@click.group()
def cli():
    """The machine learning powered musical soap dispenser"""

try:
    from .processor import process
except:
    logging.info("Could not load process command", exc_info=True)
else:
    cli.add_command(process)

try:
    from .modeltraining import train
except:
    logging.info("Could not load train command", exc_info=True)
else:
    cli.add_command(train)

if __name__ == "__main__":
    cli()
