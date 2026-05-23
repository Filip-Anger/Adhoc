import java.io.File;
import java.io.IOException;
import java.io.PrintStream;
import java.util.*;

/**
 * Represents one seating assignment. seating.get(i) is student i's seat.
 */
public class ExamSolution {
    ExamInstance instance;

    // seating.get(studentId) stores the room, row, and column assigned to that student.
    ArrayList<Seat> seating;

    /**
     * Creates an empty solution.
     */
    public ExamSolution(ExamInstance inst) {
        this.instance = inst;
        this.seating = new ArrayList<Seat>();

        ArrayList<Student> students = new ArrayList<>(instance.students);
        students.sort(Comparator.comparingInt(s -> s.groupId));

        ArrayList<ArrayList<Student>> groupedStudents = new ArrayList<>();
        for (Student student : students) {
            if (groupedStudents.get(student.groupId) != null) {
                groupedStudents.set(student.groupId, (ArrayList<Student>) List.of(new Student[]{student}));
            }
        }
    }

    /**
     * Creates a complete initial solution, optionally shuffled.
     */
    public ExamSolution(ExamInstance inst, boolean random) {
        this.instance = inst;
        this.seating = new ArrayList<Seat>();

        ArrayList<Seat> seats = new ArrayList<>();

        // Collect all available seats.
        for (Room room : instance.rooms) {
            for (int row = 0; row < room.getRows(); row++) {
                for (int col = 0; col < room.getCols(); col++) {
                    seats.add(new Seat(room.getId(), row, col));
                }
            }
        }

        if (random) Collections.shuffle(seats);

        // Assign seats to students 0..N-1.
        for (int i = 0; i < instance.N; i++) {
            seating.add(seats.get(i));
        }
    }

    /**
     * Returns an independent copy of this solution.
     */
    public ExamSolution copy() {
        ExamSolution sol = new ExamSolution(instance);

        for (Seat s : seating) {
            sol.seating.add(s.copy());
        }

        return sol;
    }

    /**
     * Assigns one student to one seat.
     */
    public void seatStudent(Student stud, Seat seat) {
        seating.set(stud.id, seat);
    }

    /**
     * Checks whether a seat is inside its room bounds.
     */
    private boolean isValidSeatPosition(Seat seat) {
        if (seat.getRoomId() < 0 || seat.getRoomId() >= instance.M) {
            return false;
        }

        Room room = instance.rooms.get(seat.getRoomId());

        return seat.getRow() >= 0 && seat.getRow() < room.getRows() &&
                seat.getCol() >= 0 && seat.getCol() < room.getCols();
    }

    /**
     * Checks that all students have valid, unique seats.
     */
    public boolean checkValid() {
        HashSet<Seat> taken = new HashSet<Seat>();

        for (int i = 0; i < instance.N; i++) {
            if (!isValidSeatPosition(seating.get(i))) return false;
            if (taken.contains(seating.get(i))) return false;
            taken.add(seating.get(i));
        }

        return true;
    }

    /**
     * Counts same-group students adjacent to listed cheaters.
     */
    public int cheaterIsolation() {
        int cheatPenalty = 0;

        for (Student s1 : instance.cheaters) {
            for (Student s2 : instance.groups.get(s1.groupId).students) {
                if (s1.id == s2.id) continue;

                Seat seat1 = seating.get(s1.id);
                Seat seat2 = seating.get(s2.id);

                if (seat1.roomId == seat2.roomId &&
                        Math.abs(seat1.row - seat2.row) <= 1 &&
                        Math.abs(seat1.col - seat2.col) <= 1) {
                    cheatPenalty++;
                }
            }
        }

        return cheatPenalty;
    }

    /**
     * Groups the seats of every exam group by room.
     */
    private TreeMap<Integer, ArrayList<Seat>> seatsByRoom(Group group) {
        TreeMap<Integer, ArrayList<Seat>> distr = new TreeMap<Integer, ArrayList<Seat>>();

        for (Student s : group.students) {
            Seat seat = seating.get(s.id);

            if (!distr.containsKey(seat.roomId)) {
                distr.put(seat.roomId, new ArrayList<Seat>());
            }

            distr.get(seat.roomId).add(seat);
        }

        return distr;
    }

    /**
     * Computes the group splitting part before normalization.
     */
    private double rawGroupSplittingCost() {
        double splittingCost = 0.0;

        for (Group group : instance.groups) {
            TreeMap<Integer, ArrayList<Seat>> distr = seatsByRoom(group);
            splittingCost += distr.size() * instance.cSplit;
        }

        return splittingCost;
    }

