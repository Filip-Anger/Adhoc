from pathlib import Path
import os
import sys
import math

from src.ExamInstance import ExamInstance
from src.ExamSolution import ExamSolution
from src.Seat import Seat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_best_rect(n, max_h=10000, max_w=10000):
    """Find (h, w) with h*w >= n, h <= max_h, w <= max_w, minimizing diameter."""
    if n <= 0:
        return (0, 0)
    if n == 1:
        return (1, 1)
    best = None
    best_d = float('inf')
    for h in range(1, min(n, max_h) + 1):
        w = math.ceil(n / h)
        if w > max_w:
            continue
        d = (h - 1) ** 2 + (w - 1) ** 2
        if d < best_d:
            best_d = d
            best = (h, w)
    return best


def get_color(row, col):
    """4-color checkerboard index 0-3."""
    return (row % 2) * 2 + (col % 2)


COLOR_ROW_OFF = [0, 0, 1, 1]
COLOR_COL_OFF = [0, 1, 0, 1]


def skyline_place(n, skyline, max_R, max_C):
    """Find best (top, left, h, w) for n items on a skyline grid.
    Returns None if nothing fits."""
    rect = find_best_rect(n, max_R, max_C)
    if rect is None:
        return None
    h0, w0 = rect

    best = None
    best_d = float('inf')
    best_top = float('inf')

    # Try the optimal rect first, then fallback to other shapes
    candidates = [(h0, w0)]
    # Also try shapes close to optimal
    for h in range(max(1, h0 - 2), min(n, max_R) + 1):
        w = math.ceil(n / h)
        if w > max_C:
            continue
        candidates.append((h, w))

    for h, w in candidates:
        for sc in range(max_C - w + 1):
            top = max(skyline[sc:sc + w]) if w > 0 else 0
            if top + h > max_R:
                continue
            d = (h - 1) ** 2 + (w - 1) ** 2
            if (top < best_top) or (top == best_top and d < best_d):
                best_top = top
                best_d = d
                best = (top, sc, h, w)

    return best


# ---------------------------------------------------------------------------
# All-cheaters solver (e.g. cheaters.txt where C == N)
# ---------------------------------------------------------------------------

def solve_all_cheaters(instance, solution):
    G = instance.G
    rooms = list(instance.rooms)

    # 1. LPT color assignment
    groups_by_size = sorted(range(G),
                            key=lambda g: len(instance.groups[g].students),
                            reverse=True)
    color_load = [0] * 4
    group_color = {}
    for g in groups_by_size:
        c = min(range(4), key=lambda c: color_load[c])
        group_color[g] = c
        color_load[c] += len(instance.groups[g].students)

    # 2. Per-room logical grid dims for each color
    def log_dims(room, c):
        lr = len(range(COLOR_ROW_OFF[c], room.getRows(), 2))
        lc = len(range(COLOR_COL_OFF[c], room.getCols(), 2))
        return lr, lc

    remaining_cap = {}
    for r in rooms:
        for c in range(4):
            lr, lc = log_dims(r, c)
            remaining_cap[(r.getId(), c)] = lr * lc

    # 3. Best-fit bin-pack per color
    assignments = {g: [] for g in range(G)}
    for g in groups_by_size:
        c = group_color[g]
        need = len(instance.groups[g].students)
        # Best-fit single room
        best_rid = None
        best_waste = float('inf')
        for r in rooms:
            cap = remaining_cap[(r.getId(), c)]
            if cap >= need and cap - need < best_waste:
                best_waste = cap - need
                best_rid = r.getId()
        if best_rid is not None:
            assignments[g].append((best_rid, need))
            remaining_cap[(best_rid, c)] -= need
        else:
            for r in sorted(rooms, key=lambda r: remaining_cap[(r.getId(), c)],
                            reverse=True):
                if need <= 0:
                    break
                cap = remaining_cap[(r.getId(), c)]
                if cap <= 0:
                    continue
                take = min(need, cap)
                assignments[g].append((r.getId(), take))
                remaining_cap[(r.getId(), c)] -= take
                need -= take

    # 4. Group by (room, color) for placement
    rc_groups = {}
    for g in range(G):
        c = group_color[g]
        for rid, cnt in assignments[g]:
            rc_groups.setdefault((rid, c), []).append((g, cnt))

    group_idx = {g: 0 for g in range(G)}

    for (rid, c), glist in rc_groups.items():
        r = instance.rooms[rid]
        lr, lc = log_dims(r, c)
        glist.sort(key=lambda x: x[1], reverse=True)

        skyline = [0] * lc

        for g, count in glist:
            pos = skyline_place(count, skyline, lr, lc)
            if pos is None:
                # Fallback: fill any available logical seat
                students = instance.groups[g].students
                idx = group_idx[g]
                placed = 0
                for li in range(lr):
                    for lj in range(lc):
                        if placed >= count:
                            break
                        pr = COLOR_ROW_OFF[c] + 2 * li
                        pc = COLOR_COL_OFF[c] + 2 * lj
                        solution.seatStudent(students[idx],
                                             Seat(rid, pr, pc))
                        idx += 1
                        placed += 1
                    if placed >= count:
                        break
                group_idx[g] = idx
                continue

            log_top, log_left, h, w = pos
            students = instance.groups[g].students
            idx = group_idx[g]
            placed = 0
            for li in range(h):
                for lj in range(w):
                    if placed >= count:
                        break
                    pr = COLOR_ROW_OFF[c] + 2 * (log_top + li)
                    pc = COLOR_COL_OFF[c] + 2 * (log_left + lj)
                    solution.seatStudent(students[idx], Seat(rid, pr, pc))
                    idx += 1
                    placed += 1
                if placed >= count:
                    break
            group_idx[g] = idx
            for lc_i in range(log_left, log_left + w):
                skyline[lc_i] = max(skyline[lc_i], log_top + h)


