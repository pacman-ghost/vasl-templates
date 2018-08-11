"""Test template packs."""

import os
import zipfile
import tempfile
import base64

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp import snippets
from vasl_templates.webapp.tests.utils import \
    select_tab, select_menu_option, dismiss_notifications, get_clipboard, \
    get_stored_msg, set_stored_msg, add_simple_note, for_each_template, find_child, find_children

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
        elem, clipboard = _generate_snippet( template_id, orig_template_id )
        assert clipboard != ""
        # upload a new template
        fname = template_id + ".j2"
        set_stored_msg( "template_pack_persistence",
            "{} | {}".format( fname, "UPLOADED TEMPLATE" )
        )
        select_menu_option( "template_pack" )
        # make sure generating a snippet returns the new version
        dismiss_notifications()
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
    _check_snippets( lambda tid: "Customized {}.".format( tid.upper() ) )

    # upload only part of template pack
    _upload_template_pack( zip_data[ : int(len(zip_data)/2) ] )
    assert get_stored_msg("_last-error_").startswith( "Can't unpack the ZIP:" )

    # try uploading an empty template pack
    _upload_template_pack( b"" )
    assert get_stored_msg("_last-error_").startswith( "Can't unpack the ZIP:" )

    # NOTE: We can't test the limit on template pack size, since it happens after the browser's
    # "open file" dialog has finished, but before we read the file data (i.e. we don't execute
    # that bit of code since we're using the "template_pack_persistence" hack).

# ---------------------------------------------------------------------

def test_new_default_template_pack( webapp, webdriver, monkeypatch ):
    """Test changing the default template pack."""

    # configure a new default template pack
    dname = os.path.join( os.path.split(__file__)[0], "fixtures/template-packs/new-default/" )
    monkeypatch.setattr( snippets, "default_template_pack", dname )

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # check that the new templates are being used
    _check_snippets( lambda tid: "New default {}.".format( tid.upper() ) )

# ---------------------------------------------------------------------

def test_nationality_data( webapp, webdriver ):
    """Test a template pack with nationality data."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1, template_pack_persistence=1 ) )
    select_tab( "scenario" )

    # select the British as player 1
    player1_sel = Select( find_child( "select[name='PLAYER_1']" ) )
    player1_sel.select_by_value( "british" )
    tab_ob1 = find_child( "a[href='#tabs-ob1']" )
    assert tab_ob1.text.strip() == "British OB"
    assert player1_sel.first_selected_option.text == "British"
    players = [ o.text for o in player1_sel.options ]

    # upload a template pack that contains nationality data
    zip_data = _make_zip_from_files( "with-nationality-data" )
    _upload_template_pack( zip_data )
    assert get_stored_msg("_last-error_") is None

    # check that the UI was updated correctly
    assert tab_ob1.text.strip() == "Poms! OB"
    assert player1_sel.first_selected_option.text == "Poms!"

    # check that there is a new Korean player
    players2 = [ o.text for o in player1_sel.options ]
    players2.remove( "Korean" )
    players2 = [ "British" if o == "Poms!" else o for o in players2 ]
    assert players2 == players

# ---------------------------------------------------------------------

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

# ---------------------------------------------------------------------

def _check_snippets( expected ):
    """Check that snippets are being generated as expected."""

    def test_template( template_id, orig_template_id ):
        """Test each template."""
        dismiss_notifications()
        _, clipboard = _generate_snippet( template_id, orig_template_id )
        assert clipboard == expected( template_id )
    for_each_template( test_template )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _generate_snippet( template_id, orig_template_id ):
    """Generate a snippet for the specified template."""

    if template_id == "scenario_note":
        # create a scenario note and generate a snippet for it
        sortable = find_child( "#scenario_notes-sortable" )
        add_simple_note( sortable, "test scenario note", None )
        elems = find_children( "li img.snippet", sortable )
        elem = elems[0]
    elif template_id in ("ob_setup","ob_note"):
        # create a OB setup/note and generate a snippet for it
        select_tab( "ob1" )
        sortable = find_child( "#{}s-sortable_1".format( template_id ) )
        add_simple_note( sortable, "test {}".format(template_id), None )
        elems = find_children( "#{}s-sortable_1 li img.snippet".format( template_id ) )
        elem = elems[0]
    else:
        # generate a snippet for the specified template
        elem = find_child( "button.generate[data-id='{}']".format( orig_template_id ) )
    elem.click()
    return elem, get_clipboard()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _upload_template_pack( zip_data ):
    """Upload a template pack."""
    set_stored_msg( "template_pack_persistence",
        "{} | {}".format( "test.zip", base64.b64encode(zip_data).decode("ascii") )
    )
    select_menu_option( "template_pack" )
