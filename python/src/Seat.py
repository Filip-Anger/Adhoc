class Seat:
    """Represents one seat assignment."""

    def __init__(self, room_id: int, row: int, col: int):
        self.room_id = room_id
        self.row = row
        self.col = col

    def getRoomId(self) -> int:
        return self.room_id

    def getRow(self) -> int:
        return self.row

    def getCol(self) -> int:
        return self.col

    def copy(self):
        return Seat(self.room_id, self.row, self.col)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Seat)
            and self.room_id == other.room_id
            and self.row == other.row
            and self.col == other.col
        )

    def __hash__(self) -> int:
        return hash((self.room_id, self.row, self.col))

    def __repr__(self) -> str:
        return f"Seat(room_id={self.room_id}, row={self.row}, col={self.col})"
