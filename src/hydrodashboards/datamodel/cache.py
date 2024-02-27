from dataclasses import dataclass, field
from pathlib import Path
import shutil
import pandas as pd
import pickle
import bz2
import _pickle as cPickle

CACHE_DIR = Path(__file__).parent.joinpath("../../../cache").absolute().resolve()


def set_cache_dir(cache_dir):
    global CACHE_DIR
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(exist_ok=True, parents=True)
    CACHE_DIR = Path(cache_dir)


def delete_all_cache():
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class Cache:
    sub_dir: str
    cache_dir: Path = None
    data: dict = field(default_factory=dict)
    data_frame: bool = False
    compression: bool = False
    load_data: bool = True

    def __post_init__(self):
        self.cache_dir = CACHE_DIR / self.sub_dir
        self.mkdir()

    def mkdir(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def delete_cache(self):
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data = {}

    def cache_file(self, key):
        return self.cache_dir.joinpath(f"{key}.pickle")

    def exists(self, key):
        exists = False
        if key in self.data.keys():
            exists = True
        else:
            exists = self.cache_file(key).exists()
            if exists and self.load_data:
                self.get_data(key)
        return exists

    def get_data(self, key):
        if self.data_frame:
            data = pd.read_pickle(self.cache_file(key))
        elif self.compression:
            data = cPickle.load(bz2.BZ2File(self.cache_file(key), "rb"))
        else:
            with open(self.cache_file(key), "rb") as src:
                data = pickle.load(src)
        if self.load_data:
            self.data[key] = data
        else:
            return data

    def set_data(self, data, key):
        cache_file = self.cache_file(key)
        cache_file.parent.mkdir(exist_ok=True, parents=True)
        if self.data_frame:
            data.to_pickle(cache_file)
        elif self.compression:
            with bz2.BZ2File(cache_file, "w") as dst:
                cPickle.dump(data, dst)
        else:
            with open(cache_file, "wb") as dst:
                pickle.dump(data, dst, protocol=pickle.HIGHEST_PROTOCOL)
        if self.load_data:
            self.data[key] = data
