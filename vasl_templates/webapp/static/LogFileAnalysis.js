/* jshint esnext: true */

// --------------------------------------------------------------------

// Wrapper around the results of a log file analysis.
class LogFileAnalysis
{

    constructor( data, logFileNo ) {

        // initialize
        var logFiles=[], playersSeen={}, events=[], title=null, title2=null ;

        // process each log file
        data.logFiles.forEach( function( logFile, index ) {
            if ( logFileNo >= 0 && logFileNo != index )
                return ;
            // record the next log file and generate an event for it
            logFiles.push( logFile.filename ? logFile.filename : "file #"+(1+index) ) ;
            events.push( { eventType: "logFile", filename: logFile.filename } ) ;
            // take a copy of each event
            logFile.events.forEach( function( evt ) {
                events.push( evt ) ;
                playersSeen[ evt.playerId ] = true ;
            } ) ;
            // check if we found a scenario name in the log file
            if ( logFile.scenario.scenarioName ) {
                // NOTE: We prefer the last (i.e. probably the most recent) scenario name/ID.
                title = logFile.scenario.scenarioName ;
                title2 = logFile.scenario.scenarioId ;
            }
        } ) ;

        // check if we found a scenario name
        if ( ! title ) {
            // nope - just use the log filename
            title = logFiles[0] ;
            if ( logFiles.length > 1 )
                title2 = "and " + (logFiles.length-1) + " " + pluralString(logFiles.length-1,"other","others") ;
        }

        // keep only the players seen in the events
        var players={}, playerIds=[] ;
        for ( var playerId in data.players ) {
            if ( ! playersSeen[playerId] )
                continue ;
            players[ playerId ] = data.players[ playerId ] ;
            playerIds.push( playerId ) ;
        }

        // check if the user is one of the scenario players
        if ( gUserSettings[ "vasl-username" ] ) {
            var vaslUserName = gUserSettings[ "vasl-username" ].toLowerCase() ;
            for ( var i=0 ; i < playerIds.length ; ++i ) {
                playerId = playerIds[ i ] ;
                if ( players[ playerId ].toLowerCase() === vaslUserName ) {
                    // yup - change their name to "Me" and put them first
                    players[ playerId ] = "Me" ;
                    var tmp = playerIds[0] ;
                    playerIds[0] = playerId ;
                    playerIds[i] = tmp ;
                    break ;
                }
            }
        }

        // save the extracted results
        this._players = players ; // nb: maps player ID's to names
        this._playerIds = playerIds ; // nb: ordered list of player ID's
        this.logFiles = logFiles ;
        this.logFileNo = logFileNo ;
        this.events = events ;
        this.title = title ;
        this.title2 = title2 ;
    }

    extractStats( filter ) {

        // initialize
        var events = this.events ;

        function doExtractStats( playerId, singleDie ) {

            // initialize
            var stats2 = { nRolls: 0, distrib: {} } ;
            var rollTotal = 0 ;

            // process each event
            events.forEach( function( evt ) {
                if ( evt.eventType !== "roll" || playerId != evt.playerId )
                    return ;
                if ( filter && ! filter(evt) )
                    return ;
                if ( singleDie && ! LogFileAnalysis.isSingleDie( evt.rollValue ) )
                    return ;
                else if ( ! singleDie && LogFileAnalysis.isSingleDie( evt.rollValue ) )
                    return ;
                stats2.nRolls += 1 ;
                var evtRollTotal = LogFileAnalysis.rollTotal( evt.rollValue ) ;
                rollTotal += evtRollTotal ;
                if ( stats2.distrib[ evtRollTotal ] )
                    stats2.distrib[ evtRollTotal ] += 1 ;
                else
                    stats2.distrib[ evtRollTotal ] = 1 ;
            } ) ;

            stats2.rollAverage = rollTotal / stats2.nRolls ;
            return stats2 ;
        }

        // extract the stats for each player
        var stats = { totalRolls: { DR: 0, dr: 0 } } ;
        this.forEachPlayer( function( playerId ) {
            stats[ playerId ] = {
                DR: doExtractStats( playerId, false ),
                dr: doExtractStats( playerId, true ),
            } ;
            stats.totalRolls.DR += stats[playerId].DR.nRolls ;
            stats.totalRolls.dr += stats[playerId].dr.nRolls ;
        } ) ;

        return stats ;
    }

