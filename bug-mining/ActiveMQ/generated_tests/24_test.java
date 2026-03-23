import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;

import junit.framework.TestCase;

public class ReproductionTest extends TestCase {

    public void testBooleanStreamLargeUnmarshal() throws Exception {
        BooleanStream bs = new BooleanStream();
        for (int i = 0; i < 1000; i++) {
            bs.writeBoolean(i % 2 == 0);
        }
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        DataOutputStream ds = new DataOutputStream(buffer);
        bs.marshal(ds);
        ds.close();

        ByteArrayInputStream in = new ByteArrayInputStream(buffer.toByteArray());
        DataInputStream dis = new DataInputStream(in);
        bs = new BooleanStream();
        bs.unmarshal(dis);

        for (int i = 0; i < 1000; i++) {
            boolean expected = i % 2 == 0;
            boolean actual = bs.readBoolean();
            assertEquals("value of object: " + i + " was: " + actual, expected, actual);
        }
    }
}