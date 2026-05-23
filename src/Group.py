class Group:
    """Represents one exam group."""

    def __init__(self, group_id: int):
        self.id = group_id
        self.students = []

    def addStudent(self, student):
        if student not in self.students:
            self.students.append(student)

    def containsStudent(self, student) -> bool:
        return student in self.students

    def getGroupSize(self) -> int:
        return len(self.students)

    def __repr__(self) -> str:
        return f"Group(id={self.id}, size={len(self.students)})"
