import org.apache.activemq.advisory.AdvisoryBroker;
import org.apache.activemq.broker.Broker;
import org.apache.activemq.broker.BrokerContext;
import org.apache.activemq.broker.ConnectionContext;
import org.apache.activemq.command.ActiveMQDestination;
import org.apache.activemq.command.ActiveMQTempTopic;
import org.apache.activemq.command.ConnectionInfo;
import org.apache.activemq.command.DestinationInfo;
import org.apache.activemq.command.ProducerInfo;
import org.apache.activemq.command.SessionInfo;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;

import java.util.concurrent.ConcurrentHashMap;

import static org.junit.Assert.fail;

public class ReproductionTest {

    private AdvisoryBroker advisoryBroker;
    private ConnectionContext connectionContext;
    private ActiveMQTempTopic tempTopic;
    private DestinationInfo destinationInfo;
    private ProducerInfo producerInfo;

    @Before
    public void setUp() throws Exception {
        Broker nextBroker = Mockito.mock(Broker.class);
        advisoryBroker = new AdvisoryBroker(nextBroker);
        connectionContext = new ConnectionContext();
        connectionContext.setBroker(nextBroker);
        connectionContext.setConnectionId(new ConnectionId("test:1"));
        connectionContext.setClientId("testClientId");

        tempTopic = new ActiveMQTempTopic("temp-topic://TEST");
        destinationInfo = new DestinationInfo();
        destinationInfo.setConnectionId(connectionContext.getConnectionId());
        destinationInfo.setOperationType(DestinationInfo.ADD_OPERATION_TYPE);
        destinationInfo.setDestination(tempTopic);

        SessionInfo sessionInfo = new SessionInfo(connectionContext.getConnectionId(), 1);
        connectionContext.addSession(sessionInfo);

        producerInfo = new ProducerInfo(sessionInfo.getSessionId(), 1);
        producerInfo.setDestination(tempTopic);
    }

    @Test
    public void testTemporaryDestinationNotSentAcrossNetworkBridge() throws Exception {
        advisoryBroker.addDestination(connectionContext, tempTopic);
        advisoryBroker.addProducer(connectionContext, producerInfo);

        // Simulate the removal of the destination on the remote broker
        advisoryBroker.removeDestination(connectionContext, tempTopic, 0);

        // Attempt to send a message to the removed temporary destination
        try {
            advisoryBroker.processMessage(new org.apache.activemq.command.Message(producerInfo.getProducerId(), tempTopic));
            fail("Expected JMSException: Cannot publish to a deleted Destination");
        } catch (Exception e) {
            // Expected exception
        }
    }
}