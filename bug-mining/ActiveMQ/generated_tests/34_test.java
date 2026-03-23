import org.apache.activemq.broker.AbstractConnection;
import org.apache.activemq.command.ConnectionId;
import org.apache.activemq.command.ConnectionInfo;
import org.apache.activemq.command.ExceptionResponse;
import org.apache.activemq.command.Response;
import org.apache.activemq.transport.Transport;
import org.apache.activemq.transport.TransportListener;
import org.apache.activemq.util.ServiceSupport;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

class ReproductionTest {

    @Test
    void testClientIdNotReleasedOnTransportException() throws Exception {
        Transport transport = Mockito.mock(Transport.class);
        TransportListener transportListener = Mockito.mock(TransportListener.class);
        Mockito.when(transport.getTransportListener()).thenReturn(transportListener);

        AbstractConnection connection = new AbstractConnection(transport) {
            @Override
            public Response processAddConnection(ConnectionInfo info) throws Exception {
                return null;
            }

            @Override
            public Response processRemoveConnection(ConnectionId id) throws Exception {
                return null;
            }

            @Override
            public Response processKeepAlive(KeepAliveInfo info) throws Exception {
                return null;
            }

            @Override
            public Response processRemoveSubscription(RemoveSubscriptionInfo info) throws Exception {
                return null;
            }
        };

        ConnectionInfo connectionInfo = new ConnectionInfo();
        ConnectionId connectionId = new ConnectionId("test:1");
        connectionInfo.setConnectionId(connectionId);

        connection.start();
        connection.processAddConnection(connectionInfo);

        // Simulate a transport exception
        IOException ioException = new IOException("Simulated network failure");
        connection.serviceTransportException(ioException);

        // Verify that the connection is disposed
        assert connection.isDisposed();

        // Verify that the connection state is removed
        Map<ConnectionId, ConnectionState> connectionStates = new HashMap<>();
        Field field = AbstractConnection.class.getDeclaredField("connectionStates");
        field.setAccessible(true);
        field.set(connection, connectionStates);

        assert connectionStates.isEmpty();
    }
}