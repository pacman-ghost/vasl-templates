"""Test utility functions."""

from vasl_templates.webapp.utils import friendly_fractions

# ---------------------------------------------------------------------

def test_friendly_fractions():
    """Test generating friendly fractions."""

    def do_test( val, expected, singular=False ): #pylint: disable=missing-docstring
        # test without a postfix
        assert friendly_fractions( val ) == expected
        # test the singular/plural postfixes
        expected = expected+" foo" if singular else expected+" foos"
        assert friendly_fractions( val, "foo", "foos" ) == expected

    # do the test
    do_test( 0, "0" )
    do_test( 0.124, "0" )
    do_test( 0.125, "&frac14;", singular=True )
    do_test( 0.374, "&frac14;", singular=True )
    do_test( 0.375, "&frac12;", singular=True )
    do_test( 0.624, "&frac12;", singular=True )
    do_test( 0.625, "&frac34;", singular=True )
    do_test( 0.874, "&frac34;", singular=True )
    do_test( 0.875, "1", singular=True )
    do_test( 1.124, "1", singular=True )
    do_test( 1.125, "1&frac14;" )
    do_test( 1.374, "1&frac14;" )
    do_test( 1.375, "1&frac12;" )
    do_test( 1.624, "1&frac12;" )
    do_test( 1.625, "1&frac34;" )
    do_test( 1.874, "1&frac34;" )
    do_test( 1.875, "2" )
    do_test( 2.125, "2&frac14;" )
    do_test( 2.5, "2&frac12;" )
    do_test( 2.75, "2&frac34;" )
