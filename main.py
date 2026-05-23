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

    # Collect all available seats across all rooms in order of room, row, and column.
    all_seats = []
    for room in instance.rooms:
        for row in range(room.getRows()):
            for col in range(room.getCols()):
                all_seats.append(Seat(room.getId(), row, col))

    # Seat students group by group sequentially into the available seats.
    seat_idx = 0
    for g in range(instance.G):
        group = instance.groups[g]
        for student in group.students:
            solution.seatStudent(student, all_seats[seat_idx])
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
