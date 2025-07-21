import copy
from dataclasses import dataclass

import bokeh


@dataclass
class CallbackEdits:
    """If we dont want callbacks to trigger when changing a value
    it is possible to remove the callback temporarily and add it again
    after.
    """

    widget: bokeh.model
    verbose: bool = False

    def __post_init__(self):
        self.cbs = copy.deepcopy(self.widget._callbacks)

    def remove(self, target_fun=None):
        """Remove all callbacks or when target_fun is provided,
        only that one.
        """
        for key, val in self.cbs.items():
            for fun in val:
                # Only remove target_fun
                if target_fun is not None:
                    if fun != target_fun:
                        continue

                if self.verbose:
                    print(f"Removing callback; {key}:{fun}")
                self.widget.remove_on_change(key, fun)

    def add(self):
        """Add callbacks again. Defining the same callback twice
        doesnt hurt, so we dont have to specify the target function.
        """
        for key, val in self.cbs.items():
            for fun in val:
                if self.verbose:
                    print(f"Add callback; {key}:{fun}")
                self.widget.on_change(key, fun)