# ---------------------------------------------------------------------------
# Standard solver (mixed cheaters or no cheaters)
# ---------------------------------------------------------------------------

def solve_standard(instance, solution):
    G = instance.G
    rooms = list(instance.rooms)

    # Separate cheaters / non-cheaters per group
    nc_by_group = [[] for _ in range(G)]
    ch_by_group = [[] for _ in range(G)]
    for s in instance.students:
        if s.cheater:
            ch_by_group[s.group_id].append(s)
        else:
            nc_by_group[s.group_id].append(s)

    # --- Phase 1: assign groups to rooms (best-fit by diameter) -----------
    group_sizes = sorted([(g, len(instance.groups[g].students))
                          for g in range(G)],
                         key=lambda x: x[1], reverse=True)

    room_remaining = {r.getId(): r.getCapacity() for r in rooms}
    assignments = {g: [] for g in range(G)}

    for g, size in group_sizes:
        remaining = size
        # Best-fit considering diameter
        best_rid = None
        best_score = float('inf')
        for r in rooms:
            cap = room_remaining[r.getId()]
            if cap < remaining:
                continue
            rect = find_best_rect(remaining, r.getRows(), r.getCols())
            if rect is None:
                continue
            h, w = rect
            diam = math.sqrt((h - 1) ** 2 + (w - 1) ** 2)
            score = diam + (cap - remaining) * 0.0001  # tie-break by waste
            if score < best_score:
                best_score = score
                best_rid = r.getId()
        if best_rid is not None:
            assignments[g].append((best_rid, remaining))
            room_remaining[best_rid] -= remaining
        else:
            for r in sorted(rooms,
                            key=lambda r: room_remaining[r.getId()],
                            reverse=True):
                if remaining <= 0:
                    break
                cap = room_remaining[r.getId()]
                if cap <= 0:
                    continue
                take = min(remaining, cap)
                assignments[g].append((r.getId(), take))
                room_remaining[r.getId()] -= take
                remaining -= take

    # --- Phase 2: distribute students to rooms ----------------------------
    room_data = {r.getId(): [] for r in rooms}
    for g in range(G):
        nc_pool = list(nc_by_group[g])
        ch_pool = list(ch_by_group[g])
        for rid, count in assignments[g]:
            nc_take = min(len(nc_pool), count)
            ch_take = min(len(ch_pool), count - nc_take)
            room_data[rid].append({
                'gid': g,
                'nc': nc_pool[:nc_take],
                'ch': ch_pool[:ch_take],
            })
            nc_pool = nc_pool[nc_take:]
            ch_pool = ch_pool[ch_take:]

    # --- Phase 3: place students room-by-room -----------------------------
    for r in rooms:
        rid = r.getId()
        R = r.getRows()
        C = r.getCols()
        groups_here = room_data[rid]
        if not groups_here:
            continue

        grid = [[None] * C for _ in range(R)]
        group_pos = {}  # gid -> set of (row,col)

        groups_here.sort(key=lambda x: len(x['nc']), reverse=True)

        # 3a: Place non-cheaters with skyline packing
        skyline = [0] * C

        for entry in groups_here:
            gid = entry['gid']
            nc_students = entry['nc']
            n_nc = len(nc_students)
            group_pos.setdefault(gid, set())
            if n_nc == 0:
                continue

            pos = skyline_place(n_nc, skyline, R, C)

            if pos is not None:
                top, left, h, w = pos
                idx = 0
                for r_off in range(h):
                    for c_off in range(w):
                        if idx >= n_nc:
                            break
                        row, col = top + r_off, left + c_off
                        if grid[row][col] is None:
                            solution.seatStudent(nc_students[idx],
                                                 Seat(rid, row, col))
                            grid[row][col] = nc_students[idx]
                            group_pos[gid].add((row, col))
                            idx += 1
                    if idx >= n_nc:
                        break
                for ci in range(left, left + w):
                    skyline[ci] = max(skyline[ci], top + h)
                # Overflow from block collisions
                for s in nc_students[idx:]:
                    _place_any(s, grid, R, C, rid, solution, group_pos[gid])
            else:
                for s in nc_students:
                    _place_any(s, grid, R, C, rid, solution, group_pos[gid])

        # 3b: Place cheaters in safe (isolated) positions
        for entry in groups_here:
            gid = entry['gid']
            ch_students = entry['ch']
            if not ch_students:
                continue
            same = group_pos.get(gid, set())
            for ch_s in ch_students:
                _place_cheater(ch_s, grid, R, C, rid, solution, same)


