import org.apache.activemq.ActiveMQPrefetchPolicy;
import org.apache.activemq.RedeliveryPolicy;
import org.junit.Test;

import java.io.ByteArrayOutputStream;
import java.io.ObjectOutputStream;

import static org.junit.Assert.fail;

public class ReproductionTest {

    @Test
    public void testActiveMQPrefetchPolicySerialization() {
        ActiveMQPrefetchPolicy prefetchPolicy = new ActiveMQPrefetchPolicy();
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            ObjectOutputStream oos = new ObjectOutputStream(bos);
            oos.writeObject(prefetchPolicy);
            oos.flush();
            oos.close();
            bos.close();
        } catch (Exception e) {
            fail("ActiveMQPrefetchPolicy should be serializable but threw an exception: " + e.getMessage());
        }
    }

    @Test
    public void testRedeliveryPolicySerialization() {
        RedeliveryPolicy redeliveryPolicy = new RedeliveryPolicy();
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            ObjectOutputStream oos = new ObjectOutputStream(bos);
            oos.writeObject(redeliveryPolicy);
            oos.flush();
            oos.close();
            bos.close();
        } catch (Exception e) {
            fail("RedeliveryPolicy should be serializable but threw an exception: " + e.getMessage());
        }
    }
}