from pathlib import Path
import os
import sys
import math
import random

from src.ExamInstance import ExamInstance
from src.ExamSolution import ExamSolution
from src.Seat import Seat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_pattern_color(row, col):
    if row % 2 == 0:
        return 1 if col % 2 == 0 else 2
    else:
        return 3 if col % 2 == 0 else 4


# ---------------------------------------------------------------------------
# Sportshall-specific Solver (1 room)
# ---------------------------------------------------------------------------

def solve_sportshall(instance, solution):
    G = instance.G
    room = instance.rooms[0]
    R = room.getRows()
    C = room.getCols()
    
    # Separate students by group
    ch_by_group = [[] for _ in range(G)]
    nc_by_group = [[] for _ in range(G)]
    for s in instance.students:
        if s.cheater:
            ch_by_group[s.group_id].append(s)
        else:
            nc_by_group[s.group_id].append(s)
            
    taken_seats = set()
    group_seats = {g: set() for g in range(G)}
    
    # Place non-cheaters group by group compactly
    sorted_groups = sorted(range(G), key=lambda g: len(nc_by_group[g]), reverse=True)
    for g in sorted_groups:
        students = nc_by_group[g]
        n = len(students)
        if n == 0:
            continue
            
        avail = []
        for r in range(R):
            for c in range(C):
                if (r, c) not in taken_seats:
                    avail.append((r, c))
                    
        best_seats = None
        best_diam = float('inf')
        candidates = list(avail)
        if len(candidates) > 100:
            random.seed(42)
            candidates = random.sample(candidates, 100)
            
        for cr, cc in candidates:
            avail.sort(key=lambda s: (s[0] - cr)**2 + (s[1] - cc)**2)
            selected = avail[:n]
            max_d2 = 0
            for i in range(n):
                r1, c1 = selected[i]
                for j in range(i + 1, n):
                    r2, c2 = selected[j]
                    d2 = (r1 - r2)**2 + (c1 - c2)**2
                    if d2 > max_d2:
                        max_d2 = d2
            diam = math.sqrt(max_d2)
            if diam < best_diam:
                best_diam = diam
                best_seats = selected
                
        for s, (r, c) in zip(students, best_seats):
            solution.seatStudent(s, Seat(0, r, c))
            taken_seats.add((r, c))
            group_seats[g].add((r, c))

    # Place cheaters group by group (border-gap placement)
    sorted_ch_groups = sorted(range(G), key=lambda g: len(ch_by_group[g]), reverse=True)
    for g in sorted_ch_groups:
        cheaters = ch_by_group[g]
        if not cheaters:
            continue
            
        if group_seats[g]:
            cr = sum(r for r, c in group_seats[g]) / len(group_seats[g])
            cc = sum(c for r, c in group_seats[g]) / len(group_seats[g])
        else:
            cr, cc = R / 2, C / 2
            
        for s in cheaters:
            best_seat = None
            best_dist = float('inf')
            for r in range(R):
                for c in range(C):
                    if (r, c) in taken_seats:
                        continue
                    # Check adjacency to group_seats[g]
                    safe = True
                    for gr, gc in group_seats[g]:
                        if abs(r - gr) <= 1 and abs(c - gc) <= 1:
                            safe = False
                            break
                    if not safe:
                        continue
                    dist = (r - cr)**2 + (c - cc)**2
                    if dist < best_dist:
                        best_dist = dist
                        best_seat = (r, c)
            if best_seat is None:
                # Fallback
                for r in range(R):
                    for c in range(C):
                        if (r, c) not in taken_seats:
                            best_seat = (r, c)
                            break
                    if best_seat:
                        break
            if best_seat is None:
                raise ValueError("No empty seats left in the room!")
            r, c = best_seat
            solution.seatStudent(s, Seat(0, r, c))
            taken_seats.add((r, c))
            group_seats[g].add((r, c))


# ---------------------------------------------------------------------------
# Multi-room Solver (optimized hybrid)
# ---------------------------------------------------------------------------

