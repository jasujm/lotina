import os

from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

load_dotenv()

engine = sa.create_engine(os.getenv("DATABASE_URL"))

metadata = sa.MetaData()
samples = sa.Table(
    "samples",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("label", sa.String(63), nullable=False),
    sa.Column("data", mysql.LONGBLOB, nullable=False),
)

metadata.create_all(engine)
