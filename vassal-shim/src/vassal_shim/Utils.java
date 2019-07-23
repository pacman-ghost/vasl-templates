package vassal_shim ;

import java.io.FileOutputStream ;
import java.io.IOException ;
import javax.xml.transform.TransformerFactory ;
import javax.xml.transform.Transformer ;
import javax.xml.transform.OutputKeys ;
import javax.xml.transform.TransformerException ;
import javax.xml.transform.TransformerConfigurationException ;
import javax.xml.transform.dom.DOMSource ;
import javax.xml.transform.stream.StreamResult ;

import org.w3c.dom.Document ;
import org.w3c.dom.NodeList ;
import org.w3c.dom.Node ;

// --------------------------------------------------------------------

public class Utils
{

    public static void saveXml( Document doc, String fname )
        throws IOException, TransformerConfigurationException, TransformerException
    {
        // save the XML
        Transformer trans = TransformerFactory.newInstance().newTransformer() ;
        trans.setOutputProperty( OutputKeys.INDENT, "yes" ) ;
        trans.setOutputProperty( "{http://xml.apache.org/xslt}indent-amount", "4" ) ;
        trans.setOutputProperty( OutputKeys.METHOD, "xml" ) ;
        trans.setOutputProperty( OutputKeys.ENCODING, "UTF-8" ) ;
        trans.transform( new DOMSource(doc), new StreamResult(new FileOutputStream(fname)) ) ;
    }

    public static String getNodeTextContent( Node node )
    {
        // get the text content for an XML node (just itself, no descendants)
        StringBuilder buf = new StringBuilder() ;
        NodeList childNodes = node.getChildNodes() ;
        for ( int i=0 ; i < childNodes.getLength() ; ++i ) {
            Node childNode = childNodes.item( i ) ;
            if ( childNode.getNodeName().equals( "#text" ) )
                buf.append( childNode.getTextContent() ) ;
        }
        return buf.toString() ;
    }

    public static boolean startsWith( String val, String target )
    {
        // check if a string starts with a target substring
        if ( val.length() < target.length() )
            return false ;
        return val.substring( 0, target.length() ).equals( target ) ;
    }

    public static String printableString( String val )
    {
        // encode non-ASCII characters
        if ( val == null )
            return "<null>" ;
        StringBuilder buf = new StringBuilder() ;
        for ( char ch: val.toCharArray() ) {
            if ( (int)ch >= 32 && (int)ch <= 127 )
                buf.append( ch ) ;
            else
                buf.append( String.format( "<%02x>", (int)ch ) ) ;
        }
        return buf.toString() ;
    }

}
