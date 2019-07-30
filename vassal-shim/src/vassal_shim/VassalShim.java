package vassal_shim ;

import java.io.File ;
import java.io.FileInputStream ;
import java.io.InputStream ;
import java.io.InputStreamReader ;
import java.io.FileOutputStream ;
import java.io.OutputStream ;
import java.io.BufferedReader ;
import java.io.IOException ;
import java.io.FileNotFoundException ;
import java.net.URISyntaxException ;
import java.util.Collections ;
import java.util.Arrays ;
import java.util.List ;
import java.util.ArrayList ;
import java.util.Map ;
import java.util.HashMap ;
import java.util.Set ;
import java.util.HashSet ;
import java.util.Iterator ;
import java.util.Comparator ;
import java.util.Properties ;
import java.util.regex.Pattern ;
import java.util.regex.Matcher ;
import java.awt.Point ;
import java.awt.Dimension ;

import javax.xml.parsers.DocumentBuilderFactory ;
import javax.xml.parsers.DocumentBuilder ;
import javax.xml.parsers.ParserConfigurationException ;
import javax.xml.transform.TransformerException ;
import javax.xml.transform.TransformerConfigurationException ;
import javax.xml.xpath.XPathExpressionException  ;
import org.w3c.dom.Document ;
import org.w3c.dom.NodeList ;
import org.w3c.dom.Node ;
import org.w3c.dom.Element ;
import org.xml.sax.SAXException ;
import org.slf4j.Logger ;
import org.slf4j.LoggerFactory ;

import VASSAL.build.GameModule ;
import VASSAL.build.GpIdChecker ;
import VASSAL.build.module.GameState ;
import VASSAL.build.module.GameComponent ;
import VASSAL.build.module.ModuleExtension ;
import VASSAL.build.module.ObscurableOptions ;
import VASSAL.build.module.metadata.SaveMetaData ;
import VASSAL.build.widget.PieceSlot ;
import VASSAL.launch.BasicModule ;
import VASSAL.command.Command ;
import VASSAL.command.AddPiece ;
import VASSAL.command.RemovePiece ;
import VASSAL.command.ConditionalCommand ;
import VASSAL.command.AlertCommand ;
import VASSAL.build.module.map.boardPicker.Board ;
import VASSAL.counters.GamePiece ;
import VASSAL.counters.BasicPiece ;
import VASSAL.counters.DynamicProperty ;
import VASSAL.counters.Hideable ;
import VASSAL.counters.FreeRotator ;
import VASSAL.counters.PieceCloner ;
import VASSAL.preferences.Prefs ;
import VASSAL.tools.DataArchive ;
import VASSAL.tools.DialogUtils ;
import VASSAL.tools.io.FileArchive ;
import VASSAL.tools.io.IOUtils ;
import VASSAL.tools.io.FastByteArrayOutputStream ;
import VASSAL.tools.io.ObfuscatingOutputStream ;
import VASSAL.tools.io.ZipArchive ;
import VASSAL.i18n.Resources ;

import vassal_shim.Snippet ;
import vassal_shim.GamePieceLabelFields ;
import vassal_shim.LabelArea ;
import vassal_shim.ReportNode ;
import vassal_shim.AnalyzeNode ;
import vassal_shim.ModuleManagerMenuManager ;
import vassal_shim.Utils ;

// --------------------------------------------------------------------

public class VassalShim
{
    private static final Logger logger = LoggerFactory.getLogger( VassalShim.class ) ;

    private String baseDir ;
    private Properties config ;
    private String labelGpid ;
    private String vmodFilename ;
    private String boardsDir ;

    public VassalShim( String vmodFilename, String boardsDir ) throws IOException
    {
        // initialize
        this.vmodFilename = vmodFilename ;
        this.boardsDir = boardsDir ;

        // figure out where we live
        baseDir = null ;
        try {
            String jarFilename = this.getClass().getProtectionDomain().getCodeSource().getLocation().toURI().getPath() ;
            logger.debug( "Loaded from JAR: {}", jarFilename ) ;
            baseDir = new File( jarFilename ).getParent() ;
            logger.debug( "Base directory: {}", baseDir ) ;
        } catch( URISyntaxException ex ) {
            logger.error( "Can't locate JAR file:", ex ) ;
        }

        // load any config settings
        config = new Properties() ;
        if ( baseDir != null ) {
            File configFile = new File( baseDir + File.separator + "vassal-shim.properties" ) ;
            if ( configFile.isFile() ) {
                logger.info( "Loading properties: {}", configFile.getAbsolutePath() ) ;
                config.load( new FileInputStream( configFile ) ) ;
                for ( String key: config.stringPropertyNames() )
                    logger.debug( "- {} = {}", key, config.getProperty(key) ) ;
            }
        }
        labelGpid = config.getProperty( "LABEL_GPID", "6295" ) ;

        // FUDGE! Need this to be able to load the VASL module :-/
        logger.debug( "Creating the menu manager." ) ;
        new ModuleManagerMenuManager() ;

        // initialize VASL
        logger.info( "Loading VASL module: {}", vmodFilename ) ;
        if ( ! ((new File(vmodFilename)).isFile() ) )
            throw new IllegalArgumentException( "Can't find VASL module: " + vmodFilename ) ;
        DataArchive dataArchive = new DataArchive( vmodFilename ) ;
        logger.debug( "- Initializing module." ) ;
        BasicModule basicModule = new BasicModule( dataArchive ) ;
        logger.debug( "- Installing module." ) ;
        GameModule.init( basicModule ) ;
        logger.debug( "- Loaded OK." ) ;
    }

