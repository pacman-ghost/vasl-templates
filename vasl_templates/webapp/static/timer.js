/* jshint esnext: true */

// --------------------------------------------------------------------

class PerformanceTimer
{
    constructor( msg ) {
        // initialize
        if ( msg )
            console.log( "Starting timer:", msg ) ;
        this.startTimer() ;
    }

    startTimer() {
        // start the timer
        this.startTime = window.performance.now() ;
        return this.startTime ;
    }

    stopTimer() {
        // stop the timer
        var elapsedTime = window.performance.now() - this.startTime ;
        this.startTime = null ;
        return elapsedTime ;
    }

}
