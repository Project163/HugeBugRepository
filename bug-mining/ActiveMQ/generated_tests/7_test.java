import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.broker.TransportConnector;
import org.apache.activemq.transport.TransportServer;
import org.apache.activemq.transport.vm.VMTransportFactory;
import org.apache.activemq.transport.vm.VMTransportServer;
import org.junit.Test;

import javax.management.ObjectName;
import java.net.URI;
import java.util.HashMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

public class ReproductionTest {

    @Test
    public void testDiscoveryUriNotRecordedOnTransportConnectorWhenJMXInUse() throws Exception {
        BrokerService brokerService = new BrokerService();
        brokerService.setUseJmx(true);

        URI discoveryUri = new URI("discovery:multicast://default");
        TransportServer transportServer = new VMTransportFactory().doBind(discoveryUri);
        TransportConnector connector = new TransportConnector();
        connector.setServer(transportServer);

        TransportConnector addedConnector = brokerService.addConnector(connector);

        assertNotNull(addedConnector.getDiscoveryUri());
        assertEquals(discoveryUri, addedConnector.getDiscoveryUri());
    }
}