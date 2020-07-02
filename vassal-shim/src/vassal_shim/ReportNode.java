package vassal_shim ;

import java.awt.Point ;

// --------------------------------------------------------------------

public class ReportNode
{
    // POD container that holds information about what was done.

    String snippetId ;
    Point labelPos ;
    String caption ;
    String msg ;

    public ReportNode( String snippetId, Point labelPos, String caption, String msg )
    {
        // initialize the ReportNode
        this.snippetId = snippetId ;
        this.labelPos = labelPos ;
        this.caption = caption ;
        this.msg = msg ;
    }

    public ReportNode( String snippetId, Point labelPos )
    {
        // initialize the ReportNode
        this.snippetId = snippetId ;
        this.labelPos = labelPos ;
    }
}
