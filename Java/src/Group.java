import java.util.ArrayList;

/** Represents one exam group and the students belonging to it. */
public class Group {
    int id;
    ArrayList<Student> students;

    public Group(int ID) {
        this.id = ID;
        this.students = new ArrayList<Student>();
    }

    public int getId() {
        return this.id;
    }

    /** Adds a student to this group if the student is not already present. */
    public void addStudent(Student st) {
        if (!this.students.contains(st)) {
            this.students.add(st);
        }
    }

    public boolean containsStudent(Student st) {
        return this.students.contains(st);
    }

    public int getGroupSize() {
        return this.students.size();
    }
}
