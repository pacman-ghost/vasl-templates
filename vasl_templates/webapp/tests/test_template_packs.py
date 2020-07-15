"""Test template packs."""

import os
import zipfile
import base64
import re
import random

import pytest

from vasl_templates.webapp.utils import TempFile
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo
from vasl_templates.webapp.tests.utils import \
    select_tab, select_menu_option, set_player, \
    wait_for_clipboard, get_stored_msg, set_stored_msg, set_stored_msg_marker,\
    add_simple_note, for_each_template, find_child, find_children, wait_for, \
    get_droplist_vals_index, init_webapp, get_css_classes

# ---------------------------------------------------------------------

def test_individual_files( webapp, webdriver ):
    """Test loading individual template files."""

    # initialize
    init_webapp( webapp, webdriver, template_pack_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )
    set_player( 1, "german" )
    set_player( 2, "russian" )

    # try uploading a customized version of each template
    def test_template( template_id, orig_template_id ):
        """Test uploading a customized version of the template."""
        # upload a new template
        _ = upload_template_pack_file( template_id+".j2", "UPLOADED TEMPLATE", False )
        # make sure generating a snippet returns the new version
        _ = _generate_snippet( webdriver, template_id, orig_template_id )
        wait_for_clipboard( 2, "UPLOADED TEMPLATE" )
    for_each_template( test_template )

    # try uploading a template with an incorrect filename extension
    _ = upload_template_pack_file( "filename.xyz", "UPLOADED TEMPLATE", True )
    assert "Invalid template extension" in get_stored_msg( "_last-error_" )

    # try uploading a template with an unknown filename
    _ = upload_template_pack_file( "unknown.j2", "UPLOADED TEMPLATE", True )
    assert "Invalid template filename" in get_stored_msg( "_last-error_" )

# ---------------------------------------------------------------------

def test_zip_files( webapp, webdriver ):
    """Test loading ZIP'ed template packs."""

    # initialize
    init_webapp( webapp, webdriver, template_pack_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )
    set_player( 1, "german" )
    set_player( 2, "russian" )

    # upload a template pack that contains a full set of templates
    zip_data = make_zip_from_files( "full" )
    _, marker = upload_template_pack_zip( zip_data, False )
    assert get_stored_msg( "_last-error_" ) == marker

    # check that the uploaded templates are being used
    _check_snippets( webdriver, lambda tid: "Customized {}.".format( tid.upper() ) )

    # upload only part of template pack
    _ = upload_template_pack_zip(
        zip_data[ : int(len(zip_data)/2) ],
        True
    )
    assert get_stored_msg( "_last-error_" ).startswith( "Can't unpack the ZIP:" )

    # try uploading an empty template pack
    _ = upload_template_pack_zip( b"", True )
    assert get_stored_msg( "_last-error_" ).startswith( "Can't unpack the ZIP:" )

    # NOTE: We can't test the limit on template pack size, since it happens after the browser's
    # "open file" dialog has finished, but before we read the file data (i.e. we don't execute
    # that bit of code since we're using the "template_pack_persistence" hack).

# ---------------------------------------------------------------------

def test_new_default_template_pack( webapp, webdriver ):
    """Test changing the default template pack."""

    # initialize
    init_webapp( webapp, webdriver,
        reset = lambda ct:
            ct.set_default_template_pack( dname="template-packs/new-default/" ) \
              .set_vo_notes_dir( dtype="test" )
    )
    set_player( 1, "german" )
    set_player( 2, "russian" )

    # check that the new templates are being used
    _check_snippets( webdriver, lambda tid: "New default {}.".format( tid.upper() ) )

# ---------------------------------------------------------------------

