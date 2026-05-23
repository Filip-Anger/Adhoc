class Room:
    """Represents one room with a rectangular seating layout."""

    def __init__(self, room_id: int, rows: int, cols: int):
        self.id = room_id
        self.rows = rows
        self.cols = cols

    def getId(self) -> int:
        return self.id

    def getRows(self) -> int:
        return self.rows

    def getCols(self) -> int:
        return self.cols

    def getCapacity(self) -> int:
        return self.rows * self.cols

    def __repr__(self) -> str:
        return f"Room(id={self.id}, rows={self.rows}, cols={self.cols})"
