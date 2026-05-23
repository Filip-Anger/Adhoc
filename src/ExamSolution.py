import math
import random
from pathlib import Path

from .Seat import Seat


class ExamSolution:
    """Represents one seating assignment. seating[i] is student i's seat."""

    def __init__(self, instance, random_solution: bool = False):
        self.instance = instance

        # seating[student_id] stores the room, row, and column assigned to that student.
        self.seating = [Seat(-1, -1, -1) for _ in range(instance.N)]

        if random_solution:
            seats = []

            # Collect all available seats.
            for room in instance.rooms:
                for row in range(room.getRows()):
                    for col in range(room.getCols()):
                        seats.append(Seat(room.getId(), row, col))

            if len(seats) < instance.N:
                raise ValueError("Not enough seats for all students.")

            random.shuffle(seats)

            # Assign seats to students 0..N-1.
            for student_id in range(instance.N):
                self.seating[student_id] = seats[student_id]

    def copy(self):
        """Returns an independent copy of this solution."""
        sol = ExamSolution(self.instance)
        sol.seating = [seat.copy() for seat in self.seating]
        return sol

    def seatStudent(self, student, seat: Seat):
        """Assigns one student to one seat."""
        self.seating[student.id] = seat

    def isValidSeatPosition(self, seat: Seat) -> bool:
        """Checks whether a seat is inside its room bounds."""
        if seat.getRoomId() < 0 or seat.getRoomId() >= self.instance.M:
            return False

        room = self.instance.rooms[seat.getRoomId()]

        return (
            0 <= seat.getRow() < room.getRows()
            and 0 <= seat.getCol() < room.getCols()
        )

    def checkValid(self) -> bool:
        """Checks that all students have valid, unique seats."""
        taken = set()

        for student_id in range(self.instance.N):
            seat = self.seating[student_id]

            if not self.isValidSeatPosition(seat):
                return False

            if seat in taken:
                return False

            taken.add(seat)

        return True

    def cheaterIsolation(self) -> int:
        """Counts same-group students adjacent to listed cheaters."""
        cheat_penalty = 0

        for cheater in self.instance.cheaters:
            cheater_seat = self.seating[cheater.id]
            group = self.instance.groups[cheater.group_id]

            for other in group.students:
                if cheater.id == other.id:
                    continue

                other_seat = self.seating[other.id]

                if (
                    cheater_seat.room_id == other_seat.room_id
                    and abs(cheater_seat.row - other_seat.row) <= 1
                    and abs(cheater_seat.col - other_seat.col) <= 1
                ):
                    cheat_penalty += 1

        return cheat_penalty

    def _seatsByRoom(self, group):
        """Groups the seats of one exam group by room."""
        distribution = {}

        for student in group.students:
            seat = self.seating[student.id]

            if seat.room_id not in distribution:
                distribution[seat.room_id] = []

            distribution[seat.room_id].append(seat)

        return distribution

    def _rawGroupSplittingCost(self) -> float:
        """Computes the group splitting part before normalization."""
        splitting_cost = 0.0

        for group in self.instance.groups:
            distribution = self._seatsByRoom(group)
            splitting_cost += len(distribution) * self.instance.cSplit

        return splitting_cost

    def _rawDiameterCost(self) -> float:
        """Computes the diameter part before normalization."""
        diameter_cost = 0.0

        for group in self.instance.groups:
            distribution = self._seatsByRoom(group)

            for seats in distribution.values():
                diam_squared = 0.0

                # Find this group's diameter in the room.
                for i in range(len(seats)):
                    seat1 = seats[i]

                    for j in range(i + 1, len(seats)):
                        seat2 = seats[j]

                        dist_squared = (
                            (seat1.col - seat2.col) ** 2
                            + (seat1.row - seat2.row) ** 2
                        )

                        diam_squared = max(diam_squared, dist_squared)

                diameter_cost += math.sqrt(diam_squared) * self.instance.cDiam

        return diameter_cost

    def invigilatorCost(self) -> float:
        """Computes group splitting and diameter costs."""
        return self._rawGroupSplittingCost() + self._rawDiameterCost()

    def _cheatPenaltyByRoom(self):
        """Computes the number of cheating penalties per room."""
        penalties = [0 for _ in range(self.instance.M)]

        for cheater in self.instance.cheaters:
            cheater_seat = self.seating[cheater.id]
            group = self.instance.groups[cheater.group_id]

            for other in group.students:
                if cheater.id == other.id:
                    continue

                other_seat = self.seating[other.id]

                if (
                    cheater_seat.room_id == other_seat.room_id
                    and abs(cheater_seat.row - other_seat.row) <= 1
                    and abs(cheater_seat.col - other_seat.col) <= 1
                ):
                    penalties[cheater_seat.room_id] += 1

        return penalties

    def _formatDouble(self, value: float) -> str:
        """Formats doubles without unnecessary trailing zeroes."""
        if abs(value) < 1e-9:
            value = 0.0

        result = f"{value:.6f}".rstrip("0").rstrip(".")
        return result if result and result != "-0" else "0"

    def getCost(self) -> float:
        """Computes the normalized objective value."""
        cheat_term = 0.0

        if len(self.instance.cheaters) > 0:
            cheat_term = (
                self.instance.cCheat / len(self.instance.cheaters)
            ) * self.cheaterIsolation()

        invig_term = 0.0

        if len(self.instance.groups) > 0:
            invig_term = (1.0 / len(self.instance.groups)) * self.invigilatorCost()

        return cheat_term + invig_term

    def stats(self, filename: str):
        """Writes a detailed cost breakdown to statistics/<filename>."""
        file_path = Path("statistics") / filename

        total_cheat_penalty = self.cheaterIsolation()
        room_cheat_penalty = self._cheatPenaltyByRoom()

        cheating_term = 0.0
        if len(self.instance.cheaters) > 0:
            cheating_term = (
                self.instance.cCheat / len(self.instance.cheaters)
            ) * total_cheat_penalty

        splitting_cost = self._rawGroupSplittingCost()
        diameter_cost = self._rawDiameterCost()
        invigilator_cost = splitting_cost + diameter_cost

        invigilator_term = 0.0
        if len(self.instance.groups) > 0:
            invigilator_term = invigilator_cost / len(self.instance.groups)

        total_cost = cheating_term + invigilator_term

        with open(file_path, "w", encoding="utf-8") as writer:
            writer.write("Cheater Isolation Statistics\n")
            writer.write("----------------------------\n")
            writer.write(f"Total cheatPenalty = {total_cheat_penalty}\n")
            writer.write(f"Number of cheaters |Q| = {len(self.instance.cheaters)}\n")
            writer.write(f"c_cheat = {self._formatDouble(self.instance.cCheat)}\n")
            writer.write(f"Normalized cheating term = {self._formatDouble(cheating_term)}\n\n")

            writer.write("Cheat penalty by room:\n")
            for room_id in range(self.instance.M):
                writer.write(
                    f"Room {room_id} cheatPenalty = {room_cheat_penalty[room_id]}\n"
                )
            writer.write("\n")

            writer.write("Invigilator Statistics\n")
            writer.write("----------------------\n")
            writer.write(f"Raw group splitting cost = {self._formatDouble(splitting_cost)}\n")
            writer.write(f"Raw diameter cost = {self._formatDouble(diameter_cost)}\n")
            writer.write(f"Raw invigilator cost = {self._formatDouble(invigilator_cost)}\n")
            writer.write(f"Number of groups G = {len(self.instance.groups)}\n")
            writer.write(
                f"Normalized invigilator term = {self._formatDouble(invigilator_term)}\n\n"
            )

            writer.write("Combined Objective\n")
            writer.write("------------------\n")
            writer.write(f"Cheating term = {self._formatDouble(cheating_term)}\n")
            writer.write(f"Invigilator term = {self._formatDouble(invigilator_term)}\n")
            writer.write(f"Total cost F = {self._formatDouble(total_cost)}\n")

    def output(self, filename: str):
        """Writes one line per student: room row col."""
        with open(filename, "w", encoding="utf-8") as file:
            for seat in self.seating:
                file.write(f"{seat.room_id} {seat.row} {seat.col}\n")

    def _colorFromGroup(self, group_id: int) -> str:
        """Returns a color for a group."""
        palette = [
            "#FFADAD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF",
            "#A0C4FF", "#BDB2FF", "#FFC6FF", "#B9FBC0", "#F1C0E8",
            "#CFBAF0", "#A3C4F3", "#90DBF4", "#98F5E1", "#FDE4CF",
            "#E4C1F9", "#D0F4DE", "#FCF6BD", "#FFCFD2", "#CDE7BE",
            "#FBC4AB", "#BDE0FE", "#CDB4DB", "#FFFFB5", "#D8F3DC",
        ]

        if 0 <= group_id < len(palette):
            return palette[group_id]

        hue = (group_id * 0.618033988749895) % 1.0
        saturation = 0.42
        brightness = 1.0

        return self._hsvToHex(hue, saturation, brightness)

    def _hsvToHex(self, h: float, s: float, v: float) -> str:
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        i %= 6

        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

        return "#{:02X}{:02X}{:02X}".format(
            round(r * 255), round(g * 255), round(b * 255)
        )

    def visualize(self, filename: str):
        """Writes an SVG visualization to visualizations/<filename>."""
        filename_path = Path(filename)

        if filename_path.parent == Path("."):
            file_path = Path("visualizations") / filename_path.name
        else:
            file_path = filename_path

        cell = 64
        pad = 32
        title_h = 44
        room_gap = 42
        room_inner_pad = 18
        bottom_pad = 60

        normal_border = "#777777"
        empty_fill = "#fafafa"
        empty_border = "#cfcfcf"

        width = 420
        height = pad + 44 + room_gap + bottom_pad

        # Size the SVG to fit all rooms.
        for room in self.instance.rooms:
            room_width = room.getCols() * cell + room_inner_pad * 2
            room_height = title_h + room.getRows() * cell + room_inner_pad * 2
            width = max(width, pad * 2 + room_width)
            height += room_height + room_gap

        with open(file_path, "w", encoding="utf-8") as writer:
            writer.write(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">\n'
            )

            writer.write("<style>\n")
            writer.write("text { font-family: Arial, sans-serif; fill: #000000; }\n")
            writer.write(".main-title { font-size: 24px; font-weight: 700; }\n")
            writer.write(".room-title { font-size: 20px; font-weight: 700; }\n")
            writer.write(".seat-student { font-size: 13px; font-weight: 700; }\n")
            writer.write(".seat-info { font-size: 12px; }\n")
            writer.write(".cheater-label { font-size: 11px; font-weight: 700; fill: #000000; }\n")
            writer.write(".room-card { fill: #ffffff; stroke: #dddddd; stroke-width: 1; }\n")
            writer.write("</style>\n")

            writer.write('<rect width="100%" height="100%" fill="#f7f8fa"/>\n')

            y = pad
            writer.write(
                f'<text x="{pad}" y="{y}" class="main-title">Exam seating visualization</text>\n'
            )
            y += 44 + room_gap

            for room in self.instance.rooms:
                room_card_x = pad
                room_card_y = y
                room_card_w = room.getCols() * cell + room_inner_pad * 2
                room_card_h = title_h + room.getRows() * cell + room_inner_pad * 2

                writer.write(
                    f'<rect x="{room_card_x}" y="{room_card_y}" '
                    f'width="{room_card_w}" height="{room_card_h}" '
                    f'rx="12" ry="12" class="room-card"/>\n'
                )

                writer.write(
                    f'<text x="{room_card_x + room_inner_pad}" '
                    f'y="{room_card_y + 30}" class="room-title">'
                    f'Room {room.getId()} ({room.getRows()}x{room.getCols()})</text>\n'
                )

                grid_x = room_card_x + room_inner_pad
                grid_y = room_card_y + title_h + room_inner_pad

                # layout[row][col] stores the student ID, or -1 if empty.
                layout = [[-1 for _ in range(room.getCols())] for _ in range(room.getRows())]

                # Convert seating to a room grid.
                for student_id, seat in enumerate(self.seating):
                    if (
                        seat.room_id == room.getId()
                        and 0 <= seat.row < room.getRows()
                        and 0 <= seat.col < room.getCols()
                    ):
                        layout[seat.row][seat.col] = student_id

                for row in range(room.getRows()):
                    for col in range(room.getCols()):
                        x = grid_x + col * cell
                        seat_y = grid_y + row * cell
                        student_id = layout[row][col]

                        if student_id == -1:
                            writer.write(
                                f'<rect x="{x}" y="{seat_y}" width="{cell}" height="{cell}" '
                                f'fill="{empty_fill}" stroke="{empty_border}" stroke-width="1"/>\n'
                            )
                        else:
                            student = self.instance.students[student_id]
                            group_fill = self._colorFromGroup(student.group_id)

                            writer.write(
                                f'<rect x="{x}" y="{seat_y}" width="{cell}" height="{cell}" '
                                f'fill="{group_fill}" stroke="{normal_border}" stroke-width="1"/>\n'
                            )

                            writer.write(
                                f'<text x="{x + cell // 2}" y="{seat_y + 25}" '
                                f'text-anchor="middle" class="seat-student">S{student.id}</text>\n'
                            )

                            writer.write(
                                f'<text x="{x + cell // 2}" y="{seat_y + 44}" '
                                f'text-anchor="middle" class="seat-info">G{student.group_id}</text>\n'
                            )

                            if student.cheater:
                                writer.write(
                                    f'<rect x="{x + 3}" y="{seat_y + 3}" '
                                    f'width="{cell - 6}" height="{cell - 6}" '
                                    f'fill="none" stroke="#000000" stroke-width="6"/>\n'
                                )

                                writer.write(
                                    f'<rect x="{x + 8}" y="{seat_y + 8}" '
                                    f'width="{cell - 16}" height="{cell - 16}" '
                                    f'fill="none" stroke="#ffffff" stroke-width="2"/>\n'
                                )

                                writer.write(
                                    f'<circle cx="{x + 14}" cy="{seat_y + 14}" r="10" '
                                    f'fill="#ffffff" stroke="#000000" stroke-width="2"/>\n'
                                )

                                writer.write(
                                    f'<text x="{x + 14}" y="{seat_y + 18}" '
                                    f'text-anchor="middle" class="cheater-label">C</text>\n'
                                )

                y += room_card_h + room_gap

            writer.write("</svg>\n")
