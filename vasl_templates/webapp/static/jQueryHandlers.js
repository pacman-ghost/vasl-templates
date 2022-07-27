/* jshint esnext: true */

// Manage jQuery event handlers.
class jQueryHandlers
{

    constructor() {
        // initialize
        this.events = [] ;
    }

    addHandler( $elem, evtType, handler ) {
        // add an event handler
        $elem.on( evtType, handler ) ;
        this.events.push( [ $elem, evtType, handler ] ) ;
    }

    cleanUp() {
        // clean up event handlers
        for ( var i=this.events.length-1 ; i >= 0 ; --i ) {
            var evt = this.events[ i ] ;
            evt[0].off( evt[1], evt[2] ) ;
        }
    }

}
