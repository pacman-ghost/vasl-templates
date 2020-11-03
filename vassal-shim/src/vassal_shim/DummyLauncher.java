package vassal_shim ;

import VASSAL.launch.Launcher ;
import VASSAL.tools.menu.MenuManager ;
import java.io.IOException ;

// --------------------------------------------------------------------

class DummyLauncher extends Launcher
{
    public DummyLauncher() {
        // FUDGE! The Launcher constructor does a lot of program initialization (which
        // causes crashes), but running in stand-alone mode stops that from happening.
        super( new String[]{ "--standalone" } ) ;
    }

    protected MenuManager createMenuManager() { return null ; }
    protected void launch() throws IOException {}
}
