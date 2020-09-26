package vassal_shim ;

import java.io.File ;

import VASSAL.build.module.map.ImageSaver ;
import VASSAL.build.module.Map ;
import VASSAL.tools.swing.ProgressDialog ;

// --------------------------------------------------------------------

public class AppImageSaver extends ImageSaver
{
    // FUDGE! We implement our own version of ImageSaver so that we can get access
    // to its protected member variables :-/

    // FUDGE! VASSAL's ImageSaver shows a progress dialog as the screenshot is generated,
    // so we need to provide one of these to stop it from crashing :-/
    // We detect when the process has finished when VASSAL "closes" the dialog.
    class DummyProgressDialog extends ProgressDialog
    {
        private boolean isDone ;
        public DummyProgressDialog() {
            super( null, "", "" ) ;
            isDone = false ;
        }
        public void dispose() {
            isDone = true ;
            super.dispose() ;
        }
        public boolean isDone() { return isDone ; }
    }

    public AppImageSaver( Map map )
    {
        // initialize
        super( map ) ;
    }

    public void generateScreenshot( File outputFile, int width, int height, int timeout )
        throws InterruptedException
    {
        // install our dummy progress dialog into ImageSaver
        dialog = new DummyProgressDialog() ;

        // call into VASSAL to generate the screenshot
        super.writeMapRectAsImage( outputFile, 0, 0, width, height ) ;

        // wait for the task to finish
        for ( int i=0 ; i < timeout ; ++i ) {
            if ( ((DummyProgressDialog)dialog).isDone() )
                return ;
            Thread.sleep( 1*1000 ) ;
        }
        throw new RuntimeException( "Screenshot timeout." ) ;
    }
}
