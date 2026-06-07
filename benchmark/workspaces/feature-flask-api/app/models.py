class Item:
    def __init__(self, id: int, name: str, price: float = 0):
        self.id = id
        self.name = name
        self.price = price

    def to_dict(self):
        return {"id": self.id, "name": self.name, "price": self.price}


_items = {}
_next_id = 1
