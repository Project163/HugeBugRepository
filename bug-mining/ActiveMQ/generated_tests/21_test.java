import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

public class ReproductionTest {

    @Test
    public void testBstatDoesNotPassJmxUri() {
        // Redirect System.out to capture output
        ByteArrayOutputStream outContent = new ByteArrayOutputStream();
        System.setOut(new PrintStream(outContent));

        // Simulate running bstat with a broker name and jmxuri
        String[] args = {"localhost", "--jmxuri", "service:jmx:rmi:///jndi/rmi://localhost:1099/jmxrmi"};
        Bstat.main(args);

        // Reset System.out
        System.setOut(System.out);

        // Check if the jmxuri is not present in the output (indicating the bug)
        String output = outContent.toString();
        assertFalse(output.contains("jmxuri=service:jmx:rmi:///jndi/rmi://localhost:1099/jmxrmi"), "jmxuri should not be present in the output");
    }
}