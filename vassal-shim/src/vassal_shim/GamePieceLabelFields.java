package vassal_shim ;

import java.util.ArrayList ;

import VASSAL.counters.GamePiece ;

// --------------------------------------------------------------------

public class GamePieceLabelFields
{
    // Holds the individual fields in a GamePiece label.
    // A GamePiece's state is a string, consisting of a number of separated fields.
    // We parse the string into its constituent parts, so that we can make changes
    // to some fields (i.e. the label content), and re-constitute the state string.

    // These fields contain label #1 and #2.
    public static final int FIELD_INDEX_LABEL1 = 3 ;
    public static final int FIELD_INDEX_LABEL2 = 4 ;

    private GamePiece gamePiece ;
    private ArrayList<String> fields ;
    private ArrayList<String> separators ;
    private int fieldIndex ;

    public GamePiece gamePiece() { return gamePiece ; }
    public String getLabelContent() { return getLabelContent( this.fieldIndex ) ; }
    public String getLabelContent( int fieldIndex ) { return fieldIndex < fields.size() ? fields.get(fieldIndex) : null ; }
    public void setFieldIndex( int fieldIndex ) { this.fieldIndex = fieldIndex ; }

    public GamePieceLabelFields( GamePiece gamePiece, ArrayList<String> separators, ArrayList<String> fields, int fieldIndex )
    {
        this.gamePiece = gamePiece ;
        this.separators = separators ;
        this.fields = fields ;
        this.fieldIndex = fieldIndex ;
    }

    public String getNewGamePieceState( String newField )
    {
        // get the GamePiece's state wih the new field
        fields.set( fieldIndex, newField ) ;
        StringBuilder buf = new StringBuilder() ;
        for ( int i=0 ; i < fields.size() ; ++i ) {
            buf.append( fields.get( i ) ) ;
            if ( i < separators.size() )
                buf.append( separators.get( i ) ) ;
        }
        return buf.toString() ;
    }
}

