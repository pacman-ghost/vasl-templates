"""Test template packs."""

import os
import zipfile
import tempfile
import base64

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import select_menu_option, get_clipboard
from vasl_templates.webapp.tests.utils import get_stored_msg, set_stored_msg, dismiss_notifications, find_child
from vasl_templates.webapp.tests.utils import for_each_template

# ---------------------------------------------------------------------

def test_individual_files( webapp, webdriver ):
    """Test loading individual template files."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1, template_pack_persistence=1 ) )

    # try uploading a customized version of each template
    def test_template( template_id, orig_template_id ):
        """Test uploading a customized version of the template."""
        # make sure generating a snippet returns something
        dismiss_notifications()
        elem = find_child( "input.generate[data-id='{}']".format( orig_template_id ) )
        elem.click()
        assert get_clipboard() != ""
        # upload a new template
        fname = template_id + ".j2"
        set_stored_msg( "template_pack_persistence",
            "{} | {}".format( fname, "UPLOADED TEMPLATE" )
        )
        select_menu_option( "template_pack" )
        # make sure generating a snippet returns the new version
        dismiss_notifications()
        elem = find_child( "input.generate[data-id='{}']".format( orig_template_id ) )
        elem.click()
        assert get_clipboard() == "UPLOADED TEMPLATE"
    for_each_template( test_template )

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
        lambda tid: "Customized {}.".format( tid.upper() )
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

def test_new_default_template_pack( webapp, webdriver ):
    """Test changing the default template pack."""

    # configure a new default template pack
    dname = os.path.join( os.path.split(__file__)[0], "fixtures/template-packs/new-default/" )
    from vasl_templates.webapp import snippets
    snippets.default_template_pack = dname

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # check that the new templates are being used
    _check_snippets(
        lambda tid: "New default {}.".format( tid.upper() )
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_nationality_data( webapp, webdriver ):
    """Test a template pack with nationality data."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1, template_pack_persistence=1 ) )

    # select the British as player 1
    sel = Select(
        find_child( "select[name='PLAYER_1']" )
    )
    sel.select_by_value( "british" )
    elem = find_child( "a[href='#tabs-ob1']" )
    assert elem.text.strip() == "British OB"
    sel = Select( find_child( "select[name='PLAYER_1']" ) )
    assert sel.first_selected_option.text == "British"
    players = [ o.text for o in sel.options ]

    # upload a template pack that contains nationality data
    zip_data = _make_zip_from_files( "with-nationality-data" )
    _upload_template_pack( zip_data )
    assert get_stored_msg("_last-error_") is None

    # check that the UI was updated correctly
    elem = find_child( "a[href='#tabs-ob1']" )
    assert elem.text.strip() == "Poms! OB"
    elem = find_child( "select[name='PLAYER_1']" )
    assert Select(elem).first_selected_option.text == "Poms!"

    # check that there is a new Korean player
    players2 = [ o.text for o in sel.options ]
    players2.remove( "Korean" )
    players2 = [ "British" if o == "Poms!" else o for o in players2 ]
    assert players2 == players

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _check_snippets( func ):
    """Check that snippets are being generated as expected."""

    def test_template( template_id, orig_template_id ):
        """Test each template."""
        dismiss_notifications()
        elem = find_child( "input.generate[data-id='{}']".format( orig_template_id ) )
        elem.click()
        assert get_clipboard() == func( template_id )
    for_each_template( test_template )

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
