import collections
from typing import Optional, Iterable, Any


class ExecutionTimes(collections.UserList):
    def __init__(self, initlist: Optional[Iterable[Any]] = None, max_items: int = None) -> None:
        super().__init__(initlist)
        self.max_items = max_items

    def append(self, item: Any) -> None:
        super().append(item)
        while len(self.data) > self.max_items:
            self.data.pop(0)

    def average(self) -> float:
        if not self.data:
            return 0.0
        return sum(self.data) / len(self.data)

    def max(self) -> float:
        if not self.data:
            return 0.0
        return max(self.data)
