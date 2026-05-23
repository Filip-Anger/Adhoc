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

    # Count cheaters in each group
    cheater_counts_by_group = {}
    for student in instance.students:
        if student.cheater:
            g = student.group_id
            cheater_counts_by_group[g] = cheater_counts_by_group.get(g, 0) + 1

    # Sort groups by cheater count descending
    sorted_cheater_groups = sorted(cheater_counts_by_group.keys(), key=lambda g: cheater_counts_by_group[g], reverse=True)

    # Greedily assign each group to the pattern bucket with the smallest count (LPT Scheduling)
    # This balances the pattern buckets, making the safety pattern "more compact" and using fewer rows.
    group_to_pattern = {}
    bucket_sizes = {1: 0, 2: 0, 3: 0, 4: 0}
    for g in sorted_cheater_groups:
        best_bucket = min(bucket_sizes.keys(), key=lambda b: bucket_sizes[b])
        group_to_pattern[g] = best_bucket
        bucket_sizes[best_bucket] += cheater_counts_by_group[g]

    # Separate students into cheaters and non-cheaters, assigning cheaters to balanced pattern buckets.
    cheaters_by_pattern = {1: [], 2: [], 3: [], 4: []}
    non_cheaters_by_group = [[] for _ in range(instance.G)]

    for student in instance.students:
        if student.cheater:
            p = group_to_pattern[student.group_id]
            cheaters_by_pattern[p].append(student)
        else:
            non_cheaters_by_group[student.group_id].append(student)

    # Checkerboard safety pattern index function
    def get_pattern_group(row, col):
        if row % 2 == 0:
            return 1 if col % 2 == 0 else 2
        else:
            return 3 if col % 2 == 0 else 4

    # Sort rooms by capacity descending
    sorted_rooms = sorted(instance.rooms, key=lambda r: r.getCapacity(), reverse=True)

    # Determine cheater row allocations dynamically for each room
    room_cheater_rows = {}
    for room in sorted_rooms:
        H_c = 0
        initial_counts = {p: len(cheaters_by_pattern[p]) for p in [1, 2, 3, 4]}
        
        while H_c < room.getRows():
            if all(initial_counts[p] == 0 for p in [1, 2, 3, 4]):
                break
                
            H_c += 1
            cap = {1: 0, 2: 0, 3: 0, 4: 0}
            for r_offset in range(H_c):
                for col in range(room.getCols()):
                    p = get_pattern_group(r_offset, col)
                    cap[p] += 1
                    
            if all(cap[p] >= initial_counts[p] for p in [1, 2, 3, 4]):
                for p in [1, 2, 3, 4]:
                    initial_counts[p] = 0
                break
                
        room_cheater_rows[room.getId()] = H_c
        
        # Place cheaters in the first H_c rows
        for row in range(H_c):
            for col in range(room.getCols()):
                p = get_pattern_group(row, col)
                if len(cheaters_by_pattern[p]) > 0:
                    student = cheaters_by_pattern[p].pop(0)
                    solution.seatStudent(student, Seat(room.getId(), row, col))

    # Check if any cheaters are left
    if any(len(cheaters_by_pattern[p]) > 0 for p in [1, 2, 3, 4]):
        raise ValueError("Not enough room capacity for cheaters.")

    import math

    # Non-cheaters pre-assignment
    non_cheaters_groups = []
    for g in range(instance.G):
        non_cheaters_groups.append({
            "group_id": g,
            "students": non_cheaters_by_group[g],
            "size": len(non_cheaters_by_group[g])
        })
    non_cheaters_groups.sort(key=lambda x: x["size"], reverse=True)

    # Determine if we should use buffer rows between cheaters and non-cheaters.
    # If using buffer rows exceeds the total remaining capacity, we disable them to keep the solution valid.
    total_non_cheaters = sum(g["size"] for g in non_cheaters_groups)
    total_cap_with_buffer = 0
    for r in sorted_rooms:
        H_c = room_cheater_rows[r.getId()]
        start_row = H_c + 1 if H_c > 0 else 0
        avail_rows = max(0, r.getRows() - start_row)
        total_cap_with_buffer += avail_rows * r.getCols()
        
    use_buffer = (total_cap_with_buffer >= total_non_cheaters)

    room_assignments = {r.getId(): [] for r in sorted_rooms}
    room_capacities = {}
    for r in sorted_rooms:
        H_c = room_cheater_rows[r.getId()]
        start_row = H_c + 1 if (H_c > 0 and use_buffer) else H_c
        avail_rows = max(0, r.getRows() - start_row)
        room_capacities[r.getId()] = avail_rows * r.getCols()

    # Greedy Best-Fit assignment of non-cheaters
    for g_info in non_cheaters_groups:
        students_to_assign = list(g_info["students"])
        
        while len(students_to_assign) > 0:
            target_room = None
            min_waste = float("inf")
            for r in sorted_rooms:
                cap = room_capacities[r.getId()]
                if cap >= len(students_to_assign):
                    waste = cap - len(students_to_assign)
                    if waste < min_waste:
                        min_waste = waste
                        target_room = r
                        
            if target_room is not None:
                room_assignments[target_room.getId()].append({
                    "group_id": g_info["group_id"],
                    "students": students_to_assign,
                    "size": len(students_to_assign)
                })
                room_capacities[target_room.getId()] -= len(students_to_assign)
                students_to_assign = []
            else:
                largest_room = max(sorted_rooms, key=lambda r: room_capacities[r.getId()])
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

    # Helper function to pack a strip of height H
    def pack_strip(groups, H, C):
        selected = []
        width_sum = 0
        for g in groups:
            w_min = (g["size"] + H - 1) // H
            if max(H, w_min) > 2 * min(H, w_min):
                continue
            if width_sum + w_min <= C:
                selected.append(g)
                width_sum += w_min
            else:
                break
                
        if not selected:
            return None, None
            
        extra = C - width_sum
        widths = [(g["size"] + H - 1) // H for g in selected]
        
        for i in range(len(selected)):
            max_w = 2 * H
            add = min(extra, max_w - widths[i])
            widths[i] += add
            extra -= add
            if extra == 0:
                break
                
        if extra > 0:
            return None, None
            
        return selected, widths

    overflow_students = []

    # Seat the non-cheaters room by room using strip packing
    for r in sorted_rooms:
        room_id = r.getId()
        R = r.getRows()
        C = r.getCols()
        H_c = room_cheater_rows[room_id]
        start_row = H_c + 1 if (H_c > 0 and use_buffer) else H_c
        
        groups_in_room = room_assignments[room_id]
        if not groups_in_room:
            continue
            
        groups_in_room.sort(key=lambda x: x["size"], reverse=True)
        
        remaining_groups = list(groups_in_room)
        current_row = start_row
        
        while remaining_groups and current_row < R:
            g_largest = remaining_groups[0]
            S = math.ceil(math.sqrt(g_largest["size"]))
            H = min(S, R - current_row)
            if H == 0:
                break
                
            selected_groups, widths = pack_strip(remaining_groups, H, C)
            
            if selected_groups is not None:
                col_start = 0
                for g, w in zip(selected_groups, widths):
                    block_seats = []
                    for r_offset in range(H):
                        for c_offset in range(w):
                            if len(block_seats) < g["size"]:
                                block_seats.append(Seat(room_id, current_row + r_offset, col_start + c_offset))
                    for student, seat in zip(g["students"], block_seats):
                        solution.seatStudent(student, seat)
                    col_start += w
                    remaining_groups.remove(g)
                current_row += H
            else:
                # Fallback to sequential placement in remaining space of this room
                avail_seats = [Seat(room_id, row, col) for row in range(current_row, R) for col in range(C)]
                for g in list(remaining_groups):
                    for student in g["students"]:
                        if avail_seats:
                            solution.seatStudent(student, avail_seats.pop(0))
                        else:
                            overflow_students.append(student)
                    remaining_groups.remove(g)
                break
                
        # Place any remaining groups that could not fit in strips
        if remaining_groups:
            taken_seats_in_room = set()
            for s_id in range(instance.N):
                seat = solution.seating[s_id]
                if seat.room_id == room_id:
                    taken_seats_in_room.add((seat.row, seat.col))
            avail_seats = []
            for row in range(start_row, R):
                for col in range(C):
                    if (row, col) not in taken_seats_in_room:
                        avail_seats.append(Seat(room_id, row, col))
            for g in remaining_groups:
                for student in g["students"]:
                    if avail_seats:
                        solution.seatStudent(student, avail_seats.pop(0))
                    else:
                        overflow_students.append(student)

    # Place overflow students in any remaining empty seats across all rooms
    if overflow_students:
        taken_seats_global = set()
        for s_id in range(instance.N):
            seat = solution.seating[s_id]
            if seat.room_id != -1:
                taken_seats_global.add((seat.room_id, seat.row, seat.col))
                
        avail_seats_global = []
        for r in sorted_rooms:
            H_c = room_cheater_rows[r.getId()]
            start_row = H_c + 1 if (H_c > 0 and use_buffer) else H_c
            for row in range(start_row, r.getRows()):
                for col in range(r.getCols()):
                    if (r.getId(), row, col) not in taken_seats_global:
                        avail_seats_global.append(Seat(r.getId(), row, col))
                        
        for student in overflow_students:
            solution.seatStudent(student, avail_seats_global.pop(0))

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