    public void dumpScenario( String scenarioFilename ) throws IOException
    {
        // load the scenario and dump its commands
        Command cmd = loadScenario( scenarioFilename ) ;
        dumpCommand( cmd, "" ) ;
    }

    public void analyzeScenario( String scenarioFilename, String reportFilename )
        throws IOException, ParserConfigurationException, TransformerConfigurationException, TransformerException
    {
        // load the scenario
        configureBoards() ;
        Command cmd = loadScenario( scenarioFilename ) ;
        cmd.execute() ;

        // analyze the scenario
        logger.info( "Analyzing scenario: " + scenarioFilename ) ;
        HashMap<String,AnalyzeNode> results = new HashMap<String,AnalyzeNode>() ;
        analyzeCommand( cmd, results ) ;

        // generate the report
        Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument() ;
        Element rootElem = doc.createElement( "analyzeReport" ) ;
        doc.appendChild( rootElem ) ;
        for ( String gpid: results.keySet() ) {
            AnalyzeNode node = results.get( gpid ) ;
            Element elem = doc.createElement( "piece" ) ;
            elem.setAttribute( "gpid", gpid ) ;
            elem.setAttribute( "name", node.name ) ;
            elem.setAttribute( "count", Integer.toString( node.count ) ) ;
            rootElem.appendChild( elem ) ;
        }

        // save the report
        Utils.saveXml( doc, reportFilename ) ;
    }

    public void updateScenario( String scenarioFilename, String snippetsFilename, String saveFilename, String reportFilename )
        throws IOException, ParserConfigurationException, SAXException, XPathExpressionException, TransformerException
    {
        // load the snippets supplied to us by the web server
        Map<String,Snippet> snippets = parseSnippets( snippetsFilename ) ;

        // load the scenario
        configureBoards() ;
        Command cmd = loadScenario( scenarioFilename ) ;
        // NOTE: The call to execute() is what's causing the VASSAL UI to appear on-screen. If we take it out,
        // label creation still works, but any boards and existing labels are not detected, presumably because
        // their Command's need to be executed to take effect.
        cmd.execute() ;

        // extract the labels from the scenario
        Map<String,GamePieceLabelFields> ourLabels = new HashMap<String,GamePieceLabelFields>() ;
        ArrayList<GamePieceLabelFields> otherLabels = new ArrayList<GamePieceLabelFields>() ;
        logger.info( "Searching the VASL scenario for labels..." ) ;
        extractLabels( cmd, ourLabels, otherLabels ) ;

        // update the labels from the snippets
        Map< String, ArrayList<ReportNode> > labelReport = processSnippets( ourLabels, otherLabels, snippets ) ;

        // save the scenario
        saveScenario( saveFilename ) ;

        // generate the report
        generateLabelReport( labelReport, reportFilename ) ;

        // NOTE: The test suite always dumps the scenario after updating it, so we could save a lot of time
        // by dumping it here, thus avoiding the need to run this shim again to do the dump (and spinning up
        // a JVM, initializing VASSAL/VASL, etc.) but it's probably worth doing things the slow way, to avoid
        // any possible problems caused by reusing the current session (e.g. there might be some saved state somewhere).
    }

    private Map<String,Snippet> parseSnippets( String snippetsFilename ) throws IOException, ParserConfigurationException, SAXException, XPathExpressionException
    {
        logger.info( "Loading snippets: {}", snippetsFilename ) ;
        Map<String,Snippet> snippets = new HashMap<String,Snippet>() ;

        // load the snippets
        DocumentBuilderFactory docBuilderFactory = DocumentBuilderFactory.newInstance() ;
        DocumentBuilder docBuilder = docBuilderFactory.newDocumentBuilder() ;
        Document doc = docBuilder.parse( new File( snippetsFilename ) ) ;
        doc.getDocumentElement().normalize() ;
        NodeList nodes = doc.getElementsByTagName( "snippet" ) ;
        for ( int i=0 ; i < nodes.getLength() ; ++i ) {
            Node node = nodes.item( i ) ;
            if ( node.getNodeType() != Node.ELEMENT_NODE )
                continue ;
            Snippet snippet = new Snippet( (Element)node, config ) ;
            logger.debug( "- Added snippet '{}' [{}x{}] (labelArea={}) (autoCreate={}):\n{}",
                snippet.snippetId,
                snippet.width, snippet.height,
                snippet.labelArea,
                snippet.autoCreate, snippet.content
            ) ;
            snippets.put( snippet.snippetId, snippet ) ;
        }

        return snippets ;
    }

