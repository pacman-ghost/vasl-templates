package vassal_shim ;

import java.io.BufferedWriter ;
import java.io.FileWriter ;

import VASSAL.Info ;

import vassal_shim.VassalShim ;

// --------------------------------------------------------------------

public class Main
{
    public static void main( String[] args )
    {
        // parse the command line arguments
        if ( args.length == 0 ) {
            printHelp() ;
            System.exit( 0 ) ;
        }

        // execute the specified command
        try {
            String cmd = args[0].toLowerCase() ;
            if ( cmd.equals( "dump" ) ) {
                checkArgs( args, 3, "the VASL .vmod file and scenario file" ) ;
                VassalShim shim = new VassalShim( args[1], null ) ;
                shim.dumpScenario( args[2] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "update" ) ) {
                checkArgs( args, 7, "the VASL .vmod file, boards directory, scenario file, snippets file and output/report files" ) ;
                VassalShim shim = new VassalShim( args[1], args[2] ) ;
                shim.updateScenario( args[3], args[4], args[5], args[6] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "version" ) ) {
                checkArgs( args, 2, "the output file" ) ;
                System.out.println( Info.getVersion() ) ;
                // FUDGE! The Python web server can't capture output on Windows - save the result to a file as well :-/
                BufferedWriter writer = new BufferedWriter( new FileWriter( args[1] ) ) ;
                writer.write( Info.getVersion() ) ;
                writer.close() ;
                System.exit( 0 ) ;
            }
            else {
                System.out.println( "Unknown command: " + cmd ) ;
                System.exit( 1 ) ;
            }
        } catch( Exception ex ) {
            System.out.println( "ERROR: " + ex ) ;
            ex.printStackTrace( System.out ) ;
            System.exit( -1 ) ;
        }
    }

    private static void checkArgs( String[]args, int expected, String hint )
    {
        // check the number of arguments
        if ( args.length != expected ) {
            System.out.println( "Incorrect number of arguments, please specify " + hint + "." ) ;
            System.exit( 2 ) ;
        }
    }

    private static void printHelp()
    {
        // show program usage
        System.out.println( Main.class.getName() + " {command} {options}" ) ;
        System.out.println( "  Provide access to VASSAL functionality." ) ;
        System.out.println() ;
        System.out.println( "Available commands:" ) ;
        System.out.println( "  dump:   Dump a .vsav file." ) ;
        System.out.println( "  update: Update the labels in a .vsav file." ) ;
    }
}
