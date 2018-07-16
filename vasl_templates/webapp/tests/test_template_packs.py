"""Test template packs."""

import os
import zipfile
import tempfile
import base64

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import select_tab, select_menu_option, get_clipboard
from vasl_templates.webapp.tests.utils import get_stored_msg, set_stored_msg, dismiss_notifications, find_child

# standard templates
STD_TEMPLATES = {
    "scenario": [ "scenario", "players", "victory_conditions", "ssr" ],
    "ob1": [ "ob_setup_1" ],
}

# nationality-specific templates
NAT_TEMPLATES = {
    "german": [ "pf", "psk", "atmm" ],
    "russian": [ "mol", "mol-p" ],
    "american": [ "baz" ],
    "british": [ "piat" ],
}

# ---------------------------------------------------------------------

def test_individual_files( webapp, webdriver ):
    """Test loading individual template files."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1, template_pack_persistence=1 ) )

    # generate a list of all the templates we need to test
    templates_to_test = set()
    dname = os.path.join( os.path.split(__file__)[0], "../data/default-templates" )
    for fname in os.listdir(dname):
        if os.path.splitext(fname)[1] != ".j2":
            continue
        templates_to_test.add( fname )

    # initialize
    def test_template( template_id ):
        """Test uploading a customized version of the template."""
        # make sure generating a snippet returns something
        dismiss_notifications()
        elem = find_child( "input.generate[data-id='{}']".format( template_id ) )
        elem.click()
        assert get_clipboard() != ""
        # upload a new template
        fname = ("ob_setup" if template_id.startswith("ob_setup_") else template_id) + ".j2"
        set_stored_msg( "template_pack_persistence",
            "{} | {}".format( fname, "UPLOADED TEMPLATE" )
        )
        select_menu_option( "template_pack" )
        # make sure generating a snippet returns the new version
        dismiss_notifications()
        elem = find_child( "input.generate[data-id='{}']".format( template_id ) )
        elem.click()
        assert get_clipboard() == "UPLOADED TEMPLATE"
        templates_to_test.remove( fname )

    # try uploading a customized version of each template
    for tab_id,template_ids in STD_TEMPLATES.items():
        select_tab( tab_id )
        for template_id in template_ids:
            test_template( template_id )

    # try uploading a customized version of each nationality-specific template
    for nat,template_ids in NAT_TEMPLATES.items():
        select_tab( "scenario" )
        sel = Select( find_child( "select[name='PLAYER_1']" ) )
        sel.select_by_value( nat )
        select_tab( "ob1" )
        for template_id in template_ids:
            test_template(template_id )

    # make sure we tested everything
    assert not templates_to_test

    # try uploading a template with an incorrect filename extension
    set_stored_msg( "template_pack_persistence",
        "filename.xyz | UPLOADED TEMPLATE"
    )
    select_menu_option( "template_pack" )
    last_error_msg = get_stored_msg("_last-error_" )
    assert "Invalid template extension" in last_error_msg

    # try uploading a template with an unknown filename
    set_stored_msg( "template_pack_persistence",
        "unknown.j2 | UPLOADED TEMPLATE"
    )
    select_menu_option( "template_pack" )
    last_error_msg = get_stored_msg("_last-error_" )
    assert "Invalid template filename" in last_error_msg

# ---------------------------------------------------------------------

def test_zip_files( webapp, webdriver ):
    """Test loading ZIP'ed template packs."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1, template_pack_persistence=1 ) )

    # upload a template pack that contains a full set of templates
    zip_data = _make_zip_from_files( "full" )
    _upload_template_pack( zip_data )
    assert get_stored_msg("_last-error_") is None

    # check that the uploaded templates are being used
    _check_snippets(
        lambda tid: "Customized {}.".format(
            "OB_SETUP" if tid.startswith("ob_setup_") else tid.upper()
        )
    )

    # upload only part of template pack
    _upload_template_pack( zip_data[ : int(len(zip_data)/2) ] )
    assert get_stored_msg("_last-error_").startswith( "Can't unpack the ZIP:" )

    # try uploading an empty template pack
    _upload_template_pack( b"" )
    assert get_stored_msg("_last-error_").startswith( "Can't unpack the ZIP:" )

    # NOTE: We can't test the limit on template pack size, since it happens after the browser's
    # "open file" dialog has finished, but before we read the file data (i.e. we don't execute
    # that bit of code since we're using the "template_pack_persistence" hack).

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_autoload_template_pack( webapp, webdriver ):
    """Test auto-loading template packs."""

    # configure the autoload template pack
    dname = os.path.join( os.path.split(__file__)[0], "fixtures/template-packs/autoload/" )
    from vasl_templates.webapp import generate
    generate.autoload_template_pack = dname

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # check that the autoload'ed templates are being used
    _check_snippets(
        lambda tid: "Autoload'ed {}.".format(
            "OB_SETUP" if tid.startswith("ob_setup_") else tid.upper()
        )
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _check_snippets( func ):
    """Check that snippets are being generated as expected."""
    for tab_id,template_ids in STD_TEMPLATES.items():
        select_tab( tab_id )
        for template_id in template_ids:
            dismiss_notifications()
            elem = find_child( "input.generate[data-id='{}']".format( template_id ) )
            elem.click()
            assert get_clipboard() == func(template_id)
    for nat,template_ids in NAT_TEMPLATES.items():
        select_tab( "scenario" )
        sel = Select( find_child( "select[name='PLAYER_1']" ) )
        sel.select_by_value( nat )
        select_tab( "ob1" )
        for template_id in template_ids:
            dismiss_notifications()
            elem = find_child( "input.generate[data-id='{}']".format( template_id ) )
            elem.click()
            assert get_clipboard() == func(template_id)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _make_zip( files ):
    """Generate a ZIP file."""
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.close()
        with zipfile.ZipFile( temp_file.name, "w" ) as zip_file:
            for fname,fdata in files.items():
                zip_file.writestr( fname, fdata )
        return open( temp_file.name, "rb" ).read()

def _make_zip_from_files( dname ):
    """Generate a ZIP file from files in a directory."""
    files = {}
    dname = os.path.join( os.path.split(__file__)[0], "fixtures/template-packs/"+dname )
    for root,_,fnames in os.walk(dname):
        for fname in fnames:
            fname = os.path.join( root, fname )
            assert fname.startswith( dname )
            fname2 = fname[len(dname)+1:]
            with open( fname, "r" ) as fp:
                files[fname2] = fp.read()
    return _make_zip( files )

def _upload_template_pack( zip_data ):
    """Upload a template pack."""
    set_stored_msg( "template_pack_persistence",
        "{} | {}".format( "test.zip", base64.b64encode(zip_data).decode("ascii") )
    )
    select_menu_option( "template_pack" )