    private void extractLabels( Command cmd, Map<String,GamePieceLabelFields> ourLabels, ArrayList<GamePieceLabelFields> otherLabels )
    {
        // check if this command is a label we're interested in
        if ( cmd instanceof AddPiece ) {
            AddPiece addPieceCmd = (AddPiece) cmd ;
            if ( addPieceCmd.getTarget() instanceof DynamicProperty ) {
                GamePiece target = addPieceCmd.getTarget() ;
                // NOTE: We can't check for target.getName() == "User-Labeled", it seems to get changed to the first label :shrug:

                // yup - parse the label content
                ArrayList<String> separators = new ArrayList<String>() ;
                ArrayList<String> fields = new ArrayList<String>() ;
                parseGamePieceState( target.getState(), separators, fields ) ;

                // check if the label is one of ours
                String snippetId = isVaslTemplatesLabel( fields, GamePieceLabelFields.FIELD_INDEX_LABEL1 ) ;
                if ( snippetId != null ) {
                    logger.debug( "- Found label (1): {}", snippetId ) ;
                    ourLabels.put( snippetId,
                        new GamePieceLabelFields( target, separators, fields, GamePieceLabelFields.FIELD_INDEX_LABEL1 )
                    ) ;
                }
                else {
                    snippetId = isVaslTemplatesLabel( fields, GamePieceLabelFields.FIELD_INDEX_LABEL2 ) ;
                    if ( snippetId != null ) {
                        logger.debug( "- Found label (2): {}", snippetId ) ;
                        ourLabels.put( snippetId,
                            new GamePieceLabelFields( target, separators, fields, GamePieceLabelFields.FIELD_INDEX_LABEL2 )
                        ) ;
                    } else {
                        otherLabels.add(
                            new GamePieceLabelFields( target, separators, fields, -1 )
                        ) ;
                    }
                }
            }
        }

        // extract labels in sub-commands
        for ( Command c: cmd.getSubCommands() )
            extractLabels( c, ourLabels, otherLabels ) ;
    }

    private String isVaslTemplatesLabel( ArrayList<String> fields, int fieldIndex )
    {
        // check if a label is one of ours
        if ( fieldIndex >= fields.size() )
           return null ;
        Matcher matcher = Pattern.compile( "<!-- vasl-templates:id (.+?) " ).matcher(
            fields.get( fieldIndex )
        ) ;
        if ( ! matcher.find() )
            return null ;
        return matcher.group( 1 ) ;
    }

