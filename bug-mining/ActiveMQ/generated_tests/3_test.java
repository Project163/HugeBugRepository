import org.apache.maven.model.Model;
import org.apache.maven.model.io.xpp3.MavenXpp3Reader;
import org.codehaus.plexus.util.xml.pull.XmlPullParserException;
import org.junit.Test;
import java.io.FileReader;
import java.io.IOException;
import static org.junit.Assert.assertEquals;

public class ReproductionTest {

    @Test
    public void testPomScope() throws IOException, XmlPullParserException {
        MavenXpp3Reader reader = new MavenXpp3Reader();
        Model model = reader.read(new FileReader("activemq-optional/pom.xml"));
        assertEquals("compile", model.getDependencies().get(1).getScope());
    }
}