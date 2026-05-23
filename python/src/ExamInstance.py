from .Student import Student
from .Room import Room
from .Group import Group


class ExamInstance:
    """Stores one input instance: students, rooms, groups, cheaters, and coefficients."""

    def __init__(self, filename: str):
        self.N = 0  # number of students
        self.M = 0  # number of rooms
        self.G = 0  # number of groups
        self.C = 0  # number of cheaters

        # coefficients for cost function
        self.cCheat = 1.0
        self.cSplit = 1.0
        self.cDiam = 1.0

        self.students = []
        self.rooms = []
        self.groups = []
        self.cheaters = []

        self.read(filename)

    def read(self, filename: str):
        """Reads the task input format from a file."""
        with open(filename, "r", encoding="utf-8") as file:
            tokens = file.read().split()

        idx = 0

        self.N = int(tokens[idx])
        idx += 1
        self.M = int(tokens[idx])
        idx += 1
        self.G = int(tokens[idx])
        idx += 1

        self.cCheat = float(tokens[idx])
        idx += 1
        self.cSplit = float(tokens[idx])
        idx += 1
        self.cDiam = float(tokens[idx])
        idx += 1

        self.groups = [Group(group_id) for group_id in range(self.G)]

        self.students = []
        for student_id in range(self.N):
            group_id = int(tokens[idx])
            idx += 1

            student = Student(student_id, group_id)
            self.students.append(student)

            if 0 <= group_id < self.G:
                self.groups[group_id].addStudent(student)
            else:
                raise ValueError(f"Invalid group id {group_id} for student {student_id}")

        self.rooms = []
        for room_id in range(self.M):
            rows = int(tokens[idx])
            idx += 1
            cols = int(tokens[idx])
            idx += 1
            self.rooms.append(Room(room_id, rows, cols))

        self.C = int(tokens[idx])
        idx += 1

        self.cheaters = []
        for _ in range(self.C):
            student_id = int(tokens[idx])
            idx += 1

            if student_id < 0 or student_id >= self.N:
                raise ValueError(f"Invalid cheater student id: {student_id}")

            student = self.students[student_id]
            student.cheater = True
            self.cheaters.append(student)

    def getTotalCapacity(self) -> int:
        return sum(room.getCapacity() for room in self.rooms)

    def __repr__(self) -> str:
        return (
            f"ExamInstance(N={self.N}, M={self.M}, G={self.G}, C={self.C}, "
            f"cCheat={self.cCheat}, cSplit={self.cSplit}, cDiam={self.cDiam})"
        )
