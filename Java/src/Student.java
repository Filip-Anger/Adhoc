/** Represents one student, their exam group, and whether they are a listed cheater. */
public class Student {
    int id;
    int groupId;
    boolean cheater;

    public Student(int ID, int groupId) {
        this.id = ID;
        this.groupId = groupId;
        cheater = false;
    }

    public int getId() {
        return this.id;
    }

    public int getGroupId() {
        return this.groupId;
    }

    public boolean isCheater() {
        return cheater;
    }
}
