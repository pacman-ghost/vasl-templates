"""Webapp handlers for testing porpoises."""

import inspect
import base64

from flask import request, jsonify, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.tests.remote import ControlTests

_control_tests = ControlTests( app )

# ---------------------------------------------------------------------

@app.route( "/control-tests/<action>" )
def control_tests( action ):
    """Accept commands from a remote test suite."""

    # check if this functionality has been enabled
    if not app.config.get( "ENABLE_REMOTE_TEST_CONTROL" ):
        abort( 404 )

    # figure out what we're being asked to do
    func = getattr( _control_tests, action )
    if not func:
        abort( 404 )

    # get any parameters
    sig = inspect.signature( func )
    kwargs = {}
    for param in sig.parameters.values():
        if param.name in ("vengine","vmod","gpids","key","val","dtype","fname","dname","extns_dtype","bin_data"):
            kwargs[ param.name ] = request.args.get( param.name, param.default )
            if param.name == "bin_data":
                kwargs["bin_data"] = base64.b64decode( kwargs["bin_data"] )

    # execute the command
    resp = func( **kwargs )

    # return any response
    if isinstance( resp, (str,list,dict) ):
        return jsonify( resp )
    else:
        assert resp == _control_tests, "Methods should return self if there is no response data."
        return "ok"
