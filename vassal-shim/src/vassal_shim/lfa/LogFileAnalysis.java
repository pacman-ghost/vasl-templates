package vassal_shim.lfa ;

import java.util.ArrayList ;

// --------------------------------------------------------------------

public class LogFileAnalysis
{
    public String logFilename ;
    public String scenarioName ;
    public String scenarioId ;
    public ArrayList<Event> events ;

    public LogFileAnalysis( String logFilename, String scenarioName, String scenarioId, ArrayList<Event> events ) {
        this.logFilename = logFilename ;
        this.scenarioName = scenarioName ;
        this.scenarioId = scenarioId ;
        this.events = events ;
    }
}
