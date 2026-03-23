import org.junit.Test;
import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.ActiveMQConnectionFactory;
import javax.jms.Connection;
import javax.jms.Session;
import javax.jms.Destination;
import javax.jms.MessageProducer;
import javax.jms.MessageConsumer;
import javax.jms.TextMessage;
import javax.jms.JMSException;

public class ReproductionTest {

    @Test
    public void testTwoBrokerTopicSendReceive() throws Exception {
        BrokerService broker1 = new BrokerService();
        broker1.setBrokerName("broker1");
        broker1.addConnector("tcp://localhost:61616");
        broker1.start();

        BrokerService broker2 = new BrokerService();
        broker2.setBrokerName("broker2");
        broker2.addConnector("tcp://localhost:61617");
        broker2.start();

        ActiveMQConnectionFactory factory1 = new ActiveMQConnectionFactory("tcp://localhost:61616");
        Connection connection1 = factory1.createConnection();
        connection1.start();
        Session session1 = connection1.createSession(false, Session.AUTO_ACKNOWLEDGE);
        Destination topic = session1.createTopic("testTopic");
        MessageProducer producer = session1.createProducer(topic);

        ActiveMQConnectionFactory factory2 = new ActiveMQConnectionFactory("tcp://localhost:61617");
        Connection connection2 = factory2.createConnection();
        connection2.start();
        Session session2 = connection2.createSession(false, Session.AUTO_ACKNOWLEDGE);
        MessageConsumer consumer = session2.createConsumer(topic);

        TextMessage message = session1.createTextMessage("Test Message");
        producer.send(message);

        TextMessage receivedMessage = (TextMessage) consumer.receive(5000);
        assert receivedMessage != null && "Test Message".equals(receivedMessage.getText());

        connection1.close();
        connection2.close();
        broker1.stop();
        broker2.stop();
    }
}