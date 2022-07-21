package vassal_shim ;

import java.io.BufferedWriter ;
import java.io.FileWriter ;
import java.util.ArrayList ;
import java.lang.reflect.Method ;
import java.lang.reflect.InvocationTargetException ;

import VASSAL.Info ;

import vassal_shim.VassalShim ;

// --------------------------------------------------------------------

public class Main
{
    public static void main( String[] args )
    {
        // FUDGE! In VASSAL 3.4.4, they changed the way the version number is tracked (it's now in the resources),
        // and Info.getVersion() reports the wrong thing OOB :-/ We have to install a StandardConfig instance
        // into the Info class, but since this is a new thing, we have to use reflection to figure out if it exists
        // and we can do it (and we obviously can't check the VASSAL version, since that's what we're trying to set :-/).
        // NOTE: We do this in all cases, not just when we're getting the VASSAL version, since VASL is checking
        // the VASSAL version and complains if there is a mismatch e.g. VASL 6.6.1 was compiled against VASSAL 3.4.6,
        // but even if we're using VASSAL 3.4.6, it mis-reports itself as 3.4.3, so VASL complains. It might just be
        // a warning for the user, but VASL could also be adjusting its behaviour depending on what version of VASSAL
        // is being used, so for safety, we install the VASSAL version number properly. Sigh... :-/
        try {
            // NOTE: We're trying to do this:
            //   Info.setConfig( new StandardConfig() ) ;
            Class<?> infoClass = Class.forName( "VASSAL.Info" ) ;
            Class<?> configClass = Class.forName( "VASSAL.launch.Config" ) ;
            Method setConfigMethod = infoClass.getMethod( "setConfig", configClass ) ;
            Object standardConfig = Class.forName( "VASSAL.launch.StandardConfig" ).getDeclaredConstructor().newInstance() ;
            setConfigMethod.invoke( null, standardConfig ) ;
        } catch( ClassNotFoundException | InstantiationException | IllegalAccessException | NoSuchMethodException | InvocationTargetException ex ) {
            // NOTE: If anything fails, we assume it's because we're on a version earlier than 3.4.4,
            // and hopefully Info.getVersion() will work OOB.
        }

        // execute the specified command
        try {
            if ( args.length == 0 )
                return ;
            String cmd = args[0].toLowerCase() ;
            if ( cmd.equals( "dump" ) ) {
                checkArgs( args, 3, false, "the VASL .vmod file and scenario file" ) ;
                VassalShim shim = new VassalShim( args[1], null ) ;
                shim.dumpScenario( args[2] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "analyze" ) ) {
                checkArgs( args, 4, false, "the VASL .vmod file, scenario file and output file" ) ;
                VassalShim shim = new VassalShim( args[1], null ) ;
                shim.analyzeScenario( args[2], args[3] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "analyzelogs" ) ) {
                checkArgs( args, 4, true, "the VASL .vmod file, log file(s) and output file" ) ;
                ArrayList<String> logFilenames = new ArrayList<String>() ;
                for ( int i=2 ; i < args.length-1 ; ++i )
                    logFilenames.add( args[i] ) ;
                VassalShim shim = new VassalShim( args[1], null ) ;
                shim.analyzeLogs( logFilenames, args[args.length-1] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "update" ) ) {
                checkArgs( args, 7, false, "the VASL .vmod file, boards directory, scenario file, snippets file and output/report files" ) ;
                VassalShim shim = new VassalShim( args[1], args[2] ) ;
                shim.updateScenario( args[3], args[4], args[5], args[6] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "screenshot" ) ) {
                checkArgs( args, 4, false, "the VASL .vmod file, scenario file and output file" ) ;
                VassalShim shim = new VassalShim( args[1], null ) ;
                shim.takeScreenshot( args[2], args[3] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "prepareupload" ) ) {
                checkArgs( args, 5, false, "the VASL .vmod file, scenario file and 2 output files" ) ;
                VassalShim shim = new VassalShim( args[1], null ) ;
                shim.prepareUpload( args[2], args[3], args[4] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "getpieceinfo" ) ) {
                checkArgs( args, 3, false, "the VASL .vmod file, and output file" ) ;
                VassalShim shim = new VassalShim( args[1], null ) ;
                shim.getPieceInfo( args[2] ) ;
                System.exit( 0 ) ;
            }
            else if ( cmd.equals( "version" ) ) {
                checkArgs( args, 2, false, "the output file" ) ;
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

    private static void checkArgs( String[] args, int expected, boolean orMore, String hint )
    {
        // check the number of arguments
        boolean ok ;
        if ( orMore )
            ok = args.length >= expected ;
        else
            ok = args.length == expected ;
        if ( ! ok ) {
            System.out.println( "Incorrect number of arguments, please specify " + hint + "." ) ;
            System.exit( 2 ) ;
        }
    }
}
