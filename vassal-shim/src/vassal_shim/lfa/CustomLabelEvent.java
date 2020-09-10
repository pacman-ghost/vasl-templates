package vassal_shim.lfa ;

import org.w3c.dom.Document ;
import org.w3c.dom.Element ;

// --------------------------------------------------------------------

public class CustomLabelEvent implements Event
{
    String customLabel ;

    public CustomLabelEvent( String customLabel )
    {
        // initialize the CustomLabelEvent
        this.customLabel = customLabel ;
    }

    public Element makeXmlElement( Document doc )
    {
        // create an XML element for the CustomLabelEvent
        Element elem = doc.createElement( "customLabelEvent" ) ;
        elem.setTextContent( customLabel ) ;
        return elem ;
    }

    public String toString()
    {
        // return the CustomLabelEvent as a string
        return "<CustomLabelEvent:" + customLabel + ">" ;
    }
}
