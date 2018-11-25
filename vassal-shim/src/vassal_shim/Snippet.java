package vassal_shim ;

import java.util.Properties ;
import java.util.ArrayList ;
import org.w3c.dom.NodeList ;
import org.w3c.dom.Node ;
import org.w3c.dom.Element ;
import javax.xml.xpath.XPathFactory ;
import javax.xml.xpath.XPath ;
import javax.xml.xpath.XPathExpression ;
import javax.xml.xpath.XPathExpressionException ;
import javax.xml.xpath.XPathConstants ;

import vassal_shim.Utils ;

// --------------------------------------------------------------------

public class Snippet
{
    // POD container that holds the snippet information sent to us from the web server.

    public String snippetId ;
    public String content ;
    public ArrayList<String> rawContent ;
    public int width, height ;
    public boolean autoCreate ;
    public String labelArea ;

    public Snippet( Element elem, Properties config ) throws XPathExpressionException
    {
        // initialize
        XPathFactory xpathFactory = XPathFactory.newInstance() ;

        // initialize the Snippet
        this.snippetId = elem.getAttribute( "id" ) ;
        this.content = Utils.getNodeTextContent( elem ) ;
        String snippetWidth = elem.getAttribute( "width" ) ;
        this.width = Integer.parseInt(
            snippetWidth != "" ? snippetWidth : config.getProperty("AUTOCREATE_LABEL_DEFAULT_WIDTH","300")
        ) ;
        String snippetHeight = elem.getAttribute( "height" ) ;
        this.height = Integer.parseInt(
            snippetHeight != "" ? snippetHeight : config.getProperty("AUTOCREATE_LABEL_DEFAULT_HEIGHT","300")
        ) ;
        this.autoCreate = elem.getAttribute( "autoCreate" ).equals( "true" ) ;
        this.labelArea = elem.getAttribute( "labelArea" ) ;

        // initialize the Snippet
        this.rawContent = new ArrayList<String>() ;
        XPathExpression expr = xpathFactory.newXPath().compile( "rawContent/phrase/text()" ) ;
        NodeList nodes = (NodeList) expr.evaluate( elem, XPathConstants.NODESET ) ;
        for ( int i=0 ; i < nodes.getLength() ; ++i ) {
            Node node = nodes.item( i ) ;
            this.rawContent.add( nodes.item(i).getTextContent() ) ;
        }
    }
}
