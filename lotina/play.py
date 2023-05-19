import contextlib

import click
import sqlalchemy as sa
import pyaudio

from . import db


def get_sample(id):
    return db.engine.execute(
        sa.select([db.samples.c.label, db.samples.c.data]).where(db.samples.c.id == id)
    ).one()


def play_sample(data):
    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16, channels=1, rate=22050, output=True)

    with contextlib.closing(stream):
        stream.write(data)


def play(id):
    """Play sample"""
    sample = get_sample(id)
    click.echo(f"Sample {id}")
    click.echo(f"Label: {sample.label}")
    click.echo("Playing...")

    play_sample(sample.data)
