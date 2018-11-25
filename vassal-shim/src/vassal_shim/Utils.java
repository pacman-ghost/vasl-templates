package vassal_shim ;

import org.w3c.dom.NodeList ;
import org.w3c.dom.Node ;

// --------------------------------------------------------------------

public class Utils
{
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
