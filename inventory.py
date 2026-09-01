"""Player inventory: 10 hotbar slots + 30 storage slots."""
from items import get

HOTBAR = 10
SIZE = 40


class Inventory:
    def __init__(self):
        self.slots = [None] * SIZE  # each entry: [item_id, count]

    def add(self, item_id: str, count: int = 1) -> int:
        """Add items, returns the amount that did NOT fit."""
        max_stack = get(item_id).stack
        # fill existing stacks first
        for slot in self.slots:
            if count <= 0:
                break
            if slot and slot[0] == item_id and slot[1] < max_stack:
                take = min(max_stack - slot[1], count)
                slot[1] += take
                count -= take
        # then empty slots
        for i in range(SIZE):
            if count <= 0:
                break
            if self.slots[i] is None:
                take = min(max_stack, count)
                self.slots[i] = [item_id, take]
                count -= take
        return count

    def remove(self, item_id: str, count: int = 1) -> bool:
        """Remove `count` of item if available. Returns success."""
        if self.count_of(item_id) < count:
            return False
        for i in range(SIZE):
            slot = self.slots[i]
            if slot and slot[0] == item_id:
                take = min(slot[1], count)
                slot[1] -= take
                count -= take
                if slot[1] <= 0:
                    self.slots[i] = None
                if count <= 0:
                    return True
        return count <= 0

    def count_of(self, item_id: str) -> int:
        return sum(s[1] for s in self.slots if s and s[0] == item_id)

    def has_all(self, needs: dict) -> bool:
        return all(self.count_of(k) >= v for k, v in needs.items())

    def consume(self, needs: dict) -> bool:
        if not self.has_all(needs):
            return False
        for k, v in needs.items():
            self.remove(k, v)
        return True

    def to_list(self):
        return [list(s) if s else None for s in self.slots]

    @classmethod
    def from_list(cls, data):
        inv = cls()
        inv.slots = [list(s) if s else None for s in data[:SIZE]] + [None] * (SIZE - len(data))
        return inv
