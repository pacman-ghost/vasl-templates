package vassal_shim ;

import javax.swing.JFrame ;
import javax.swing.JMenuBar ;

import VASSAL.tools.menu.MenuManager ;
import VASSAL.tools.menu.MenuBarProxy ;

// --------------------------------------------------------------------

public class ModuleManagerMenuManager extends MenuManager
{
    private final MenuBarProxy menuBar = new MenuBarProxy() ;

    public JMenuBar getMenuBarFor( JFrame fc ) { return null ; }
    public MenuBarProxy getMenuBarProxyFor( JFrame fc ) { return menuBar ; }
}
