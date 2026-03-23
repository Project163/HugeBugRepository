import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.network.DiscoveryNetworkConnector;
import org.apache.activemq.transport.vm.VMTransportFactory;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;

import javax.jms.Connection;
import javax.jms.ConnectionFactory;
import javax.jms.JMSException;
import javax.jms.MessageConsumer;
import javax.jms.MessageProducer;
import javax.jms.Session;
import javax.jms.TextMessage;
import javax.jms.Topic;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

public class ReproductionTest {

    private BrokerService brokerService1;
    private BrokerService brokerService2;
    private ConnectionFactory connectionFactory1;
    private ConnectionFactory connectionFactory2;

    @Before
    public void setUp() throws Exception {
        brokerService1 = new BrokerService();
        brokerService1.setBrokerName("broker1");
        brokerService1.setUseJmx(false);
        brokerService1.addConnector("vm://broker1?broker.persistent=false");

        brokerService2 = new BrokerService();
        brokerService2.setBrokerName("broker2");
        brokerService2.setUseJmx(false);
        brokerService2.addConnector("vm://broker2?broker.persistent=false");

        DiscoveryNetworkConnector networkConnector = new DiscoveryNetworkConnector(new URI("multicast://default"));
        networkConnector.setLocalUri(new URI("vm://broker1?network=true"));
        brokerService1.addNetworkConnector(networkConnector);

        brokerService1.start();
        brokerService2.start();

        connectionFactory1 = brokerService1.getBroker().getVmConnector().getConnectionFactory();
        connectionFactory2 = brokerService2.getBroker().getVmConnector().getConnectionFactory();
    }

    @After
    public void tearDown() throws Exception {
        brokerService1.stop();
        brokerService2.stop();
    }

    @Test
    public void testReconnectWithInvalidClientIDException() throws Exception {
        Connection connection1 = connectionFactory1.createConnection();
        connection1.setClientID("NC_broker1");
        connection1.start();

        Connection connection2 = connectionFactory2.createConnection();
        connection2.setClientID("NC_broker2");
        connection2.start();

        Session session1 = connection1.createSession(false, Session.AUTO_ACKNOWLEDGE);
        Topic topic1 = session1.createTopic("testTopic");
        MessageProducer producer1 = session1.createProducer(topic1);

        Session session2 = connection2.createSession(false, Session.AUTO_ACKNOWLEDGE);
        Topic topic2 = session2.createTopic("testTopic");
        MessageConsumer consumer2 = session2.createConsumer(topic2);

        for (int i = 0; i < 10; i++) {
            TextMessage message = session1.createTextMessage("Message " + i);
            producer1.send(message);
        }

        for (int i = 0; i < 10; i++) {
            TextMessage receivedMessage = (TextMessage) consumer2.receive(1000);
            if (receivedMessage == null) {
                fail("Message " + i + " was not received");
            }
            assertEquals("Message " + i, receivedMessage.getText());
        }

        connection1.close();
        brokerService1.stop();
        brokerService1.start();

        connection1 = connectionFactory1.createConnection();
        connection1.setClientID("NC_broker1");
        connection1.start();

        session1 = connection1.createSession(false, Session.AUTO_ACKNOWLEDGE);
        topic1 = session1.createTopic("testTopic");
        producer1 = session1.createProducer(topic1);

        for (int i = 0; i < 10; i++) {
            TextMessage message = session1.createTextMessage("Message " + i);
            producer1.send(message);
        }

        for (int i = 0; i < 10; i++) {
            TextMessage receivedMessage = (TextMessage) consumer2.receive(1000);
            if (receivedMessage == null) {
                fail("Message " + i + " was not received after reconnect");
            }
            assertEquals("Message " + i, receivedMessage.getText());
        }

        connection1.close();
        connection2.close();
    }
}