    /**
     * Computes the diameter part before normalization.
     */
    private double rawDiameterCost() {
        double diameterCost = 0.0;

        for (Group group : instance.groups) {
            TreeMap<Integer, ArrayList<Seat>> distr = seatsByRoom(group);

            for (ArrayList<Seat> A : distr.values()) {
                double diam = 0.0;

                // Find this group's diameter in the room.
                for (int i = 0; i < A.size(); i++) {
                    Seat seat1 = A.get(i);

                    for (int j = i + 1; j < A.size(); j++) {
                        Seat seat2 = A.get(j);

                        double distSquared =
                                (seat1.col - seat2.col) * (seat1.col - seat2.col) +
                                        (seat1.row - seat2.row) * (seat1.row - seat2.row);

                        diam = Math.max(diam, distSquared);
                    }
                }

                diameterCost += Math.sqrt(diam) * instance.cDiam;
            }
        }

        return diameterCost;
    }

    /**
     * Computes group splitting and diameter costs.
     */
    public double invigilatorCost() {
        return rawGroupSplittingCost() + rawDiameterCost();
    }

    /**
     * Computes the number of cheating penalties per room.
     */
    private int[] cheatPenaltyByRoom() {
        int[] penalties = new int[instance.M];

        for (Student s1 : instance.cheaters) {
            for (Student s2 : instance.groups.get(s1.groupId).students) {
                if (s1.id == s2.id) continue;

                Seat seat1 = seating.get(s1.id);
                Seat seat2 = seating.get(s2.id);

                if (seat1.roomId == seat2.roomId &&
                        Math.abs(seat1.row - seat2.row) <= 1 &&
                        Math.abs(seat1.col - seat2.col) <= 1) {
                    penalties[seat1.roomId]++;
                }
            }
        }

        return penalties;
    }

    /**
     * Formats doubles without unnecessary trailing zeroes.
     */
    private String formatDouble(double value) {
        if (Math.abs(value) < 1e-9) value = 0.0;

        return String.format(Locale.US, "%.6f", value)
                .replaceAll("0+$", "")
                .replaceAll("\\.$", "");
    }

    /**
     * Computes the normalized objective value.
     */
    public double getCost() {
        double cheatTerm = 0.0;

        if (!instance.cheaters.isEmpty()) {
            cheatTerm = (instance.cCheat / (double) instance.cheaters.size()) * cheaterIsolation();
        }

        return cheatTerm + (1.0 / (double) instance.groups.size()) * invigilatorCost();
    }

    /**
     * Writes a detailed cost breakdown to the statistics folder.
     * The file is written to statistics/<filename>.
     *
     */
    public void stats(String filename) {
        File file = new File("statistics/" + filename);

        int totalCheatPenalty = cheaterIsolation();
        int[] roomCheatPenalty = cheatPenaltyByRoom();

        double cheatingTerm = 0.0;
        if (!instance.cheaters.isEmpty()) {
            cheatingTerm = (instance.cCheat / (double) instance.cheaters.size()) * totalCheatPenalty;
        }

        double splittingCost = rawGroupSplittingCost();
        double diameterCost = rawDiameterCost();
        double invigilatorCost = splittingCost + diameterCost;
        double invigilatorTerm = 0.0;
        if (!instance.groups.isEmpty()) {
            invigilatorTerm = invigilatorCost / (double) instance.groups.size();
        }

        double totalCost = cheatingTerm + invigilatorTerm;

        try {
            PrintStream writer = new PrintStream(file);

            writer.println("Cheater Isolation Statistics");
            writer.println("----------------------------");
            writer.println("Total cheatPenalty = " + totalCheatPenalty);
            writer.println("Number of cheaters |Q| = " + instance.cheaters.size());
            writer.println("c_cheat = " + formatDouble(instance.cCheat));
            writer.println("Normalized cheating term = " + formatDouble(cheatingTerm));
            writer.println();

            writer.println("Cheat penalty by room:");
            for (int roomId = 0; roomId < instance.M; roomId++) {
                writer.println("Room " + roomId + " cheatPenalty = " + roomCheatPenalty[roomId]);
            }
            writer.println();

            writer.println("Invigilator Statistics");
            writer.println("----------------------");
            writer.println("Raw group splitting cost = " + formatDouble(splittingCost));
            writer.println("Raw diameter cost = " + formatDouble(diameterCost));
            writer.println("Raw invigilator cost = " + formatDouble(invigilatorCost));
            writer.println("Number of groups G = " + instance.groups.size());
            writer.println("Normalized invigilator term = " + formatDouble(invigilatorTerm));
            writer.println();

            writer.println("Combined Objective");
            writer.println("------------------");
            writer.println("Cheating term = " + formatDouble(cheatingTerm));
            writer.println("Invigilator term = " + formatDouble(invigilatorTerm));
            writer.println("Total cost F = " + formatDouble(totalCost));

            writer.close();

        } catch (IOException e) {
            System.out.println("Error: could not write statistics file");
            e.printStackTrace();
        }
    }