def test_nationality_data( webapp, webdriver ):
    """Test a template pack with nationality data."""

    # initialize
    init_webapp( webapp, webdriver, template_pack_persistence=1 )

    # select the British as player 1
    player1_sel = set_player( 1, "british" )
    tab_ob1 = find_child( "a[href='#tabs-ob1']" )
    assert tab_ob1.text.strip() == "British OB"
    # FUDGE!  player1_sel.first_selected_option.text doesn't contain the right value
    # if we're using jQuery selectmenu's :-/
    assert player1_sel.first_selected_option.get_attribute( "value" ) == "british"
    droplist_vals = get_droplist_vals_index( player1_sel )
    assert droplist_vals["british"] == "British"

    # upload a template pack that contains nationality data
    zip_data = make_zip_from_files( "with-nationality-data" )
    _, marker = upload_template_pack_zip( zip_data, False )
    assert get_stored_msg( "_last-error_" ) == marker

    # check that the UI was updated correctly
    assert tab_ob1.text.strip() == "Poms! OB"
    assert player1_sel.first_selected_option.get_attribute( "value" ) == "british"
    droplist_vals2 = get_droplist_vals_index( player1_sel )
    assert droplist_vals2["british"] == "Poms!"

    # check that there is a new Korean player
    del droplist_vals2["korean"]
    droplist_vals2 = {
        k: "British" if v == "Poms!" else v
        for k,v in droplist_vals2.items()
    }
    assert droplist_vals2 == droplist_vals

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest.config.option.short_tests, reason="--short-tests specified" ) #pylint: disable=no-member
def test_missing_templates( webapp, webdriver ):
    """Test UI updates for missing templates."""

    # initialize
    init_webapp( webapp, webdriver, template_pack_persistence=1 )

    # get the files in the default template pack
    files = {}
    dname = os.path.normpath( os.path.join( os.path.split(__file__)[0], "../data/default-template-pack" ) )
    for root,_,fnames in os.walk( dname ):
        for fname in fnames:
            if os.path.splitext( fname )[1] == ".swp":
                continue
            fname = os.path.join( root, fname )
            fname2 = os.path.relpath( fname, start=dname )
            if fname2.startswith( "extras/" ):
                continue
            if fname2 == "ob_vo":
                fname2 = random.choice( [ "ob_vehicles", "ob_ordnance" ] )
            elif fname2 == "ob_vo_note":
                fname2 = random.choice( [ "ob_vehicles_note", "ob_ordnance_note" ] )
            elif fname2 == "ob_ma_note":
                fname2 = random.choice( [ "ob_vehicles_ma_note", "ob_ordnance_ma_note" ] )
            files[ fname2 ] = "dummy template" # nb: we don't care about the content

    def adjust_template_id( template_id ): #pylint: disable=missing-docstring
        if re.search( r"^ob_(vehicles|ordnance)_\d$", template_id ):
            return "ob_vo"
        elif re.search(  r"^ob_(vehicle|ordnance)_note_\d$", template_id ):
            return "ob_vo_note"
        elif re.search( r"^ob_(vehicles|ordnance)_ma_notes_\d$", template_id ):
            return "ob_ma_notes"
        else:
            return template_id

    # upload the template pack, with one file missing each time
    for fname in files:

        # generate and upload the modified template pack
        zip_data = _make_zip(
            { k: v for k,v in files.items() if k != fname }
        )
        upload_template_pack_zip( zip_data, False )

        # check the state of each button (everything should be enabled, except for the one
        # corresponding to the template file we excluded from the upload)
        def check_buttons( sel, is_snippet_control ): #pylint: disable=missing-docstring
            for btn in find_children( sel ):
                # check the UI state of the next button
                template_id = adjust_template_id( btn.get_attribute( "data-id" ) )
                if fname == "national-capabilities.json":
                    expected = False # nb: this is the JSON file, not the template file, and so doesn't effect buttons
                elif fname == "nat_caps.j2":
                    expected = template_id.startswith( "nat_caps_" )
                else:
                    expected = os.path.splitext( fname )[0] == template_id
                disabled = webdriver.execute_script( "return $(arguments[0]).button('option','disabled')", btn )
                assert expected == disabled
                # check that snippet control groups have been enabled/disabled correctly
                parent = btn.find_element_by_xpath( ".." )
                parent_classes = get_css_classes( parent )
                if is_snippet_control:
                    assert "snippet-control" in parent_classes
                    elem = find_child( ".ui-selectmenu-button", parent )
                    elem_classes = get_css_classes( elem )
                    if expected:
                        assert "ui-selectmenu-disabled" in elem_classes
                    else:
                        assert "ui-selectmenu-disabled" not in elem_classes
                else:
                    assert "snippet-control" not in parent_classes
        check_buttons( "button.generate", True )
        check_buttons( "button.edit-template", False )

        # NOTE: We should really check that the "generate snippet" buttons don't appear in sortable entries,
        # but that's more trouble than it's worth - templates such as ob_setup and ob_vehicles are never
        # going to be missing, since the program becomes kinda pointless if they're not there :-/

