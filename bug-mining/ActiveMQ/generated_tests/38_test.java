import org.junit.jupiter.api.Test;
import org.xml.sax.SAXException;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import java.io.File;
import java.io.IOException;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class ReproductionTest {

    @Test
    public void testProjectXmlArchiveUrl() throws ParserConfigurationException, IOException, SAXException {
        File xmlFile = new File("etc/project.xml");
        DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
        DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
        Document doc = dBuilder.parse(xmlFile);
        doc.getDocumentElement().normalize();

        NodeList mailingLists = doc.getElementsByTagName("mailingList");
        for (int i = 0; i < mailingLists.getLength(); i++) {
            Element mailingList = (Element) mailingLists.item(i);
            String name = mailingList.getElementsByTagName("name").item(0).getTextContent();
            if ("ActiveMQ Developer List".equals(name)) {
                String archiveUrl = mailingList.getElementsByTagName("archive").item(0).getTextContent();
                assertEquals("http://dir.gmane.org/gmane.comp.java.activemq.devel", archiveUrl);
            }
        }
    }
}