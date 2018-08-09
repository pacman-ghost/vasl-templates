""" Test how players are handled. """

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import get_nationalities, select_tab, find_child

# ---------------------------------------------------------------------

def test_player_change( webapp, webdriver ):
    """Test changing players."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )
    select_tab( "scenario" )
    nationalities = get_nationalities( webapp )
    player_sel = {
        1: Select( find_child( "select[name='PLAYER_1']" ) ),
        2: Select( find_child( "select[name='PLAYER_2']" ) )
    }
    ob_tabs = {
        1: find_child( "#tabs .ui-tabs-nav a[href='#tabs-ob1']" ),
        2: find_child( "#tabs .ui-tabs-nav a[href='#tabs-ob2']" )
    }

    # make sure that the UI was updated correctly for the initial players
    for player_no in [1,2]:
        player_id = player_sel[player_no].first_selected_option.get_attribute( "value" )
        expected = "{} OB".format( nationalities[player_id]["display_name"] )
        assert ob_tabs[player_no].text.strip() == expected

    # change player 1
    player_sel[1].select_by_value( "finnish" )
    assert ob_tabs[1].text.strip() == "{} OB".format( nationalities["finnish"]["display_name"] )

    # change player 2
    player_sel[2].select_by_value( "japanese" )
    assert ob_tabs[2].text.strip() == "{} OB".format( nationalities["japanese"]["display_name"] )