    private Map< String, ArrayList<ReportNode> >
    processSnippets( Map<String,GamePieceLabelFields> ourLabels, ArrayList<GamePieceLabelFields> otherLabels, Map<String,Snippet> snippets )
    {
        // initialize
        Map< String, ArrayList<ReportNode> > labelReport = new HashMap<String,ArrayList<ReportNode>>() ;
        for ( String key: new String[]{"created","updated","deleted","unchanged"} )
            labelReport.put( key, new ArrayList<ReportNode>() ) ;

        // process each snippet
        logger.info( "Processing snippets..." ) ;
        Iterator< Map.Entry<String,Snippet> > iter = snippets.entrySet().iterator() ;
        while( iter.hasNext() ) {
            Map.Entry<String,Snippet> entry = iter.next() ;
            String snippetId = entry.getKey() ;
            Snippet snippet = entry.getValue() ;
            if ( Utils.startsWith( snippetId, "extras/" ) ) {
                logger.info( "- Skipping extras snippet: " + snippetId ) ;
                continue ;
            }
            logger.debug( "- Processing snippet: {}", snippetId ) ;
            // check if we have a label with a matching snippet ID
            GamePieceLabelFields labelFields = ourLabels.get( snippetId ) ;
            if ( labelFields != null ) {
                logger.debug( "  - Found matching label." ) ;
                ourLabels.remove( snippetId ) ;
            } else {
                // nope - check if there is a legacy label that corresponds to this snippet
                labelFields = findLegacyLabel( otherLabels, snippet ) ;
                if ( labelFields != null )
                    logger.debug( "  - Found matching legacy label." ) ;
                else {
                    // nope - skip this snippet (we will create a new label for it later)
                    logger.debug( "  - Couldn't find matching label." ) ;
                    continue ;
                }
            }
            // we've match the snippet to a label, update the label content
            String currState = labelFields.gamePiece().getState() ;
            String snippetContent = snippet.content.replace( "\n", " " ) ;
            String newState = labelFields.getNewGamePieceState( snippetContent ) ;
            if ( currState.equals( newState ) ) {
                logger.info( "- Skipping label (unchanged): {}", snippetId ) ;
                labelReport.get( "unchanged" ).add( new ReportNode( snippetId, null ) ) ;
            } else {
                logger.info( "- Updating label: {}", snippetId ) ;
                logger.debug( "  - curr state: " + Utils.printableString(currState) ) ;
                logger.debug( "  - new state:  " + Utils.printableString(newState) ) ;
                labelFields.gamePiece().setState( newState ) ;
                labelReport.get( "updated" ).add( new ReportNode( snippetId, null ) ) ;
            }
            iter.remove() ;
        }

        // delete excess labels
        // NOTE: This will only affect labels that have a snippet ID i.e. legacy labels will be left in place.
        for ( String snippetId: ourLabels.keySet() ) {
            if ( Utils.startsWith( snippetId, "extras/" ) )
                continue ;
            logger.info( "- Deleting label: {}", snippetId ) ;
            GamePieceLabelFields labelFields = ourLabels.get( snippetId ) ;
            RemovePiece cmd = new RemovePiece( labelFields.gamePiece() ) ;
            cmd.execute() ;
            labelReport.get( "deleted" ).add( new ReportNode( snippetId, null ) ) ;
        }

        // We now want to create new labels for any snippets left that haven't already been processed.
        //
        // We divide the map into several areas:
        //   +------------------------------------------+
        //   |                 GENERAL                  |
        //   +------------+----------------+------------+
        //   |            |                |            |
        //   |  PLAYER 1  |    board(s)    |  PLAYER 2  |
        //   |            |                |            |
        //   |            |----------------|            +
        //   |            |    OVERFLOW    |            |
        //   +------------------------------------------+
        // Non-player specific labels (e.g. SCENARIO and SSR) go into GENERAL, player-specific labels
        // go into their respective areas, and everything else left over that didn't fit into their
        // normal area goes into OVERFLOW.
        //
        // The exception to this is if the scenario contains no boards, in which case we just create
        // a single GENERAL area that spans the entire available space.
        //
        // NOTE: We don't consider any labels that might already be present in the scenario. While we could
        // handle this, it would slow down an already slow process i.e. the web server would have to dump
        // the scenario, extract any existing labels, calculate their size, then pass that information
        // back to us, so that we can take them into account when placing new labels (which would also
        // then become much more complicated). It's just not worth it for something that will rarely happen.

        // locate the PieceSlot we will use to create labels
        logger.debug( "- Locating PieceSlot: gpid={}", labelGpid ) ;
        PieceSlot labelPieceSlot = null ;
        GpIdChecker gpidChecker = new GpIdChecker() ;
        for ( PieceSlot pieceSlot : GameModule.getGameModule().getAllDescendantComponentsOf( PieceSlot.class ) ) {
            if ( pieceSlot.getGpId().equals( labelGpid ) ) {
                labelPieceSlot = pieceSlot ;
                break ;
            }
        }
        if ( labelPieceSlot == null )
            throw new IllegalArgumentException( "Can't find PieceSlot: gpid=" + labelGpid ) ;

        // initialize our LabelArea's
        int xMargin = Integer.parseInt( config.getProperty( "AUTOCREATE_LABEL_XMARGIN", "20" ) ) ;
        int yMargin = Integer.parseInt( config.getProperty( "AUTOCREATE_LABEL_YMARGIN", "20" ) ) ;
        Map< String, LabelArea > labelAreas = new HashMap<String,LabelArea>() ;
        VASSAL.build.module.Map map ;
        List<VASSAL.build.module.Map> maps = VASSAL.build.module.Map.getMapList() ;
        if ( maps.size() > 1 )
            logger.warn( "WARNING: Found multiple maps - using the first one." ) ;
        map = maps.get( 0 ) ;
        if ( map.getBoardCount() == 0 )
            // the scenario doesn't contain any boards - we create a single GENERAL area that spans
            // the entire map (we assume a single board width, and unlimited height)
            labelAreas.put( "general",
                new LabelArea( "general", new Point(xMargin,yMargin), 2500, 99999, xMargin, yMargin )
            ) ;
        else {
            // get the total amount of space available
            Dimension mapSize = map.mapSize() ;
            int mapWidth = mapSize.width ;
            int mapHeight = mapSize.height ;
            // get the amount of empty space around the boards
            Dimension edgeBuffer = map.getEdgeBuffer() ;
            int borderWidth = edgeBuffer.width ;
            int borderHeight = edgeBuffer.height ;
            labelAreas.put( "general",
                new LabelArea( "general",
                    new Point( xMargin, yMargin ),
                    mapWidth-2*xMargin, borderHeight-2*yMargin,
                    xMargin, yMargin
                )
            ) ;
            labelAreas.put( "player1",
                new LabelArea( "player1",
                    new Point( xMargin, borderHeight ),
                    borderWidth-2*xMargin, mapHeight-borderHeight,
                    xMargin, yMargin
                )
            ) ;
            labelAreas.put( "player2",
                new LabelArea( "player2",
                    new Point( mapWidth-borderWidth+xMargin, borderHeight ),
                    borderWidth-2*xMargin, mapHeight-borderHeight,
                    xMargin, yMargin
                )
            ) ;
            labelAreas.put( "overflow",
                new LabelArea( "overflow",
                    new Point( borderWidth, mapHeight-borderHeight+yMargin ),
                    mapWidth-2*borderWidth, 99999, // nb: unlimited height
                    xMargin, yMargin
                )
            ) ;
        }

        // figure out what order to create the labels
        String snippetOrder = config.getProperty( "AUTOCREATE_LABEL_ORDER",
            "scenario players scenario_note* victory_conditions ssr"
            + " ob_setup_1* ob_note_1* ob_vehicles_1 ob_vehicles_ma_notes_1 ob_vehicle_note_1* ob_ordnance_1 ob_ordnance_ma_notes_1 ob_ordnance_note_1*"
            + " ob_setup_2* ob_note_2* ob_vehicles_2 ob_vehicles_ma_notes_2 ob_vehicle_note_2* ob_ordnance_2 ob_ordnance_ma_notes_2 ob_ordnance_note_2*"
        ) ;
        logger.debug( "Snippet order: {}", snippetOrder ) ;
        Set<String> snippetsKeySet = new HashSet<String>( snippets.keySet() ) ;
        ArrayList<String> snippetIds = new ArrayList<String>() ;
        for ( String snippetId: snippetOrder.split( "\\s+" ) ) {

            if ( snippetId.charAt( snippetId.length()-1 ) == '*' ) {

                // this is a wildcard snippet ID - find all matching snippets
                ArrayList<String> matches = new ArrayList<String>() ;
                String snippetIdStem = snippetId.substring( 0, snippetId.length()-1 ) ;
                Iterator<String> iter2 = snippetsKeySet.iterator() ;
                while( iter2.hasNext() ) {
                    String sid = iter2.next() ;
                    if ( Utils.startsWith( sid, snippetIdStem ) ) {
                        matches.add( sid ) ;
                        iter2.remove() ;
                    }
                }
                Collections.sort( matches, new Comparator<String>() {
                    public int compare( String lhs, String rhs ) {
                        // NOTE: These snippet ID's have the form "xyz.1", "xyz.2", etc. - we sort by the trailing number.
                        int pos = lhs.lastIndexOf( '.' ) ;
                        int lhsVal = Integer.parseInt( lhs.substring( pos+1 ) ) ;
                        pos = rhs.lastIndexOf( '.' ) ;
                        int rhsVal = Integer.parseInt( rhs.substring( pos+1 ) ) ;
                        if ( lhsVal == rhsVal )
                            return 0 ;
                        else
                            return lhsVal < rhsVal ? -1 : +1 ;
                    }
                } ) ;
                for ( String sid: matches )
                    snippetIds.add( sid ) ;

            } else {

                // this is a normal snippet ID - add it to the list (if present)
                if ( snippetsKeySet.contains( snippetId ) ) {
                    snippetIds.add( snippetId ) ;
                    snippetsKeySet.remove( snippetId ) ;
                }

            }
        }
        // add any leftovers
        for ( String snippetId: snippetsKeySet )
            snippetIds.add( snippetId ) ;

        // create new labels
        String forceNewRowForVal = config.getProperty( "AUTOCREATE_LABEL_FORCE_NEW_ROW_FOR",
            "ob_setup_1.1 ob_note_1.1 ob_vehicles_1 ob_ordnance_1 ob_setup_2.1 ob_note_2.1 ob_vehicles_2 ob_ordnance_2"
        ) ;
        logger.debug( "Force new row for: {}", forceNewRowForVal ) ;
        Set<String> forceNewRowFor = new HashSet<String>(
            Arrays.asList( forceNewRowForVal.split( "\\s+" ) )
        ) ;
        logger.info( "Creating labels..." ) ;
        for ( String snippetId: snippetIds ) {

            // get the next snippet
            Snippet snippet = snippets.get( snippetId ) ;
            if ( snippet == null ) {
                logger.info( "- WARNING: Couldn't find a snippet for '{}'.", snippetId ) ;
                continue ;
            }
            if ( ! snippet.autoCreate ) {
                logger.debug( "- Auto-create disabled for '{}'.", snippetId ) ;
                continue ;
            }
            if ( snippet.content.length() == 0 ) {
                logger.info( "- Skipping label creation for '{}' - no content.", snippetId ) ;
                continue ;
            }

            // figure out where to put the new label
            LabelArea labelArea = labelAreas.get( snippet.labelArea ) ;
            if ( labelArea == null )
                labelArea = labelAreas.get( "general" ) ;
            if ( forceNewRowFor.contains( snippetId ) )
                labelArea.startNewRow( snippetId ) ;
            Point pos = labelArea.getNextPosition( snippetId, snippet.width, snippet.height ) ;
            if ( pos == null ) {
                LabelArea labelArea2 = labelAreas.get( "overflow" ) ;
                pos = labelArea2.getNextPosition( snippetId, snippet.width, snippet.height ) ;
                if ( pos == null )
                    throw new RuntimeException( "LabelArea '" + labelArea.getName() + "' and 'overflow' are full!" ) ;
            }

            // create the label
            // NOTE: This is a bit of a hack :-/ We generate a new GamePiece from the PieceSlot, which gives us a label
            // loaded with default values. We then replace these default values with our values, and then add
            // the GamePiece to the game. This will break if the default values ever change, but that's unlikely to happen.
            logger.info( "- Creating label '{}' at [{},{}].", snippetId, pos.x, pos.y ) ;
            GamePiece gamePiece = labelPieceSlot.getPiece() ;
            gamePiece = PieceCloner.getInstance().clonePiece( gamePiece ) ; // nb: the piece needs to be "expanded"
            String defaultUserName = config.getProperty( "DEFAULT_LABEL_USERNAME", "David Sullivan" ) ;
            String defaultLabelText1 = config.getProperty( "DEFAULT_LABEL_TEXT1", "Label" ) ;
            String defaultLabelText2 = config.getProperty( "DEFAULT_LABEL_TEXT2", "no background" ) ;
            String snippetContent = snippet.content.replace( "\n", " " ) ;
            gamePiece.setState(
                gamePiece.getState().replace( "\t"+defaultUserName+"\\", "\tvasl-templates\\" )
                                    .replace( "\t"+defaultLabelText1+"\\", "\t" + snippetContent + "\\" )
                                    .replace( "\t"+defaultLabelText2+"\\", "\t\\" )
                                    .replace( "\tnull;0;0", "\tMap0;" + makeVassalCoordString(pos,snippet) )
            ) ;
            GameModule.getGameModule().getGameState().addPiece( gamePiece ) ;
            labelReport.get( "created" ).add( new ReportNode( snippetId, pos ) ) ;
        }

        return labelReport ;
    }