    /**
     * Writes one line per student: room row col.
     * The file is written to output/<filename>.
     *
     */
    public void output(String filename) {
        File file = new File(filename);

        try {
            PrintStream writer = new PrintStream(file);

            for (Seat seat : seating) {
                writer.println(seat.roomId + " " + seat.row + " " + seat.col);
            }

            writer.close();

        } catch (IOException e) {
            System.out.println("Error: file not found");
            e.printStackTrace();
        }
    }

    /**
     * Returns a color for a group.
     */
    private String colorFromGroup(int groupId) {
        String[] palette = {
                "#FFADAD",
                "#FFD6A5",
                "#FDFFB6",
                "#CAFFBF",
                "#9BF6FF",
                "#A0C4FF",
                "#BDB2FF",
                "#FFC6FF",
                "#B9FBC0",
                "#F1C0E8",
                "#CFBAF0",
                "#A3C4F3",
                "#90DBF4",
                "#98F5E1",
                "#FDE4CF",
                "#E4C1F9",
                "#D0F4DE",
                "#FCF6BD",
                "#FFCFD2",
                "#CDE7BE",
                "#FBC4AB",
                "#BDE0FE",
                "#CDB4DB",
                "#FFFFB5",
                "#D8F3DC"
        };

        if (groupId >= 0 && groupId < palette.length) {
            return palette[groupId];
        }

        // Fallback color for additional groups.
        float hue = (float) ((groupId * 0.618033988749895) % 1.0);
        float saturation = 0.42f;
        float brightness = 1.0f;

        int rgb = java.awt.Color.HSBtoRGB(hue, saturation, brightness);
        return String.format("#%06X", rgb & 0xFFFFFF);
    }

