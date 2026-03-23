import org.apache.activemq.transport.stomp.StompConnection;
import org.apache.activemq.transport.stomp.StompFrame;
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class ReproductionTest {

    @Test
    public void testStompConnectionFailure() throws Exception {
        StompConnection connection = new StompConnection();
        connection.open("localhost", 61613);
        connection.connect("system", "manager");

        StompFrame connectFrame = connection.receive();
        assertEquals("CONNECTED", connectFrame.getAction());

        connection.send("/queue/test", "test message");
        StompFrame messageFrame = connection.receive();
        assertEquals("MESSAGE", messageFrame.getAction());

        connection.disconnect();
    }
}