def solve_multi_room(instance, solution):
    G = instance.G
    rooms = list(instance.rooms)
    
    # Separate students by group
    ch_by_group = [[] for _ in range(G)]
    nc_by_group = [[] for _ in range(G)]
    for s in instance.students:
        if s.cheater:
            ch_by_group[s.group_id].append(s)
        else:
            nc_by_group[s.group_id].append(s)
            
    # LPT assignment of groups to pattern buckets based on cheater count
    sorted_cheater_groups = sorted(range(G), key=lambda g: len(ch_by_group[g]), reverse=True)
    group_to_pattern = {}
    bucket_sizes = {1: 0, 2: 0, 3: 0, 4: 0}
    for g in sorted_cheater_groups:
        best_bucket = min(bucket_sizes.keys(), key=lambda b: bucket_sizes[b])
        group_to_pattern[g] = best_bucket
        bucket_sizes[best_bucket] += len(ch_by_group[g])
        
    cheaters_by_pattern = {1: [], 2: [], 3: [], 4: []}
    for s in instance.students:
        if s.cheater:
            p = group_to_pattern[s.group_id]
            cheaters_by_pattern[p].append(s)
            
    # Sort rooms by capacity descending
    sorted_rooms = sorted(rooms, key=lambda r: r.getCapacity(), reverse=True)
    
    # Place cheaters in the first H_c rows of each room
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
                    p = get_pattern_color(r_offset, col)
                    cap[p] += 1
            if all(cap[p] >= initial_counts[p] for p in [1, 2, 3, 4]):
                for p in [1, 2, 3, 4]:
                    initial_counts[p] = 0
                break
                
        room_cheater_rows[room.getId()] = H_c
        for row in range(H_c):
            for col in range(room.getCols()):
                p = get_pattern_color(row, col)
                if len(cheaters_by_pattern[p]) > 0:
                    student = cheaters_by_pattern[p].pop(0)
                    solution.seatStudent(student, Seat(room.getId(), row, col))
                    
    # Determine buffer rows
    total_non_cheaters = sum(len(nc_by_group[g]) for g in range(G))
    total_cap_with_buffer = 0
    for r in sorted_rooms:
        H_c = room_cheater_rows[r.getId()]
        start_row = H_c + 1 if H_c > 0 else 0
        avail_rows = max(0, r.getRows() - start_row)
        total_cap_with_buffer += avail_rows * r.getCols()
        
    use_buffer = (total_cap_with_buffer >= total_non_cheaters)
    
    room_capacities = {}
    room_start_row = {}
    for r in sorted_rooms:
        H_c = room_cheater_rows[r.getId()]
        start_row = H_c + 1 if (H_c > 0 and use_buffer) else H_c
        room_start_row[r.getId()] = start_row
        room_capacities[r.getId()] = max(0, r.getRows() - start_row) * r.getCols()
        
    # Assign non-cheaters to rooms using Best-Fit Decreasing
    non_cheaters_groups = []
    for g in range(G):
        if len(nc_by_group[g]) > 0:
            non_cheaters_groups.append({
                "group_id": g,
                "students": nc_by_group[g],
                "size": len(nc_by_group[g])
            })
    non_cheaters_groups.sort(key=lambda x: x["size"], reverse=True)
    
    room_assignments = {r.getId(): [] for r in sorted_rooms}
    for g_info in non_cheaters_groups:
        students_to_assign = list(g_info["students"])
        while len(students_to_assign) > 0:
            target_room = None
            min_waste = float('inf')
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

    # Place non-cheaters room by room
    for r in sorted_rooms:
        rid = r.getId()
        R = r.getRows()
        C = r.getCols()
        start_row = room_start_row[rid]
        
        glist = room_assignments[rid]
        if not glist:
            continue
            
        glist.sort(key=lambda x: x["size"], reverse=True)
        
        taken_seats = set()
        for row in range(start_row):
            for col in range(C):
                taken_seats.add((row, col))
                
        # Skyline tracking
        skyline = [start_row] * C
        
        for g_info in glist:
            n = g_info["size"]
            students = g_info["students"]
            
            # Try to place in a compact rectangle using skyline
            rect = None
            best_d = float('inf')
            for h in range(1, R - start_row + 1):
                w = math.ceil(n / h)
                if w > C:
                    continue
                for sc in range(C - w + 1):
                    top = max(skyline[sc:sc+w])
                    if top + h > R:
                        continue
                    d = (h - 1)**2 + (w - 1)**2
                    if d < best_d:
                        best_d = d
                        rect = (top, sc, h, w)
                        
            if rect is not None:
                top, left, h, w = rect
                idx = 0
                for r_off in range(h):
                    for c_off in range(w):
                        if idx < n:
                            row, col = top + r_off, left + c_off
                            solution.seatStudent(students[idx], Seat(rid, row, col))
                            taken_seats.add((row, col))
                            idx += 1
                for ci in range(left, left + w):
                    skyline[ci] = max(skyline[ci], top + h)
            else:
                # Fallback: Center-based compact placement using remaining empty seats
                avail = []
                for row in range(start_row, R):
                    for col in range(C):
                        if (row, col) not in taken_seats:
                            avail.append((row, col))
                if len(avail) < n:
                    raise ValueError(f"Not enough seats for group {g_info['group_id']} in room {rid}")
                    
                best_seats = None
                best_diam = float('inf')
                candidates = list(avail)
                if len(candidates) > 100:
                    random.seed(42)
                    candidates = random.sample(candidates, 100)
                for cr, cc in candidates:
                    avail.sort(key=lambda s: (s[0] - cr)**2 + (s[1] - cc)**2)
                    selected = avail[:n]
                    max_d2 = 0
                    for i in range(n):
                        r1, c1 = selected[i]
                        for j in range(i + 1, n):
                            r2, c2 = selected[j]
                            d2 = (r1 - r2)**2 + (c1 - c2)**2
                            if d2 > max_d2:
                                max_d2 = d2
                    diam = math.sqrt(max_d2)
                    if diam < best_diam:
                        best_diam = diam
                        best_seats = selected
                for s, (row, col) in zip(students, best_seats):
                    solution.seatStudent(s, Seat(rid, row, col))
                    taken_seats.add((row, col))
                    
                for col in range(C):
                    col_seats = [row for row in range(start_row, R) if (row, col) in taken_seats]
                    if col_seats:
                        skyline[col] = max(col_seats) + 1


