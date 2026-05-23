from pathlib import Path
import os
import sys

from src.ExamInstance import ExamInstance
from src.ExamSolution import ExamSolution


def main():
    # Reads data/<dataset>.txt.
    dataset = "small"
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

    # TODO: call your solution here.

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
