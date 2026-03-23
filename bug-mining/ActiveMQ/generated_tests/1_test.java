import org.activemq.ActiveMQConnection;
import org.activemq.ActiveMQConnectionFactory;
import org.activemq.pool.PooledConnection;
import org.activemq.pool.PooledConnectionFactory;
import org.junit.Test;
import javax.jms.Session;
import javax.jms.JMSException;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.fail;

public class ReproductionTest {

    @Test
    public void testPooledConnectionClosesAllSessions() throws JMSException {
        ActiveMQConnectionFactory activeMQConnectionFactory = new ActiveMQConnectionFactory("vm://localhost");
        PooledConnectionFactory pooledConnectionFactory = new PooledConnectionFactory(activeMQConnectionFactory);
        PooledConnection pooledConnection = (PooledConnection) pooledConnectionFactory.createConnection();
        pooledConnection.start();

        Session session1 = pooledConnection.createSession(false, Session.AUTO_ACKNOWLEDGE);
        Session session2 = pooledConnection.createSession(false, Session.AUTO_ACKNOWLEDGE);

        assertNotNull(session1);
        assertNotNull(session2);

        pooledConnection.close();

        try {
            session1.getAcknowledgeMode();
            fail("Session should be closed");
        } catch (JMSException e) {
            // Expected
        }

        try {
            session2.getAcknowledgeMode();
            fail("Session should be closed");
        } catch (JMSException e) {
            // Expected
        }
    }
}