    private GamePieceLabelFields findLegacyLabel( ArrayList<GamePieceLabelFields> otherLabels, Snippet snippet )
    {
        // NOTE: We match snippets with labels via a snippet ID, stored in the HTML fragments in a special
        // "<!-- vasl-templates:id ... -->" comment. However, for labels created with older versions of vasl-templates,
        // this comment won't be present, so we try to match labels based on the raw content the user entered
        // in the UI of the main program.

        // NOTE: Since we are dealing with labels that don't have a snippet ID, the GamePieceLabelField's won't have
        // their fieldIndex set. We set this if and when we match a legacy label, but we don't handle the case
        // where some phrases are found in label1 and some in label2 :-/ It doesn't really matter which one we use,
        // since one of the fields will be used to store the snippet, and the other one will be blanked out.
        int fieldIndex = -1 ;

        // check each label and record which ones match the snippets's raw content
        ArrayList<GamePieceLabelFields> matches = new ArrayList<GamePieceLabelFields>() ;
        for ( GamePieceLabelFields labelFields: otherLabels ) {

            // check if all the snippet raw content phrases are present in the label
            if ( snippet.rawContent.size() == 0 ) {
                // nb: we can get here for snippets that are always passed through, even if they have no content
                continue ;
            }
            boolean allFound = true ;
            for ( String phrase: snippet.rawContent ) {
                phrase = phrase.replace( "\n", " " ) ;
                String labelContent = labelFields.getLabelContent( GamePieceLabelFields.FIELD_INDEX_LABEL1 ) ;
                if ( labelContent != null && labelContent.indexOf( phrase ) >= 0 ) {
                    fieldIndex = GamePieceLabelFields.FIELD_INDEX_LABEL1 ;
                    continue ;
                }
                labelContent = labelFields.getLabelContent( GamePieceLabelFields.FIELD_INDEX_LABEL2 ) ;
                if ( labelContent != null && labelContent.indexOf( phrase ) >= 0 ) {
                    fieldIndex = GamePieceLabelFields.FIELD_INDEX_LABEL2 ;
                    continue ;
                }
                allFound = false ;
                break ;
            }

            // yup - all phrases were found, record the label as a match
            if ( allFound )
                matches.add( labelFields ) ;
        }

        // NOTE: Exactly one label must match for us to consider it a match (i.e. if there are
        // multiple matches, we do nothing and leave it to the user to sort it out).
        if ( matches.size() == 1 ) {
            GamePieceLabelFields labelFields = matches.get( 0 ) ;
            labelFields.setFieldIndex( fieldIndex ) ;
            return labelFields ;
        }

        return null ;
    }

