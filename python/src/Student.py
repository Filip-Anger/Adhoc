class Student:
    """Represents one student in the exam distribution problem."""

    def __init__(self, student_id: int, group_id: int):
        self.id = student_id
        self.group_id = group_id
        self.cheater = False

    def __repr__(self) -> str:
        return f"Student(id={self.id}, group_id={self.group_id}, cheater={self.cheater})"
