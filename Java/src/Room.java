/** Represents one rectangular exam room. */
public class Room {
    int id;
    int rows;
    int cols;

    public Room(int ID, int rows, int cols) {
        this.id = ID;
        this.rows = rows;
        this.cols = cols;
    }

    public int getId() {
        return this.id;
    }

    public int getRows() {
        return this.rows;
    }

    public int getCols() {
        return this.cols;
    }

    public int getCapacity() {
        return this.rows * this.cols;
    }
}
