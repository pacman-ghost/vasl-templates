package vassal_shim.lfa ;

import org.w3c.dom.Document ;
import org.w3c.dom.Element ;

// --------------------------------------------------------------------

public class DiceEvent implements Event
{
    String playerName ;
    String rollType ;
    String rollValues ;

    public DiceEvent( String playerName, String rollType, String rollValues )
    {
        // initialize the DiceEvent
        this.playerName = playerName ;
        this.rollType = rollType ;
        this.rollValues = rollValues ;
    }

    public Element makeXmlElement( Document doc )
    {
        // create an XML element for the DiceEvent
        Element elem = doc.createElement( "diceEvent" ) ;
        elem.setAttribute( "player", playerName ) ;
        elem.setAttribute( "rollType", rollType ) ;
        elem.setTextContent( rollValues ) ;
        return elem ;
    }

    public String toString()
    {
        // return the DiceEvent as a string
        return "<DiceEvent:" + playerName + ":" + rollType + ":" + rollValues + ">" ;
    }
}