    private void generateLabelReport( Map<String,ArrayList<ReportNode>> labelReport, String reportFilename )
        throws TransformerException, TransformerConfigurationException, ParserConfigurationException, IOException
    {
        // generate the report
        Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument() ;
        Element rootElem = doc.createElement( "report" ) ;
        doc.appendChild( rootElem ) ;
        boolean wasModified = false ;
        for ( String key: labelReport.keySet() ) {
            ArrayList<ReportNode> reportNodes = labelReport.get( key ) ;
            Element elem = doc.createElement( key ) ;
            for ( ReportNode reportNode: reportNodes ) {
                Element reportNodeElem = doc.createElement( "label" ) ;
                reportNodeElem.setAttribute( "id", reportNode.snippetId ) ;
                if ( reportNode.labelPos != null ) {
                    reportNodeElem.setAttribute( "x", Integer.toString( reportNode.labelPos.x ) ) ;
                    reportNodeElem.setAttribute( "y", Integer.toString( reportNode.labelPos.y ) ) ;
                }
                elem.appendChild( reportNodeElem ) ;
                if ( ! key.equals( "unchanged" ) )
                    wasModified = true ;
            }
            rootElem.appendChild( elem ) ;
        }
        rootElem.setAttribute( "wasModified", wasModified?"true":"false" ) ;

        // save the report
        Utils.saveXml( doc, reportFilename ) ;
    }

    private String makeVassalCoordString( Point pos, Snippet snippet )
    {
        // FUDGE! VASSAL positions labels by the X/Y co-ords of the label's centre (!)
        return Integer.toString( pos.x + snippet.width/2 ) + ";" + Integer.toString( pos.y + snippet.height/2 ) ;
    }

    private void saveScenario( String saveFilename ) throws IOException
    {
        // disable the dialog asking for log file comments
        Prefs prefs = GameModule.getGameModule().getPrefs() ;
        String PROMPT_LOG_COMMENT = "promptLogComment";
        prefs.setValue( PROMPT_LOG_COMMENT, false ) ;

        // FUDGE! We would like to just call GameState.saveGame(), but it calls getRestoreCommand(),
        // which does nothing unless the "save game" menu action has been enabled!?! Due to Java protections,
        // there doesn't seem to be any way to get at this object and enable it, so we have to re-implement
        // the whole saveGame() code without this check :-/

        // get the save string
        Command cmd = getRestoreCommand() ;
        String saveString = GameModule.getGameModule().encode( cmd ) ;

        // save the scenario
        logger.info( "Saving scenario: {}", saveFilename ) ;
        final FastByteArrayOutputStream ba = new FastByteArrayOutputStream() ;
        OutputStream out = null ;
        try {
            out = new ObfuscatingOutputStream( ba ) ;
            out.write( saveString.getBytes( "UTF-8" ) ) ;
            out.close() ;
        }
        finally {
            IOUtils.closeQuietly( out ) ;
        }
        FileArchive archive = null ;
        try {
            archive = new ZipArchive( new File( saveFilename ) ) ;
            String SAVEFILE_ZIP_ENTRY = "savedGame" ;  //$NON-NLS-1$
            archive.add( SAVEFILE_ZIP_ENTRY, ba.toInputStream() ) ;
            (new SaveMetaData()).save( archive ) ;
            archive.close() ;
        }
        finally {
            IOUtils.closeQuietly( archive ) ;
        }
    }