# ---------------------------------------------------------------------

def _make_zip( files ):
    """Generate a ZIP file."""
    with TempFile() as temp_file:
        temp_file.close()
        with zipfile.ZipFile( temp_file.name, "w" ) as zip_file:
            for fname,fdata in files.items():
                zip_file.writestr( fname, fdata )
        return open( temp_file.name, "rb" ).read()

def make_zip_from_files( dname ):
    """Generate a ZIP file from files in a directory."""
    files = {}
    dname = os.path.join( os.path.split(__file__)[0], "fixtures/template-packs/"+dname )
    assert os.path.isdir( dname )
    for root,_,fnames in os.walk(dname):
        for fname in fnames:
            fname = os.path.join( root, fname )
            assert fname.startswith( dname )
            fname2 = fname[len(dname)+1:]
            with open( fname, "r" ) as fp:
                files[fname2] = fp.read()
    return _make_zip( files )

# ---------------------------------------------------------------------

def _check_snippets( webdriver, expected ):
    """Check that snippets are being generated as expected."""

    def test_template( template_id, orig_template_id ):
        """Test each template."""
        _ = _generate_snippet( webdriver, template_id, orig_template_id )
        wait_for_clipboard( 2, expected(template_id) )
    for_each_template( test_template )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _generate_snippet( webdriver, template_id, orig_template_id ):
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
    elif template_id in ("ob_vehicle_note","ob_ordnance_note"):
        # create a vehicle/ordnance and generate a snippet for its note
        mo = re.search( r"^ob_([a-z]+)_note_(\d)$", orig_template_id )
        vo_type, player_no = mo.group(1), int(mo.group(2))
        vo_type0 = "vehicles" if vo_type == "vehicle" else vo_type
        player_nat = "german" if player_no == 1 else "russian"
        sortable = find_child( "#ob_{}-sortable_{}".format( vo_type0, player_no ) )
        add_vo( webdriver, vo_type0, player_no, "a {} {}".format(player_nat,vo_type) )
        elems = find_children( "li img.snippet", sortable )
        elem = elems[0]
    else:
        # generate a snippet for the specified template
        elem = find_child( "button.generate[data-id='{}']".format( orig_template_id ) )
    elem.click()
    return elem

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def upload_template_pack_zip( zip_data, error_expected ):
    """Upload a template pack ZIP."""
    return _do_upload_template_pack(
        "{} | {}".format(
            "test.zip",
            base64.b64encode( zip_data ).decode( "ascii" )
        ),
        error_expected
    )

def upload_template_pack_file( fname, data, error_expected ):
    """Upload a template pack file."""
    return _do_upload_template_pack(
        "{} | {}".format( fname, data ),
        error_expected
    )

def _do_upload_template_pack( data, error_expected ):
    """Upload a template pack."""

    # upload the template pack
    set_stored_msg( "_template-pack-persistence_", data )
    info_marker = set_stored_msg_marker( "_last-info_" )
    error_marker = set_stored_msg_marker( "_last-error_" )
    select_menu_option( "template_pack" )

    # wait for the front-end to finish
    if error_expected:
        func = lambda: get_stored_msg("_last-error_") != error_marker
    else:
        func = lambda: "was loaded" in get_stored_msg("_last-info_")
    wait_for( 2, func )

    return info_marker, error_marker
