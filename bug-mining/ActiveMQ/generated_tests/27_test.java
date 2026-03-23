import org.apache.activemq.ActiveMQConnectionFactory;
import org.apache.activemq.ActiveMQMessageConsumer;
import org.apache.activemq.ActiveMQSession;
import org.apache.activemq.command.ActiveMQObjectMessage;
import org.apache.activemq.RedeliveryPolicy;
import org.apache.activemq.Scheduler;
import org.junit.jupiter.api.Test;
import javax.jms.Connection;
import javax.jms.Destination;
import javax.jms.Message;
import javax.jms.MessageConsumer;
import javax.jms.MessageProducer;
import javax.jms.Session;
import java.io.Serializable;

class ReproductionTest {

    @Test
    void testObjectMessageNotDeserializedOnRedelivery() throws Exception {
        Connection connection = new ActiveMQConnectionFactory("vm://localhost?broker.persistent=false").createConnection();
        connection.start();
        Session session = connection.createSession(false, Session.CLIENT_ACKNOWLEDGE);
        Destination destination = session.createQueue("TEST.QUEUE");
        MessageProducer producer = session.createProducer(destination);
        MessageConsumer consumer = session.createConsumer(destination);

        Serializable testObject = new TestSerializableObject("testData");
        ActiveMQObjectMessage message = new ActiveMQObjectMessage();
        message.setObject(testObject);
        producer.send(message);

        Message receivedMessage = consumer.receive(1000);
        receivedMessage.acknowledge();

        // Simulate a rollback to trigger redelivery
        ActiveMQMessageConsumer activeMQConsumer = (ActiveMQMessageConsumer) consumer;
        activeMQConsumer.rollback();

        Message redeliveredMessage = consumer.receive(1000);
        ActiveMQObjectMessage redeliveredObjectMessage = (ActiveMQObjectMessage) redeliveredMessage;
        redeliveredObjectMessage.getObject(); // This should fail if the bug is present

        connection.close();
    }

    static class TestSerializableObject implements Serializable {
        private String data;

        public TestSerializableObject(String data) {
            this.data = data;
        }

        public String getData() {
            return data;
        }
    }
}