    private static Command getRestoreCommand() // nb: taken from GameState.getRestoreCommand()
    {
        // NOTE: This is the check that's causing the problem :-/
        // if (!saveGame.isEnabled()) {
        //   return null;
        // }

        GameState gameState = GameModule.getGameModule().getGameState() ;
        Command c = new GameState.SetupCommand(false);
        c.append(checkVersionCommand());
        c.append( gameState.getRestorePiecesCommand() );
        for (GameComponent gc : gameState.getGameComponents()) {
            c.append(gc.getRestoreCommand());
        }
        c.append(new GameState.SetupCommand(true));
        return c;
    }

    private static Command checkVersionCommand() {
        // NOTE: This is the same as GameState.checkVersionCommand(), but we can't call that since it's private :-/
        String runningVersion = GameModule.getGameModule().getAttributeValueString(GameModule.VASSAL_VERSION_RUNNING);
        ConditionalCommand.Condition cond = new ConditionalCommand.Lt(GameModule.VASSAL_VERSION_RUNNING, runningVersion);
        Command c = new ConditionalCommand(new ConditionalCommand.Condition[]{cond}, new AlertCommand(Resources.getString("GameState.version_mismatch", runningVersion)));  //$NON-NLS-1$
        String moduleName = GameModule.getGameModule().getAttributeValueString(GameModule.MODULE_NAME);
        String moduleVersion = GameModule.getGameModule().getAttributeValueString(GameModule.MODULE_VERSION);
        cond = new ConditionalCommand.Lt(GameModule.MODULE_VERSION, moduleVersion);
        c.append(new ConditionalCommand(new ConditionalCommand.Condition[]{cond}, new AlertCommand(Resources.getString("GameState.version_mismatch2", moduleName, moduleVersion ))));  //$NON-NLS-1$
        return c;
    }

    private Command loadScenario( String scenarioFilename ) throws IOException
    {
        // load the scenario
        disableBoardWarnings() ;
        logger.info( "Loading scenario: {}", scenarioFilename ) ;
        return GameModule.getGameModule().getGameState().decodeSavedGame(
             new File( scenarioFilename )
        ) ;
    }

    private static void dumpCommand( Command cmd, String prefix )
    {
        // dump the command
        StringBuilder buf = new StringBuilder() ;
        buf.append( prefix + cmd.getClass().getSimpleName() ) ;
        String details = cmd.getDetails() ;
        if ( details != null )
            buf.append( " [" + details + "]" ) ;
        if ( cmd instanceof AddPiece )
            dumpCommandExtras( (AddPiece)cmd, buf, prefix ) ;
        else if ( cmd instanceof GameState.SetupCommand )
            dumpCommandExtras( (GameState.SetupCommand)cmd, buf, prefix ) ;
        else if ( cmd instanceof ModuleExtension.RegCmd )
            dumpCommandExtras( (ModuleExtension.RegCmd)cmd, buf, prefix ) ;
        else if ( cmd instanceof ObscurableOptions.SetAllowed )
            dumpCommandExtras( (ObscurableOptions.SetAllowed)cmd, buf, prefix ) ;
        System.out.println( buf.toString() ) ;

        // dump any sub-commands
        prefix += "  " ;
        for ( Command c: cmd.getSubCommands() )
            dumpCommand( c, prefix ) ;
    }

    private static void dumpCommandExtras( AddPiece cmd, StringBuilder buf, String prefix )
    {
        // dump extra command info
        GamePiece target = cmd.getTarget() ;
        buf.append( ": " + target.getClass().getSimpleName() ) ;
        if ( target.getName().length() > 0 )
            buf.append( "/" + target.getName() ) ;

        // check if this is a command we're interested in
        // NOTE: We used to support VASL 6.3.3, but when we create labels, they're of type Hideable. It would be easy enough
        // to add that here, but 6.3.3 is pretty old (2.5 years), so it's safer to just drop it from the list of supported versions.
        if ( !( target instanceof DynamicProperty ) )
            return ;
        if ( ! target.getName().equals( "User-Labeled" ) )
            return ;

        // dump extra command info
        ArrayList<String> separators = new ArrayList<String>() ;
        ArrayList<String> fields = new ArrayList<String>() ;
        parseGamePieceState( cmd.getState(), separators, fields ) ;
        for ( String field: fields ) {
            buf.append( "\n" + prefix + "- " ) ;
            if ( field.length() > 0 )
                buf.append( Utils.printableString( field ) ) ;
            else
                buf.append( "<empty>" ) ;
        }
    }

    private static void dumpCommandExtras( GameState.SetupCommand cmd, StringBuilder buf, String prefix )
    {
        // dump extra command info
        buf.append( ": starting=" + cmd.isGameStarting() ) ;
    }

    private static void dumpCommandExtras( ModuleExtension.RegCmd cmd, StringBuilder buf, String prefix )
    {
        // dump extra command info
        buf.append( ": " + cmd.getName() + " (" + cmd.getVersion() + ")" ) ;
    }

    private static void dumpCommandExtras( ObscurableOptions.SetAllowed cmd, StringBuilder buf, String prefix )
    {
        // dump extra command info
        buf.append( ": " + cmd.getAllowedIds() ) ;
    }

