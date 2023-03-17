from dataclasses import dataclass, field
from pathlib import Path
import shutil
import pandas as pd
import pickle

CACHE_DIR = Path(__file__).parent.joinpath("../../../cache").absolute().resolve()


@dataclass
class Cache:
    sub_dir: str
    cache_dir: Path = None
    data: dict = field(default_factory=dict)
    data_frame: bool = False

    def __post_init__(self):
        self.cache_dir = CACHE_DIR / self.sub_dir
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
            cache_file = self.cache_file(key)
            exists = self.cache_file(key).exists()
            if exists:
                if self.data_frame:
                    self.data[key] = pd.read_pickle(cache_file)
                else:
                    with open(cache_file, "rb") as src:
                        self.data[key] = pickle.load(src)
        return exists

    def set_data(self, data, key):
        self.data[key] = data
        cache_file = self.cache_file(key)
        cache_file.parent.mkdir(exist_ok=True, parents=True)
        if self.data_frame:
            data.to_pickle(cache_file)
        else:
            with open(cache_file, "wb") as dst:
                pickle.dump(data, dst, protocol=pickle.HIGHEST_PROTOCOL)
