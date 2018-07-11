""" Test how players are handled. """

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import get_nationalities, find_child

# ---------------------------------------------------------------------

def _get_player( webdriver, player_id ):
    """Get the nationality of the specified player."""
    sel = Select(
        find_child( webdriver, "select[name='player_{}']".format( player_id ) )
    )
    return sel.first_selected_option.get_attribute( "value" )

# ---------------------------------------------------------------------

def test_player_change( webapp, webdriver ):
    """Test changing players."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )
    nationalities = get_nationalities( webapp )

    # make sure that the UI was updated correctly for the initial players
    for player_no in [1,2]:
        player_id = _get_player( webdriver, player_no )
        elem = find_child( webdriver, "#tabs .ui-tabs-nav a[href='#tabs-ob{}']".format( player_no ) )
        assert elem.text.strip() == "{} OB".format( nationalities[player_id]["display_name"] )

    # change player 1
    sel = Select(
        find_child( webdriver, "select[name='player_1']" )
    )
    sel.select_by_value( "finnish" )
    elem = find_child( webdriver, "#tabs .ui-tabs-nav a[href='#tabs-ob1']" )
    assert elem.text.strip() == "{} OB".format( nationalities["finnish"]["display_name"] )

    # change player 2
    sel = Select(
        find_child( webdriver, "select[name='player_2']" )
    )
    sel.select_by_value( "japanese" )
    elem = find_child( webdriver, "#tabs .ui-tabs-nav a[href='#tabs-ob2']" )
    assert elem.text.strip() == "{} OB".format( nationalities["japanese"]["display_name"] )
