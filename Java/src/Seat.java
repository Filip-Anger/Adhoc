/** Represents one seat by room, row, and column. */
public class Seat {
    int roomId;
    int row;
    int col;

    public Seat(int roomId, int row, int col) {
        this.roomId = roomId;
        this.row = row;
        this.col = col;
    }

    public int getRoomId() {
        return roomId;
    }

    public int getRow() {
        return row;
    }

    public int getCol() {
        return col;
    }

    public Seat copy() {
        return new Seat(roomId, row, col);
    }

    public boolean equals(Object o) {
        if (!(o instanceof Seat)) return false;
        Seat s = (Seat) o;
        return roomId == s.roomId && row == s.row && col == s.col;
    }
}