    private void analyzeCommand( Command cmd, Map<String,AnalyzeNode> results )
    {
        // analyze the command
        if ( cmd instanceof AddPiece ) {
            GamePiece target = ((AddPiece)cmd).getTarget() ;
            logger.debug( "Found piece: " + cmd.getClass().getName() + " ; target=" + target.getClass().getName() ) ;
            // NOTE: Hideable's don't seem to be just a thing with old versions of VASSAL. We still get them
            // when adding a "46mm granatnik wz. 36" (GPID 2172) using VASL 6.4.4 :-/ This also seems to happen
            // with other 1/2" SW counters.
            // NOTE: Other pieces also occasionally appear with weird class types e.g. the Japanese Type 88 75 AA Gun
            // appears as a FreeRotator?!
            if ( target instanceof DynamicProperty || target instanceof Hideable || target instanceof FreeRotator
                 || target.getClass().getName().equals("VASL.counters.TextInfo")
            ) {
                int pos = target.getState().lastIndexOf( ";" ) ;
                String gpid = target.getState().substring( pos+1 ) ;
                if ( ! gpid.equals( labelGpid ) ) {
                    if ( ! results.containsKey( gpid ) ) {
                        logger.debug( "Found new GPID " + gpid + ": " + target.getName() ) ;
                        results.put( gpid, new AnalyzeNode( target.getName() ) ) ;
                    } else {
                        int newCount = results.get( gpid ).incrementCount() ;
                        logger.debug( "Updating count for GPID " + gpid + ": #=" + newCount ) ;
                    }
                }
            }
        }

        // analyze any sub-commands
        for ( Command c: cmd.getSubCommands() )
            analyzeCommand( c, results ) ;
    }

    private static void parseGamePieceState( String state, ArrayList<String> separators, ArrayList<String> fields )
    {
        // parse the GamePiece state
        Matcher matcher = Pattern.compile( "\\\\+\t" ).matcher( state ) ;
        int pos = 0 ;
        while( matcher.find() ) {
            separators.add( matcher.group() ) ;
            fields.add( state.substring( pos, matcher.start() ) ) ;
            pos = matcher.end() ;
        }
        fields.add( state.substring( pos ) ) ;
    }

    private void configureBoards()
    {
        // NOTE: While we can get away with just disabling warnings about missing boards when dumping scenarios,
        // they need to be present when we update a scenario, otherwise they get removed from the scenario :-/
        logger.info( "Configuring boards directory: {}", boardsDir ) ;
        Prefs prefs = GameModule.getGameModule().getPrefs() ;
        String BOARD_DIR = "boardURL" ;
        prefs.setValue( BOARD_DIR, new File(boardsDir) ) ;
    }

    private void disableBoardWarnings()
    {
        // FUDGE! VASSAL shows a GUI error dialog warning about boards not being found, and while these can be disabled,
        // the key used to enable/disable them is derived from the board filename :-( ASLBoardPicker catches
        // the FileNotFoundException thrown by ZipArchive when it can't find a file, and then calls ReadErrorDialog.error(),
        // which calls WarningDialog.showDisableable(), using the following as the key:
        //   (Object) ( e.getClass().getName() + "@" + filename )
        // This means we have to set the "warning disabled" flag for every possible board :-/

        // disable warnings for boards 00-99
        logger.info( "Disabling board warnings for bd00-99." ) ;
        for ( int i=0 ; i < 100 ; ++i )
            disableBoardWarning( String.format( "bd%02d", i ) ) ;

        // disable warnings for additional standard boards
        logger.info( "Disabling board warnings for other standard boards:" ) ;
        InputStream inputStream = this.getClass().getResourceAsStream( "/data/boardNames.txt" ) ;
        disableBoardWarnings( inputStream, "<standard>" ) ;

        // disable warnings for user-defined boards
        if ( baseDir != null ) {
            String fname = baseDir + File.separator + "boardNames.txt" ;
            inputStream = null ;
            try {
                inputStream = new FileInputStream( fname ) ;
            } catch( FileNotFoundException ex ) { }
            if ( inputStream != null ) {
                logger.info( "Disabling board warnings for user-defined boards: " + fname ) ;
                disableBoardWarnings( inputStream, fname ) ;
            }
        }
    }

    private void disableBoardWarnings( InputStream inputStream, String boardFilename )
    {
        // disable warnings for boards listed in a file
        BufferedReader reader = new BufferedReader( new InputStreamReader( inputStream ) ) ;
        String lineBuf ;
        try {
            while ( (lineBuf = reader.readLine() ) != null ) {
                lineBuf = lineBuf.trim() ;
                if ( lineBuf.length() == 0 || lineBuf.charAt(0) == '#' || lineBuf.charAt(0) == ';' || lineBuf.substring(0,2).equals("//") )
                    continue ;
                logger.debug( "- {}", lineBuf ) ;
                disableBoardWarning( lineBuf ) ;
            }
        } catch( IOException ex ) {
            logger.error( "Error reading board file: {}", boardFilename, ex ) ;
        }
    }

    private void disableBoardWarning( String boardName )
    {
        // disable warnings for the specified board
        String boardsPath = (new File(vmodFilename)).getParent() + File.separator + "boards" ;
        String key = "java.io.FileNotFoundException@" + boardsPath + File.separator + boardName ;
        DialogUtils.setDisabled( key, true ) ;
    }
}