def _place_any(student, grid, R, C, rid, solution, pos_set):
    """Place student in the first available empty seat."""
    for row in range(R):
        for col in range(C):
            if grid[row][col] is None:
                solution.seatStudent(student, Seat(rid, row, col))
                grid[row][col] = student
                pos_set.add((row, col))
                return
    raise ValueError(f"No empty seat for student {student.id} in room {rid}")


def _place_cheater(student, grid, R, C, rid, solution, same_pos):
    """Place a cheater in a safe seat closest to their group's centroid."""
    if same_pos:
        cr = sum(r for r, c in same_pos) / len(same_pos)
        cc = sum(c for r, c in same_pos) / len(same_pos)
    else:
        cr, cc = R / 2, C / 2

    best_seat = None
    best_dist = float('inf')

    for row in range(R):
        for col in range(C):
            if grid[row][col] is not None:
                continue
            # Check 8 neighbors for same-group adjacency
            safe = True
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    if (row + dr, col + dc) in same_pos:
                        safe = False
                        break
                if not safe:
                    break
            if safe:
                dist = (row - cr) ** 2 + (col - cc) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_seat = (row, col)

    if best_seat is None:
        # Fallback: accept penalty, use any empty seat
        for row in range(R):
            for col in range(C):
                if grid[row][col] is None:
                    best_seat = (row, col)
                    break
            if best_seat:
                break

    if best_seat is None:
        raise ValueError(f"No seat at all for cheater {student.id} in room {rid}")

    row, col = best_seat
    solution.seatStudent(student, Seat(rid, row, col))
    grid[row][col] = student
    same_pos.add((row, col))


# ---------------------------------------------------------------------------
# Local search: try moving whole group fragments between rooms
# ---------------------------------------------------------------------------

def local_search(instance, solution, max_iter=200):
    """Greedy local search: try swapping group fragments between rooms."""
    G = instance.G
    best_cost = solution.getCost()

    for _ in range(max_iter):
        improved = False
        # Build current group->room distribution
        dist = {}
        for g in range(G):
            dist[g] = {}
            for s in instance.groups[g].students:
                seat = solution.seating[s.id]
                dist[g].setdefault(seat.room_id, []).append(s)

        # For each group that's split, try merging fragments
        for g in range(G):
            if len(dist[g]) <= 1:
                continue
            rooms_list = sorted(dist[g].items(), key=lambda x: len(x[1]))
            smallest_rid, smallest_students = rooms_list[0]
            # Try to move these students to another room that has this group
            for target_rid, target_students in rooms_list[1:]:
                target_room = instance.rooms[target_rid]
                # Find empty seats in target room
                taken = set()
                for sid in range(instance.N):
                    s = solution.seating[sid]
                    if s.room_id == target_rid:
                        taken.add((s.row, s.col))
                empty = []
                for row in range(target_room.getRows()):
                    for col in range(target_room.getCols()):
                        if (row, col) not in taken:
                            empty.append((row, col))
                if len(empty) < len(smallest_students):
                    continue

                # Save old state and try the move
                old_seats = [(s, solution.seating[s.id].copy())
                             for s in smallest_students]
                # Move students
                for i, s in enumerate(smallest_students):
                    row, col = empty[i]
                    solution.seatStudent(s, Seat(target_rid, row, col))

                new_cost = solution.getCost()
                if new_cost < best_cost - 1e-9:
                    best_cost = new_cost
                    improved = True
                    break  # restart scan
                else:
                    # Revert
                    for s, old_seat in old_seats:
                        solution.seatStudent(s, old_seat)
            if improved:
                break

        if not improved:
            break

    return best_cost


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

    if instance.C == instance.N and instance.C > 0:
        solve_all_cheaters(instance, solution)
    else:
        solve_standard(instance, solution)

    if not solution.checkValid():
        print("Solution not valid! Attempting fixup...")
        # Emergency: re-init random and try again
        solution = ExamSolution(instance, random_solution=True)

    print(f"Cost (before local search) = {solution.getCost()}")

    final_cost = local_search(instance, solution)
    print(f"Cost (after local search) = {final_cost}")

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
