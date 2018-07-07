""" Test generating OB SETUP snippets. """

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import get_clipboard, find_child

# ---------------------------------------------------------------------

def test_ob_setup( webapp, webdriver ):
    """Test generating OB SETUP snippets."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # initialize
    def select_ob_tab( player_id ):
        """Select the OB tab for the specified player."""
        elem = find_child( webdriver, "#tabs .ui-tabs-nav a[href='#tabs-ob{}']".format( player_id ) )
        elem.click()

    # generate OB SETUP snippets for both players
    select_ob_tab( 1 )
    textarea1 = find_child( webdriver,  "textarea[name='ob_setup_1']" )
    textarea1.clear()
    textarea1.send_keys( "setup here." )
    btn1 = find_child( webdriver, "input[type='button'][data-id='ob_setup_1']" )
    select_ob_tab( 2 )
    textarea2 = find_child( webdriver,  "textarea[name='ob_setup_2']" )
    textarea2.clear()
    textarea2.send_keys( "setup there." )
    btn2 = find_child( webdriver, "input[type='button'][data-id='ob_setup_2']" )
    btn2.click()
    assert get_clipboard().strip() == "[setup there.] (col=[OBCOL:russian/OBCOL2:russian])"
    select_ob_tab( 1 )
    btn1.click()
    assert get_clipboard().strip() == "[setup here.] (col=[OBCOL:german/OBCOL2:german])"

    # change the player nationalities and generate the OB SETUP snippets again
    elem = find_child( webdriver, "#tabs .ui-tabs-nav a[href='#tabs-scenario']" )
    elem.click()
    sel = Select(
        find_child( webdriver, "select[name='player_1']" )
    )
    sel.select_by_value( "british" )
    sel = Select(
        find_child( webdriver, "select[name='player_2']" )
    )
    sel.select_by_value( "french" )
    select_ob_tab( 1 )
    btn1.click()
    assert get_clipboard().strip() == "[setup here.] (col=[OBCOL:british/OBCOL2:british])"
    select_ob_tab( 2 )
    btn2.click()
    assert get_clipboard().strip() == "[setup there.] (col=[OBCOL:french/OBCOL2:french])"
