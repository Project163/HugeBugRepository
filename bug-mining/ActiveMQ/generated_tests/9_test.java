import org.apache.activemq.broker.Main;
import org.junit.Test;
import java.io.File;
import java.util.Arrays;
import static org.junit.Assert.*;

public class ReproductionTest {

    @Test
    public void testExtensionDirectoryParsing() {
        Main main = new Main();
        List<String> args = Arrays.asList("--extdir", "invalid_directory");
        main.parseExtensions(args);
        assertEquals(1, args.size());
        assertEquals("invalid_directory", args.get(0));
    }

    @Test
    public void testExtensionDirectoryNonExistent() {
        Main main = new Main();
        List<String> args = Arrays.asList("--extdir", "non_existent_directory");
        main.parseExtensions(args);
        assertEquals(0, args.size());
    }

    @Test
    public void testExtensionDirectoryValid() {
        Main main = new Main();
        File tempDir = new File(System.getProperty("java.io.tmpdir"), "test_extdir");
        tempDir.mkdirs();
        List<String> args = Arrays.asList("--extdir", tempDir.getAbsolutePath());
        main.parseExtensions(args);
        assertEquals(0, args.size());
        assertTrue(main.extensions.contains(tempDir));
    }

    @Test
    public void testNoDefaultExtensions() {
        Main main = new Main();
        List<String> args = Arrays.asList("--noDefExt");
        main.parseExtensions(args);
        assertEquals(0, args.size());
        assertFalse(Main.useDefExt);
    }

    @Test
    public void testTaskClassExecution() throws Throwable {
        Main main = new Main();
        main.setActiveMQHome(new File(System.getProperty("java.io.tmpdir")));
        List<String> args = Arrays.asList("arg1", "arg2");
        try {
            main.runTaskClass(args);
            fail("Expected exception to be thrown");
        } catch (ClassNotFoundException e) {
            assertEquals("org.apache.activemq.broker.console.DefaultCommand", e.getMessage());
        }
    }
}