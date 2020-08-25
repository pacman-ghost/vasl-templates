package vassal_shim.lfa ;

import org.w3c.dom.Document ;
import org.w3c.dom.Element ;

// --------------------------------------------------------------------

public class TurnTrackEvent implements Event
{
    String playerSide ;
    String turnNo ;
    String phaseName ;

    public TurnTrackEvent( String playerSide, String turnNo, String phaseName )
    {
        // initialize the TurnTrackEvent
        this.playerSide = playerSide ;
        this.turnNo = turnNo ;
        this.phaseName = phaseName ;
    }

    public Element makeXmlElement( Document doc )
    {
        // create an XML element for the TurnTrackEvent
        Element elem = doc.createElement( "turnTrackEvent" ) ;
        elem.setAttribute( "side", playerSide ) ;
        elem.setAttribute( "turnNo", turnNo ) ;
        elem.setAttribute( "phase", phaseName ) ;
        return elem ;
    }

    public String toString()
    {
        // return the TurnTrackEvent as a string
        return "<TurnTrackEvent:" + playerSide + ":" + turnNo + ":" + phaseName + ">" ;
    }
}
