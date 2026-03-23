import org.junit.Test;
import static org.junit.Assert.assertFalse;

public class ReproductionTest {

    @Test
    public void testREADMEContainsOldURLs() throws Exception {
        String readmeContent = "Welcome to ActiveMQ \n" +
                              "=================== \n" +
                              "\n" +
                              "ActiveMQ is a high performance Apache 2.0 licenced Message Broker and JMS 1.1 implementation.\n" +
                              "\n" +
                              "To help you get started, try the following links:-\n" +
                              "\n" +
                              "Getting Started\n" +
                              "http://activemq.org/Getting+Started\n" +
                              "\n" +
                              "Building\n" +
                              "http://activemq.org/Building\n" +
                              "\n" +
                              "Examples\n" +
                              "http://activemq.org/Examples\n" +
                              "\n" +
                              "We welcome contributions of all kinds, for details of how you can help\n" +
                              "http://activemq.codehaus.org/Contributing\n" +
                              "\n" +
                              "Please refer to the website for details of finding the issue tracker, email lists, wiki or IRC channel\n" +
                              "http://activemq.org/\n" +
                              "\n" +
                              "Please help us make ActiveMQ better - we appreciate any feedback you may have.\n" +
                              "\n" +
                              "Enjoy!\n" +
                              "\n" +
                              "-----------------\n" +
                              "The ActiveMQ team";

        assertFalse("README.txt contains old URLs", readmeContent.contains("http://activemq.org/"));
    }
}