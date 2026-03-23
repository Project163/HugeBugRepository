import org.apache.activemq.openwire.OpenWireFormat;
import org.apache.activemq.command.DataStructure;
import org.apache.activemq.command.Message;
import org.junit.Test;
import org.mockito.Mockito;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;

public class ReproductionTest {

    @Test
    public void testClassCastExceptionWithCaching() throws IOException {
        OpenWireFormat format = new OpenWireFormat(true);
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        DataOutputStream dos = new DataOutputStream(baos);

        for (int i = 0; i < 16383; i++) {
            Message message = new Message();
            format.marshal(message, dos);
        }

        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        DataInputStream dis = new DataInputStream(bais);

        for (int i = 0; i < 16383; i++) {
            DataStructure dataStructure = format.unmarshal(dis);
        }
    }
}