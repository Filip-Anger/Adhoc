import java.io.File;
import java.io.FileNotFoundException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Scanner;

/** Stores one input instance: students, rooms, groups, cheaters, and coefficients. */
public class ExamInstance {
    final int N; // number of students
    final int M; // number of rooms
    final int G; // number of groups
    final int C; // number of cheaters

    // coefficients for cost function
    final double cCheat;
    final double cSplit;
    final double cDiam;

    final List<Student> students;
    final List<Room> rooms;
    final List<Group> groups;
    final List<Student> cheaters;

    /** Reads the task input format from a file. */
    ExamInstance(String filename) {
        int n = 0, m = 0, g = 0, c = 0;
        double tempCCheat = 1.0, tempCSplit = 1.0, tempCDiam = 1.0;

        ArrayList<Student> studs = new ArrayList<>();
        ArrayList<Room> rms = new ArrayList<>();
        ArrayList<Group> grps = new ArrayList<>();
        ArrayList<Student> chtrs = new ArrayList<>();

        File file = new File(filename);

        try {
            Scanner scanner = new Scanner(file);

            n = scanner.nextInt();
            m = scanner.nextInt();
            g = scanner.nextInt();
            
            tempCCheat = scanner.nextDouble();
            tempCSplit = scanner.nextDouble();
            tempCDiam = scanner.nextDouble();

            for (int gi = 0; gi < g; gi++) {
                grps.add(new Group(gi));
            }

            for (int studentId = 0; studentId < n; studentId++) {
                int groupId = scanner.nextInt();
                Student student = new Student(studentId, groupId);
                studs.add(student);

                if (0 <= groupId && groupId < g) {
                    grps.get(groupId).addStudent(student);
                }
                else System.out.println("Input file is invalid!");
            }

            for (int roomId = 0; roomId < m; roomId++) {
                int rows = scanner.nextInt();
                int cols = scanner.nextInt();
                rms.add(new Room(roomId, rows, cols));
            }

            c = scanner.nextInt();

            for (int i = 0; i < c; i++) {
                int stud = scanner.nextInt();
                Student s = studs.get(stud);
                chtrs.add(s);
                s.cheater = true;
            }

            scanner.close();
        } catch (FileNotFoundException e) {
            System.out.println("Could not read file!");
            e.printStackTrace();
        }

        N = n;
        M = m;
        G = g;
        C = c;

        cCheat = tempCCheat;
        cSplit = tempCSplit;
        cDiam = tempCDiam;

        students = Collections.unmodifiableList(studs);
        rooms = Collections.unmodifiableList(rms);
        groups = Collections.unmodifiableList(grps);
        cheaters = Collections.unmodifiableList(chtrs);
    }
}