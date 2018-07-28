from pymongo import MongoClient
import pandas as pd
import click
import os


def insert_data(uri, db, collection, filename):
    col = MongoClient(uri)[db][collection]
    data = pd.read_csv(filename)
    result = col.insert_many(data.to_dict("record"))
    return len(result.inserted_ids)


@click.command()
@click.option("--uri", "-u", default=os.environ.get("MONGODB_URI", "localhost"), help="mongodb uri, default: localhost")
@click.option("--db", "-d", default=os.environ.get("DB_NAME", "VnTrader_Tick_Db"), help="db name, default: VnTrader_Tick_Db")
@click.option("--collection", "-c", default=os.environ.get("COLLECTION", ""), help="collection name, default as filename")
@click.argument("filename", nargs=1)
def command(uri, db, collection, filename):
    if not collection:
        name = os.path.split(filename)[-1]
        collection = name.rsplit(".", 1)[0]
    r = insert_data(uri, db, collection, filename)
    print("Insert %s docs -> %s/%s.%s" % (r, uri, db, collection))


if __name__ == '__main__':
    command()
