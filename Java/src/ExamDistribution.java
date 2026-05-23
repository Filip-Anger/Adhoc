import java.util.Locale;

public class ExamDistribution {
    public static void main(String[] args) {
        Locale.setDefault(Locale.US);

        // Reads data/<dataset>.txt.
        String dataset = "sportshall";

        // Load the instance and create an initial random solution.
        ExamInstance inst = new ExamInstance("data/" + dataset + ".txt");
        ExamSolution sol = new ExamSolution(inst, false);

        // TODO: call your solution here.

        // checkValid checks feasibility, not optimality.
        if (!sol.checkValid()) {
            System.out.println("Solution not valid!");
        }

        System.out.println("Cost = " + sol.getCost());

        // Write solution, visualization, and statistics files.
        sol.output("output/" + dataset + ".out");
        sol.visualize(dataset + ".svg");
        sol.stats(dataset + ".stats");

        System.out.println("Output written to output/" + dataset + ".out");
        System.out.println("Visualization written to visualizations/" + dataset + ".svg");
        System.out.println("Statistics written to statistics/" + dataset + ".stats");
    }
}