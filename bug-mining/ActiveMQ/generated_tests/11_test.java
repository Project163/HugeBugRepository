import org.apache.activemq.ra.ActiveMQManagedConnectionFactory;
import org.apache.activemq.ra.ActiveMQActivationSpec;
import org.apache.activemq.ra.ActiveMQResourceAdapter;
import org.junit.Test;
import javax.resource.ResourceException;
import javax.resource.spi.ManagedConnection;
import javax.resource.spi.ConnectionRequestInfo;
import javax.security.auth.Subject;
import static org.junit.Assert.fail;

public class ReproductionTest {

    @Test
    public void testCreateManagedConnectionWithNullConnectionRequestInfo() throws ResourceException {
        ActiveMQManagedConnectionFactory factory = new ActiveMQManagedConnectionFactory();
        ActiveMQResourceAdapter resourceAdapter = new ActiveMQResourceAdapter();
        factory.setResourceAdapter(resourceAdapter);

        Subject subject = new Subject();
        ConnectionRequestInfo cri = null; // This should cause the NullPointerException

        try {
            ManagedConnection connection = factory.createManagedConnection(subject, cri);
            fail("Expected NullPointerException to be thrown");
        } catch (NullPointerException e) {
            // Expected exception
        }
    }
}