package vassal_shim ;

import java.awt.Point ;

import org.slf4j.Logger ;
import org.slf4j.LoggerFactory ;

// --------------------------------------------------------------------

public class LabelArea
{
    // Represents a rectangular area on the map in which we will put labels.

    private static final Logger logger = LoggerFactory.getLogger( LabelArea.class ) ;

    private String labelAreaName ;
    private Point topLeft ;
    private int areaWidth, areaHeight ;
    private int xMargin, yMargin ;
    private Point currPos ;
    private int currRowHeight ;

    public String getName() { return labelAreaName ; }

    public LabelArea( String name, Point topLeft, int width, int height, int xMargin, int yMargin )
    {
        logger.info( "Creating LabelArea '{}': topLeft=[{},{}] ; size={}x{} ; xMargin={} ; yMargin={}",
             name, topLeft.x, topLeft.y, width, height, xMargin, yMargin
         ) ;
        this.labelAreaName = name ;
        this.topLeft = topLeft ;
        this.areaWidth = width ;
        this.areaHeight = height ;
        this.xMargin = xMargin ;
        this.yMargin = yMargin ;
        this.currPos = new Point( 0, 0 ) ; // nb: relative to topLeft
        this.currRowHeight = 0 ;
    }

    public Point getNextPosition( String snippet_id, int labelWidth, int labelHeight )
    {
        // NOTE: When trying to position the label, we allow overflow of up to 40% of the label's width,
        // since that will still put the label's centre (which is the click target) in a clear part of the map.

        // check if the label will fit in the next available position
        logger.debug( "Getting next label position ({}): label={}x{}, currPos=[{},{}]",
            labelAreaName, labelWidth, labelHeight, currPos.x, currPos.y
        ) ;
        int overflow = (currPos.x + labelWidth) - areaWidth ;
        logger.debug( "- h.overflow = {}", overflow ) ;
        if ( overflow < 0.4 * labelWidth ) {
            // we have enough horizontal space to place the label, check vertically
            overflow = (currPos.y + labelHeight) - areaHeight ;
            logger.debug( "- can use current row, v.overflow={}", overflow ) ;
            if ( overflow < 0.4 * labelHeight ) {
                // we have enough vertical space as well, put the label in the next available position
                logger.debug( "- can use next available position: [{},{}]", currPos.x, currPos.y ) ;
                Point assignedPos = new Point( topLeft.x+currPos.x, topLeft.y+currPos.y ) ;
                currPos.x += labelWidth + xMargin ;
                currRowHeight = Math.max( currRowHeight, labelHeight ) ;
                return assignedPos ;
            } else {
                // the LabelArea is full - notify the caller
                logger.debug( "- LabelArea is full!" ) ;
                return null ;
            }
        } else {
            // there isn't enough horizontal space to place the label, start a new row
            doStartNewRow() ;
            logger.debug( "- starting a new row: y={}",currPos.y ) ;
            // put the label at the start of the new row
            if ( labelWidth > areaWidth ) {
                // the label is wider than the available width- centre it
                currPos.x = (areaWidth - labelWidth) / 2 ;
            }
            overflow = (currPos.y + labelHeight) - areaHeight ;
            logger.debug( "- v.overflow = {}", overflow ) ;
            if ( overflow >= 0.4 * labelHeight ) {
                // the LabelArea is full - notify the caller
                logger.debug( "- LabelArea is full!" ) ;
                return null ;
            }
            logger.debug( "- assigning position: [{},{}]", currPos.x, currPos.y ) ;
            Point assignedPos = new Point( topLeft.x+currPos.x, topLeft.y+currPos.y ) ;
            currPos.x += labelWidth + xMargin ;
            currRowHeight = Math.max( currRowHeight, labelHeight ) ;
            return assignedPos ;
        }
    }

    public void startNewRow( String snippetId )
    {
        // start a new row
        doStartNewRow() ;
        logger.debug( "Started a new row for '{}': y={}", snippetId, currPos.y ) ;
    }

    private void doStartNewRow()
    {
        // start a new row
        if ( currPos.x == 0 )
            return ;
        currPos.x = 0 ;
        currPos.y += currRowHeight + yMargin ;
        currRowHeight = 0 ;
    }
}
