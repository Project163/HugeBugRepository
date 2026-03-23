import org.apache.activemq.ActiveMQConnection;
import org.apache.activemq.transport.Transport;
import org.apache.activemq.transport.TransportListener;
import org.apache.activemq.transport.TransportSupport;
import org.apache.activemq.transport.mock.MockTransport;
import org.apache.activemq.util.JMSExceptionSupport;
import org.junit.jupiter.api.Test;
import javax.jms.JMSException;
import java.io.IOException;

class ReproductionTest {

    @Test
    void testClientIdNotReleasedOnNetworkFailure() throws Exception {
        Transport transport = new MockTransport() {
            @Override
            public void oneway(Object command) throws IOException {
                if (command instanceof ExceptionResponse) {
                    throw new IOException("Simulated network failure");
                }
                super.oneway(command);
            }
        };

        ActiveMQConnection connection = new ActiveMQConnection(transport, null);
        connection.setClientID("testClientId");
        connection.start();

        // Simulate network failure
        try {
            connection.syncSendPacket(new Object());
        } catch (JMSException e) {
            // Expected exception due to simulated network failure
        }

        // Attempt to reconnect with the same client ID
        ActiveMQConnection newConnection = new ActiveMQConnection(transport, null);
        newConnection.setClientID("testClientId");
        newConnection.start();
    }
}