    /**
     * Writes an SVG visualization of the seating plan.
     * <p>
     * The file is written to visualizations/<filename>.
     */
    public void visualize(String filename) {
        final int cell = 64;
        final int pad = 32;
        final int titleH = 44;
        final int roomGap = 42;
        final int roomInnerPad = 18;
        final int bottomPad = 60;

        final String normalBorder = "#777777";
        final String emptyFill = "#fafafa";
        final String emptyBorder = "#cfcfcf";

        final int normalBorderWidth = 1;
        final int emptyBorderWidth = 1;

        int width = 420;
        int height = pad + 44 + roomGap + bottomPad;

        // Size the SVG to fit all rooms.
        for (Room room : instance.rooms) {
            int roomWidth = room.getCols() * cell + roomInnerPad * 2;
            int roomHeight = titleH + room.getRows() * cell + roomInnerPad * 2;

            width = Math.max(width, pad * 2 + roomWidth);
            height += roomHeight + roomGap;
        }

        File file = new File("visualizations/" + filename);

        try {
            PrintStream writer = new PrintStream(file);

            writer.println("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" + width + "\" height=\"" + height + "\">");

            writer.println("<style>");
            writer.println("text { font-family: Arial, sans-serif; fill: #000000; }");
            writer.println(".main-title { font-size: 24px; font-weight: 700; }");
            writer.println(".room-title { font-size: 20px; font-weight: 700; }");
            writer.println(".seat-student { font-size: 13px; font-weight: 700; }");
            writer.println(".seat-info { font-size: 12px; }");
            writer.println(".cheater-label { font-size: 11px; font-weight: 700; fill: #000000; }");
            writer.println(".room-card { fill: #ffffff; stroke: #dddddd; stroke-width: 1; }");
            writer.println("</style>");

            writer.println("<rect width=\"100%\" height=\"100%\" fill=\"#f7f8fa\"/>");

            int y = pad;

            writer.println("<text x=\"" + pad + "\" y=\"" + y + "\" class=\"main-title\">Exam seating visualization</text>");
            y += 44 + roomGap;

            for (Room room : instance.rooms) {
                int roomCardX = pad;
                int roomCardY = y;
                int roomCardW = room.getCols() * cell + roomInnerPad * 2;
                int roomCardH = titleH + room.getRows() * cell + roomInnerPad * 2;

                writer.println(
                        "<rect x=\"" + roomCardX +
                                "\" y=\"" + roomCardY +
                                "\" width=\"" + roomCardW +
                                "\" height=\"" + roomCardH +
                                "\" rx=\"12\" ry=\"12\" class=\"room-card\"/>"
                );

                writer.println(
                        "<text x=\"" + (roomCardX + roomInnerPad) +
                                "\" y=\"" + (roomCardY + 30) +
                                "\" class=\"room-title\">Room " + room.getId() +
                                " (" + room.getRows() + "x" + room.getCols() + ")</text>"
                );

                int gridX = roomCardX + roomInnerPad;
                int gridY = roomCardY + titleH + roomInnerPad;

                // layout[row][col] stores the student ID, or -1 if empty.
                int[][] layout = new int[room.getRows()][room.getCols()];

                for (int row = 0; row < room.getRows(); row++) {
                    Arrays.fill(layout[row], -1);
                }

                // Convert seating to a room grid.
                for (int studentId = 0; studentId < seating.size(); studentId++) {
                    Seat seat = seating.get(studentId);

                    if (seat.roomId == room.getId()
                            && seat.row >= 0 && seat.row < room.getRows()
                            && seat.col >= 0 && seat.col < room.getCols()) {
                        layout[seat.row][seat.col] = studentId;
                    }
                }

                for (int row = 0; row < room.getRows(); row++) {
                    for (int col = 0; col < room.getCols(); col++) {
                        int x = gridX + col * cell;
                        int seatY = gridY + row * cell;
                        int studentId = layout[row][col];

                        if (studentId == -1) {
                            writer.println(
                                    "<rect x=\"" + x +
                                            "\" y=\"" + seatY +
                                            "\" width=\"" + cell +
                                            "\" height=\"" + cell +
                                            "\" fill=\"" + emptyFill +
                                            "\" stroke=\"" + emptyBorder +
                                            "\" stroke-width=\"" + emptyBorderWidth +
                                            "\"/>"
                            );
                        } else {
                            Student student = instance.students.get(studentId);
                            String groupFill = colorFromGroup(student.groupId);

                            writer.println(
                                    "<rect x=\"" + x +
                                            "\" y=\"" + seatY +
                                            "\" width=\"" + cell +
                                            "\" height=\"" + cell +
                                            "\" fill=\"" + groupFill +
                                            "\" stroke=\"" + normalBorder +
                                            "\" stroke-width=\"" + normalBorderWidth +
                                            "\"/>"
                            );

                            writer.println(
                                    "<text x=\"" + (x + cell / 2) +
                                            "\" y=\"" + (seatY + 25) +
                                            "\" text-anchor=\"middle\" class=\"seat-student\">S" +
                                            student.id + "</text>"
                            );

                            writer.println(
                                    "<text x=\"" + (x + cell / 2) +
                                            "\" y=\"" + (seatY + 44) +
                                            "\" text-anchor=\"middle\" class=\"seat-info\">G" +
                                            student.groupId + "</text>"
                            );

                            boolean isCheater = instance.cheaters.contains(student);

                            if (isCheater) {
                                writer.println(
                                        "<rect x=\"" + (x + 3) +
                                                "\" y=\"" + (seatY + 3) +
                                                "\" width=\"" + (cell - 6) +
                                                "\" height=\"" + (cell - 6) +
                                                "\" fill=\"none\" stroke=\"#000000\" stroke-width=\"6\"/>"
                                );

                                writer.println(
                                        "<rect x=\"" + (x + 8) +
                                                "\" y=\"" + (seatY + 8) +
                                                "\" width=\"" + (cell - 16) +
                                                "\" height=\"" + (cell - 16) +
                                                "\" fill=\"none\" stroke=\"#ffffff\" stroke-width=\"2\"/>"
                                );

                                writer.println(
                                        "<circle cx=\"" + (x + 14) +
                                                "\" cy=\"" + (seatY + 14) +
                                                "\" r=\"10\" fill=\"#ffffff\" stroke=\"#000000\" stroke-width=\"2\"/>"
                                );

                                writer.println(
                                        "<text x=\"" + (x + 14) +
                                                "\" y=\"" + (seatY + 18) +
                                                "\" text-anchor=\"middle\" class=\"cheater-label\">C</text>"
                                );
                            }
                        }
                    }
                }

                y += roomCardH + roomGap;
            }

            writer.println("</svg>");
            writer.close();

        } catch (IOException e) {
            System.out.println("Error: could not write visualization file");
            e.printStackTrace();
        }
    }
}