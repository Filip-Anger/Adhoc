from pathlib import Path
import os
import sys

from src.ExamInstance import ExamInstance
from src.ExamSolution import ExamSolution


def main():
    # Reads data/<dataset>.txt.
    dataset = "large"
    if len(sys.argv) >= 2:
        dataset = sys.argv[1]

    base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)

    input_file = f"data/{dataset}.txt"
    output_file = f"output/{dataset}.out"
    visualization_file = f"{dataset}.svg"
    statistics_file = f"{dataset}.stats"

    # Load the instance and create an initial random solution.
    instance = ExamInstance(input_file)
    solution = ExamSolution(instance, random_solution=True)

    from src.Seat import Seat

    # Separate students into cheaters and non-cheaters.
    # Group cheaters into 4 pattern buckets using (group_id % 4) + 1.
    cheaters_by_pattern = {1: [], 2: [], 3: [], 4: []}
    non_cheaters_by_group = [[] for _ in range(instance.G)]

    for student in instance.students:
        if student.cheater:
            p = (student.group_id % 4) + 1
            cheaters_by_pattern[p].append(student)
        else:
            non_cheaters_by_group[student.group_id].append(student)

    # Pattern function for cheater placement
    def get_pattern_group(row, col):
        if row % 2 == 0:
            return 1 if col % 2 == 0 else 2
        else:
            return 3 if col % 2 == 0 else 4

    # Seat cheaters in the first rooms using the pattern.
    last_cheater_room = -1
    for r_idx, room in enumerate(instance.rooms):
        for row in range(room.getRows()):
            for col in range(room.getCols()):
                p = get_pattern_group(row, col)
                if len(cheaters_by_pattern[p]) > 0:
                    student = cheaters_by_pattern[p].pop(0)
                    solution.seatStudent(student, Seat(room.getId(), row, col))

        # Check if all cheaters are seated
        if all(len(cheaters_by_pattern[p]) == 0 for p in [1, 2, 3, 4]):
            last_cheater_room = r_idx
            break

    if last_cheater_room == -1:
        raise ValueError("Not enough room capacity or incorrect pattern distribution to seat all cheaters.")

    import math

    # Sort non-cheater groups by size descending
    non_cheaters_groups = []
    for g in range(instance.G):
        non_cheaters_groups.append({
            "group_id": g,
            "students": non_cheaters_by_group[g],
            "size": len(non_cheaters_by_group[g])
        })
    non_cheaters_groups.sort(key=lambda x: x["size"], reverse=True)

    # We use the rooms from last_cheater_room + 1 onwards for non-cheaters.
    remaining_rooms = instance.rooms[last_cheater_room + 1:]

    # Track room assignments and remaining capacities
    room_assignments = {r.getId(): [] for r in remaining_rooms}
    room_capacities = {r.getId(): r.getCapacity() for r in remaining_rooms}

    # Threshold for "very small group" or leftovers
    SMALL_THRESHOLD = 15
    leftovers_and_small_groups = []

    for g_info in non_cheaters_groups:
        students_to_assign = list(g_info["students"])

        while len(students_to_assign) > 0:
            if len(students_to_assign) <= SMALL_THRESHOLD:
                leftovers_and_small_groups.append({
                    "group_id": g_info["group_id"],
                    "students": students_to_assign,
                    "size": len(students_to_assign)
                })
                students_to_assign = []
                break

            # Try Best-Fit for large chunk to minimize empty seats
            target_room = None
            min_waste = float("inf")
            for r in remaining_rooms:
                cap = room_capacities[r.getId()]
                if cap >= len(students_to_assign):
                    waste = cap - len(students_to_assign)
                    if waste < min_waste:
                        min_waste = waste
                        target_room = r

            if target_room is not None:
                # Assign the remaining students to this room
                room_assignments[target_room.getId()].append({
                    "group_id": g_info["group_id"],
                    "students": students_to_assign,
                    "size": len(students_to_assign)
                })
                room_capacities[target_room.getId()] -= len(students_to_assign)
                students_to_assign = []
            else:
                # The remaining students do not fit in any single room, so we must split.
                # Find the room with the largest remaining capacity > 0
                largest_room = max(remaining_rooms, key=lambda r: room_capacities[r.getId()])
                space = room_capacities[largest_room.getId()]
                if space == 0:
                    raise ValueError("No capacity left in any room for non-cheaters!")

                chunk = students_to_assign[:space]
                room_assignments[largest_room.getId()].append({
                    "group_id": g_info["group_id"],
                    "students": chunk,
                    "size": len(chunk)
                })
                room_capacities[largest_room.getId()] -= len(chunk)
                students_to_assign = students_to_assign[space:]

    # Sort leftovers and small groups by size descending before placing
    leftovers_and_small_groups.sort(key=lambda x: x["size"], reverse=True)

    # Assign leftovers and small groups using optimal squaring
    for item in leftovers_and_small_groups:
        K = item["size"]
        S = math.ceil(math.sqrt(K))

        best_room = None
        min_dist = float("inf")
        best_waste = float("inf")

        for r in remaining_rooms:
            cap = room_capacities[r.getId()]
            if cap >= K:
                # Find distance to closest wall
                dist = min(abs(r.getRows() - S), abs(r.getCols() - S))
                waste = cap - K
                if dist < min_dist:
                    min_dist = dist
                    best_room = r
                    best_waste = waste
                elif dist == min_dist:
                    # Tie-breaker: minimize waste
                    if waste < best_waste:
                        best_room = r
                        best_waste = waste

        if best_room is None:
            raise ValueError("Not enough capacity in remaining rooms for small groups/leftovers.")

        room_assignments[best_room.getId()].append(item)
        room_capacities[best_room.getId()] -= K

    # Seat the students room by room based on assignments
    for r in remaining_rooms:
        room_id = r.getId()
        R = r.getRows()
        C = r.getCols()
        groups_in_room = room_assignments[room_id]
        if not groups_in_room:
            continue

        all_room_seats = [Seat(room_id, row, col) for row in range(R) for col in range(C)]

        # First group in the room gets block shape if the room starts empty
        first_group = groups_in_room[0]
        K = first_group["size"]

        W_rect = C
        H_rect = (K + C - 1) // C
        b_rect = max(H_rect, W_rect)
        a_rect = min(H_rect, W_rect)

        if H_rect <= R and b_rect <= 2 * a_rect:
            H, W = H_rect, W_rect
        else:
            S = math.ceil(math.sqrt(K))
            H = min(S, R)
            W = min(S, C)
            if H * W < K:
                if H < S:
                    W = (K + H - 1) // H
                elif W < S:
                    H = (K + W - 1) // W

        first_group_seats = [Seat(room_id, row, col) for row in range(H) for col in range(W)][:K]
        for student, seat in zip(first_group["students"], first_group_seats):
            solution.seatStudent(student, seat)

        # Remaining seats in the room
        remaining_room_seats = [s for s in all_room_seats if s not in first_group_seats]

        # Place subsequent groups in the remaining seats
        seat_idx = 0
        for other_group in groups_in_room[1:]:
            for student in other_group["students"]:
                solution.seatStudent(student, remaining_room_seats[seat_idx])
                seat_idx += 1

    # checkValid checks feasibility, not optimality.
    if not solution.checkValid():
        print("Solution not valid!")

    print(f"Cost = {solution.getCost()}")

    # Write solution, visualization, and statistics files.
    Path("output").mkdir(exist_ok=True)
    Path("visualizations").mkdir(exist_ok=True)
    Path("statistics").mkdir(exist_ok=True)

    solution.output(output_file)
    solution.visualize(visualization_file)
    solution.stats(statistics_file)

    print(f"Output written to {output_file}")
    print(f"Visualization written to visualizations/{visualization_file}")
    print(f"Statistics written to statistics/{statistics_file}")


if __name__ == "__main__":
    main()
