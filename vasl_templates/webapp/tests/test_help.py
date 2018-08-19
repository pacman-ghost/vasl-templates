""" Test the help page. """

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_menu_option, find_child, find_children

# ---------------------------------------------------------------------

def test_help( webapp, webdriver ):
    """Test the help page."""

    # initialize
    init_webapp( webapp, webdriver )

    # make sure the HELP tab is not visible
    def get_tabs():
        """Get the visible tabs."""
        return [
            c.get_attribute( "aria-controls" )
            for c in find_children( "#tabs .ui-tabs-tab" )
            if c.is_displayed()
        ]
    assert "tabs-help" not in get_tabs()

    # show the help
    select_menu_option( "show_help" )
    webdriver.switch_to.frame( find_child( "#tabs-help iframe" ) )
    assert "This is the help page." in webdriver.page_source
    webdriver.switch_to.default_content()

    # make sure that the HELP tab is now visible
    assert "tabs-help" in get_tabs()
