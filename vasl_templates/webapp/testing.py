"""Webapp handlers for testing porpoises."""

import inspect

from flask import request, jsonify, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.tests.remote import ControlTests

# ---------------------------------------------------------------------

@app.route( "/control-tests/<action>" )
def control_tests( action ):
    """Accept commands from a remote test suite."""

    # check if this functionality has been enabled
    if not app.config.get( "ENABLE_REMOTE_TEST_CONTROL" ):
        abort( 404 )

    # figure out what we're being asked to do
    controller = ControlTests( app )
    func = getattr( controller, action )
    if not func:
        abort( 404 )

    # get any parameters
    sig = inspect.signature( func )
    kwargs = {}
    for param in sig.parameters.values():
        if param.name in ("vengine","vmod","gpids","dtype","fname","dname"):
            kwargs[ param.name ] = request.args.get( param.name, param.default )

    # execute the command
    resp = func( **kwargs )

    # return any response
    if isinstance( resp, (str,list,dict) ):
        return jsonify( resp )
    else:
        assert resp == controller, "Methods should return self if there is no response data."
        return "ok"
