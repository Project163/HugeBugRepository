import org.apache.activemq.broker.ConnectionContext;
import org.apache.activemq.broker.region.Queue;
import org.apache.activemq.command.ActiveMQDestination;
import org.apache.activemq.command.ActiveMQQueue;
import org.apache.activemq.command.Message;
import org.apache.activemq.command.MessageAck;
import org.apache.activemq.command.MessageId;
import org.apache.activemq.store.MessageStore;
import org.apache.activemq.store.memory.MemoryMessageStore;
import org.apache.activemq.usage.MemoryUsage;
import org.apache.activemq.usage.SystemUsage;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mockito;

import java.util.ArrayList;
import java.util.List;

public class ReproductionTest {

    private Queue queue;
    private ConnectionContext context;
    private MessageStore store;

    @Before
    public void setUp() throws Exception {
        ActiveMQDestination destination = new ActiveMQQueue("TEST.QUEUE");
        SystemUsage memoryManager = new SystemUsage();
        memoryManager.getMemoryUsage().setLimit(1024 * 1024); // 1MB limit
        queue = new Queue(destination, memoryManager.getMemoryUsage(), null, null, null);
        context = new ConnectionContext();
        store = new MemoryMessageStore();
        queue.setMessageStore(store);
    }

    @Test
    public void testOutOfMemoryErrorWithNonPersistentEmbeddedBroker() throws Exception {
        List<Message> messages = new ArrayList<>();
        for (int i = 0; i < 10000; i++) {
            Message message = new Message();
            message.setMessageId(new MessageId("ID:localhost-12345-1234567890123-1:" + i));
            message.setPersistent(false);
            queue.send(context, message);
            messages.add(message);
        }

        MessageAck ack = new MessageAck();
        ack.setAckType(MessageAck.RANGE_ACK_TYPE);
        ack.setFirstMessageId(messages.get(0).getMessageId());
        ack.setLastMessageId(messages.get(messages.size() - 1).getMessageId());

        queue.acknowledge(context, Mockito.mock(org.apache.activemq.broker.region.Subscription.class), ack, null);
    }
}