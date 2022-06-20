from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("hydrodashboards")
except PackageNotFoundError:
    pass
