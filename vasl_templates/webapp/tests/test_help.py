""" Test the help page. """

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_menu_option, find_child, find_children, wait_for, wait_for_elem

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

    # make sure that the HELP tab is now visible
    assert "tabs-help" in get_tabs()

    # check what's in the help iframe
    try:

        # switch to the frame
        webdriver.switch_to.frame( find_child( "#tabs-help iframe" ) )

        # check that the content loaded OK
        assert "everyone's favorite scenario" in webdriver.page_source

        # check that the license loaded OK
        elem = wait_for_elem( 2, "a.ui-tabs-anchor[href='#helptabs-license']" )
        assert elem.is_displayed()
        wait_for( 2, lambda: "GNU AFFERO GENERAL PUBLIC LICENSE" in webdriver.page_source )
        assert "Version 3" in webdriver.page_source

    finally:

        # switch back to the main window
        webdriver.switch_to.default_content()
