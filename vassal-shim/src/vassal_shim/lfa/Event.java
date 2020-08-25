package vassal_shim.lfa ;

import org.w3c.dom.Document ;
import org.w3c.dom.Element ;

// --------------------------------------------------------------------

public interface Event
{
    public Element makeXmlElement( Document doc ) ;
}

