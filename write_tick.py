from pymongo import MongoClient
from pymongo.collection import Collection
import pandas as pd
from jaqs.data.dataview import DataView
import click
import logging


FIELDS_MAP = {
    "contract": "vtSymbol",
    "last": "lastPrice",
    "volume": "lastVolume",
    "time": "datetime",
}


def fields_map(name=""):
    try:
        return FIELDS_MAP[name]
    except KeyError:
        if "_" in name:
            return name.replace("_", "").replace("price", "Price").replace("volume", "Volume")
        else:
            return name


def insert(collection, data):
    assert isinstance(data, pd.DataFrame), type(data)
    assert isinstance(collection, Collection), type(collection)

    if data.index.name != None:
        data.reset_index(inplace=True)
    r = collection.insert_many(data.to_dict("records"))
    return len(r.inserted_ids)


def read_csv(file_name):
    return pd.read_csv(file_name, index_col=0)


def apdat_data(frame):
    assert isinstance(frame, pd.DataFrame), type(frame)

    frame = frame.rename_axis(fields_map, 1)
    frame["datetime"] = frame["datetime"].apply(pd.to_datetime)
    frame["time"] = frame["datetime"].apply(lambda t: t.strftime("%H:%M:%S.%f"))
    frame["date"] = frame["datetime"].apply(lambda t: t.strftime("%Y%m%d"))
    frame["volume"] = frame["lastVolume"].sum()
    frame["openInterest"] = 0
    frame[["symbol", "exchange"]] = pd.DataFrame(list(map(lambda s: s.split(":", 1), frame["vtSymbol"])),
                                                 index=frame.index, columns=["symbol", "exchange"])
    for name in ["openPrice", "highPrice", "lowPrice", "preClosePrice", "upperLimit", "lowerLimit"]:
        frame[name] = 0
    return frame


# @click.command("write")
# @click.argument("file_name", nargs=1)
# @click.option("-m", "--mongodb_uri", default="localhost:27017")
# @click.option("-d", "--db", default="VnTrader_Tick_Db",)
# @click.option("-c", "--col", default=None)
def write_csv(file_name, mongodb_uri="localhost:27017", db="VnTrader_Tick_Db", col=None):
    csv = read_csv(file_name)
    data = apdat_data(csv)
    client = MongoClient(mongodb_uri)
    col_name = data.ix[0, "vtSymbol"] if col is None else col
    result = insert(client[db][col_name], data)
    logging.warning("insert data to %s.%s | %s", db, col_name, result)


def is_csv(name):
    return name.endswith(".csv")


if __name__ == '__main__':
    import os

    path = r"E:\CoinData\btc"
    os.chdir(path)
    for name in filter(is_csv, os.listdir(path)):
        print(name)
        write_csv(name, "192.168.0.102:27017")
        print("finish")