    extractEvents( windowSize, handlers ) {

        // initialize
        var windowVals={}, events=[], nRolls={} ;
        this.forEachPlayer( function( playerId ) {
            windowVals[playerId] = [] ;
            nRolls[playerId] = 0 ;
        } ) ;

        function callHandler( handlerName, evt ) {
            // invoke the specified handler
            if ( handlerName[0] != "_" )
                handlerName = "on" + handlerName[0].toUpperCase() + handlerName.substring(1) + "Event" ;
            var handler = handlers[ handlerName ] ;
            if ( ! handler )
                return null ;
            return handler( evt ) ;
        }

        // process each event
        this.events.forEach( function( evt ) {

            // notify the caller
            var rc = callHandler( evt.eventType, evt ) ;
            if ( rc === false )
                return ; // nb: the caller wants to ignore this event

            // check if this is a DR/dr roll
            if ( evt.eventType === "roll" ) {
                // yup - update the values in the window buffer
                var playerId = evt.playerId ;
                ++ nRolls[ playerId ] ;
                windowVals[playerId].push( evt.rollValue ) ;
                if ( windowVals[playerId].length < windowSize ) {
                    return ;
                }
                // calculate the next moving average from the buffered values
                var rollTotal = windowVals[playerId].reduce( function( total, v ) {
                    return total + LogFileAnalysis.rollTotal( v ) ;
                }, 0 ) ;
                var movingAverage = rollTotal / windowVals[playerId].length ;
                windowVals[playerId].shift() ;
                var newEvent = {
                    eventType: evt.eventType,
                    playerId: playerId,
                    rollType: evt.rollType,
                    rollValue: evt.rollValue,
                    movingAverage: movingAverage,
                    rollNo: nRolls[ playerId ],
                } ;
                // add the new value to the results
                callHandler( "_onAddEvent", newEvent ) ;
                events.push( newEvent ) ;
            }
        } ) ;

        return {
            events: events,
            nRolls: nRolls,
            windowSize: windowSize
        } ;
    }

    calcHotness( stats ) {

        // Dice "hotness" is a metric that tries to capture how good a set of rolls are. Chi-squared is the metric
        // usually used to determine how far a set of observed values is from the expected distribution, but it doesn't
        // distinguish from the rolls tending towards high or low values.
        //
        // So, we modify the chi-squared calculation as follows:
        // - take the square of the difference between the observed and expected values (as normal)
        // - however, we preserve the sign, then multiply it by a weight
        // - the values are summed
        //
        // These changes have the following effect:
        // - Weighting the columns means that if we roll more than the expected number of 5's and 6's, that will
        //   increase the score, but it we roll more 2's and 3's, that will increase the score by even more.
        // - Also, because the weights are negative for rolls >= 8, rolling more of these makes the score go down.
        // - Preserving the sign means that if we roll more 2's than expected, the score increases, but if we roll
        //   fewer than expected, the score will decrease. Similarly, if we roll more 10's than expected, the score
        //   will go down (because while the squared difference is positive, the weight is negative).

        function doCalcHotness( stats, expected, weights ) {
            if ( stats.nRolls === 0 )
                return null ;
            var total = 0 ;
            for ( var val in weights ) {
                var observed = stats.distrib[val] || 0 ;
                var diff = observed/stats.nRolls - expected[val]/100 ;
                var sign = diff < 0 ? -1 : +1 ;
                var delta = sign * Math.pow(diff,2) * weights[val] / (expected[val]/100) ;
                total += delta ;
            }
            return total ;
        }

        // calculate how hot the dice were
        var results = {} ;
        this.forEachPlayer( function( playerId ) {
            var hotness = {} ;
            for ( var key in LogFileAnalysis.EXPECTED_DISTRIB ) {
                hotness[ key ] = doCalcHotness(
                    stats[ playerId ][ key ],
                    LogFileAnalysis.EXPECTED_DISTRIB[ key ],
                    gAppConfig.LFA_DICE_HOTNESS_WEIGHTS[ key ]
                ) ;
            }
            // NOTE: Dice hotness (and chi-squared) aren't particularly meaningful for small datasets,
            // and can have very skewed results. However, if there are enough DR's, we don't want to let
            // there only being a few dr's from stopping us from showing a result. It's tricky to handle
            // this case (we can't just add in the dr score if there are enough dr's, since that would
            // benefit someone over another player who didn't have enough dr's), so we just ignore dr's :-/
            var rollRatio = stats[playerId].DR.nRolls / gAppConfig.LFA_DICE_HOTNESS_THRESHOLDS.DR ;
            results[ playerId ] = [ hotness.DR, rollRatio ] ;
        } ) ;

        return results ;
    }

    getRollTypes() {
        // return the roll types
        var rollTypes = {} ;
        this.events.forEach( function( evt ) {
            if ( evt.eventType === "roll" && ! rollTypes[ evt.rollType ] )
                rollTypes[ evt.rollType ] = true ;
        } );
        return Object.keys( rollTypes ) ;
    }

    forEachPlayer( func ) {
        // call the specified function for each player
        var playerIds = this.playerIds() ;
        for ( var i=0 ; i < playerIds.length ; ++i )
            func( playerIds[i], i ) ;
    }

    playerIds() { return this._playerIds ; }
    playerName( playerId ) { return this._players[ playerId ] ; }

    static rollTotal( roll ) {
        // return the total of a DR/dr
        if ( LogFileAnalysis.isSingleDie( roll ) )
            return roll ;
        else
            return roll.reduce( function (total,n) { return  total + n ; }, 0 ) ;
    }

    static isSingleDie( roll ) {
        // check if a roll is a DR or dr
        return ! Array.isArray( roll ) ;
    }

}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

LogFileAnalysis.EXPECTED_DISTRIB = {
    DR: { 2: 2.8, 3: 5.6, 4: 8.3, 5: 11.1, 6: 13.9, 7: 16.7, 8: 13.9, 9: 11.1, 10: 8.3, 11: 5.6, 12: 2.8 },
    dr: { 1: 16.7, 2: 16.7, 3: 16.7, 4: 16.7, 5: 16.7, 6: 16.7 },
} ;