# ---------------------------------------------------------------------------
# Local Search (Fast Targeted Swaps)
# ---------------------------------------------------------------------------

def fast_local_search(instance, solution):
    G = instance.G
    rooms = list(instance.rooms)
    
    def get_group_diam_in_room(g_id, room_id, seating):
        seats = []
        for s in instance.groups[g_id].students:
            seat = seating[s.id]
            if seat.room_id == room_id:
                seats.append(seat)
        if len(seats) <= 1:
            return 0.0
        max_d2 = 0
        for i in range(len(seats)):
            s1 = seats[i]
            for j in range(i+1, len(seats)):
                s2 = seats[j]
                d2 = (s1.row - s2.row)**2 + (s1.col - s2.col)**2
                if d2 > max_d2:
                    max_d2 = d2
        return math.sqrt(max_d2)

    # List of non-cheater students
    nc_students = [s for s in instance.students if not s.cheater]
    
    for room in rooms:
        rid = room.getId()
        room_nc = [s for s in nc_students if solution.seating[s.id].room_id == rid]
        if len(room_nc) < 2:
            continue
            
        improved = True
        iterations = 0
        while improved and iterations < 100:
            improved = False
            
            # Find outliers for each group in this room
            outliers = []
            for g in range(G):
                g_seats = [solution.seating[s.id] for s in instance.groups[g].students if solution.seating[s.id].room_id == rid]
                if not g_seats:
                    continue
                cr = sum(s.row for s in g_seats) / len(g_seats)
                cc = sum(s.col for s in g_seats) / len(g_seats)
                
                best_s = None
                max_dist = -1
                for s in instance.groups[g].students:
                    if s.cheater:
                        continue
                    seat = solution.seating[s.id]
                    if seat.room_id != rid:
                        continue
                    dist = (seat.row - cr)**2 + (seat.col - cc)**2
                    if dist > max_dist:
                        max_dist = dist
                        best_s = s
                if best_s:
                    outliers.append((best_s, max_dist))
                    
            outliers.sort(key=lambda x: x[1], reverse=True)
            
            for s1, _ in outliers:
                g1 = s1.group_id
                seat1 = solution.seating[s1.id]
                
                g1_seats = [solution.seating[s.id] for s in instance.groups[g1].students if solution.seating[s.id].room_id == rid]
                g1_cr = sum(s.row for s in g1_seats) / len(g1_seats)
                g1_cc = sum(s.col for s in g1_seats) / len(g1_seats)
                
                candidates = []
                for s2 in room_nc:
                    if s2.group_id == g1:
                        continue
                    seat2 = solution.seating[s2.id]
                    dist_s2 = (seat2.row - g1_cr)**2 + (seat2.col - g1_cc)**2
                    dist_s1 = (seat1.row - g1_cr)**2 + (seat1.col - g1_cc)**2
                    if dist_s2 < dist_s1:
                        candidates.append((s2, dist_s2))
                        
                candidates.sort(key=lambda x: x[1])
                
                for s2, _ in candidates[:20]:
                    d1_old = get_group_diam_in_room(g1, rid, solution.seating)
                    d2_old = get_group_diam_in_room(s2.group_id, rid, solution.seating)
                    old_sum = d1_old + d2_old
                    
                    pos1 = solution.seating[s1.id].copy()
                    pos2 = solution.seating[s2.id].copy()
                    
                    solution.seating[s1.id] = pos2
                    solution.seating[s2.id] = pos1
                    
                    d1_new = get_group_diam_in_room(g1, rid, solution.seating)
                    d2_new = get_group_diam_in_room(s2.group_id, rid, solution.seating)
                    new_sum = d1_new + d2_new
                    
                    if new_sum < old_sum - 1e-6:
                        improved = True
                        break
                    else:
                        solution.seating[s1.id] = pos1
                        solution.seating[s2.id] = pos2
                if improved:
                    break
            iterations += 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dataset = "large"
    if len(sys.argv) >= 2:
        dataset = sys.argv[1]

    base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)

    input_file = f"data/{dataset}.txt"
    output_file = f"output/{dataset}.out"
    visualization_file = f"{dataset}.svg"
    statistics_file = f"{dataset}.stats"

    instance = ExamInstance(input_file)
    solution = ExamSolution(instance)

    if instance.M == 1:
        solve_sportshall(instance, solution)
    else:
        solve_multi_room(instance, solution)

    if not solution.checkValid():
        print("Solution check failed after placement! Attempting emergency fallback...")
        solution = ExamSolution(instance, random_solution=True)

    print(f"Cost (before local search) = {solution.getCost()}")

    fast_local_search(instance, solution)
    print(f"Cost (after local search) = {solution.getCost()}")

    if not solution.checkValid():
        print("CRITICAL WARNING: Solution is invalid!")

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
