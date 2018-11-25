package vassal_shim ;

import java.awt.Point ;

// --------------------------------------------------------------------

public class ReportNode
{
    // POD container that holds information about what was done.

    String snippetId ;
    Point labelPos ;

    public ReportNode( String snippetId, Point labelPos )
    {
        // initialize the ReportNode
        this.snippetId = snippetId ;
        this.labelPos = labelPos ;
    }
}
