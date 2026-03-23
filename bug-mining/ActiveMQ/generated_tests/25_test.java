import org.apache.activemq.ra.MessageEndpointProxy;
import org.apache.activemq.ra.ServerSessionPoolImpl;
import org.apache.activemq.ra.ActiveMQEndpointWorker;
import org.apache.activemq.ra.ActiveMQActivationSpec;
import org.apache.activemq.ra.LocalAndXATransaction;
import org.apache.activemq.ActiveMQSession;
import org.apache.activemq.command.MessageDispatch;
import org.junit.Test;
import javax.jms.JMSException;
import javax.jms.Session;
import javax.resource.spi.UnavailableException;
import javax.resource.spi.endpoint.MessageEndpoint;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.LinkedList;

import static org.junit.Assert.fail;
import static org.mockito.Mockito.*;

public class ReproductionTest {

    @Test
    public void testNPEWhenEndpointFactoryNeverCreatesEndpoints() throws Exception {
        ActiveMQEndpointWorker activeMQAsfEndpointWorker = mock(ActiveMQEndpointWorker.class);
        ActiveMQActivationSpec activationSpec = mock(ActiveMQActivationSpec.class);
        when(activeMQAsfEndpointWorker.endpointActivationKey.getActivationSpec()).thenReturn(activationSpec);
        when(activationSpec.getEnableBatchBooleanValue()).thenReturn(false);
        when(activationSpec.isUseRAManagedTransactionEnabled()).thenReturn(true);
        when(activeMQAsfEndpointWorker.connection.createSession(anyBoolean(), anyInt())).thenReturn(mock(ActiveMQSession.class));
        when(activeMQAsfEndpointWorker.endpointFactory.createEndpoint(any())).thenReturn(null);

        ServerSessionPoolImpl serverSessionPool = new ServerSessionPoolImpl(activeMQAsfEndpointWorker, 10);

        try {
            serverSessionPool.getServerSession();
            fail("Expected NullPointerException to be thrown");
        } catch (NullPointerException e) {
            // Expected
        }
    }
}