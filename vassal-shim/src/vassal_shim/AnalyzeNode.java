package vassal_shim ;

// --------------------------------------------------------------------

public class AnalyzeNode
{
    // POD container that holds information about a VASL piece.

    String name ;
    int count ;

    public AnalyzeNode( String name )
    {
        // initialize the AnalyzeNode
        this.name = name ;
        this.count = 0 ;
    }

    public void incrementCount() { ++count ; }
}
