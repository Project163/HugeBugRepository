import org.apache.activemq.ActiveMQConnectionFactory;
import org.apache.activemq.ActiveMQQueueBrowser;
import org.apache.activemq.command.ActiveMQQueue;
import org.apache.activemq.command.Response;
import org.apache.activemq.transport.tcp.ResponseHolder;
import org.junit.Test;
import javax.jms.JMSException;
import javax.jms.Queue;
import javax.jms.QueueConnection;
import javax.jms.QueueSession;
import java.lang.reflect.Field;

public class ReproductionTest {

    @Test
    public void testActiveMQQueueBrowserIgnoreInterrupts() throws Exception {
        ActiveMQConnectionFactory connectionFactory = new ActiveMQConnectionFactory("vm://localhost?broker.persistent=false");
        QueueConnection connection = connectionFactory.createQueueConnection();
        QueueSession session = connection.createQueueSession(false, QueueSession.AUTO_ACKNOWLEDGE);
        Queue queue = new ActiveMQQueue("TEST.QUEUE");
        ActiveMQQueueBrowser browser = (ActiveMQQueueBrowser) session.createBrowser(queue);

        // Simulate a long wait in waitForMessage
        Field semaphoreField = ActiveMQQueueBrowser.class.getDeclaredField("semaphore");
        semaphoreField.setAccessible(true);
        Object semaphore = semaphoreField.get(browser);

        Thread browserThread = new Thread(() -> {
            try {
                browser.getNextMessage();
            } catch (JMSException e) {
                e.printStackTrace();
            }
        });

        browserThread.start();

        // Wait for browserThread to enter wait state
        Thread.sleep(1000);

        // Interrupt the browserThread
        browserThread.interrupt();

        // Wait for browserThread to finish
        browserThread.join();

        // Check if the browserThread was interrupted
        if (!browserThread.isInterrupted()) {
            throw new AssertionError("Thread was not interrupted as expected");
        }

        browser.close();
        session.close();
        connection.close();
    }
}