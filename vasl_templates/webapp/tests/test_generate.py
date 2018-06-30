""" Test response generation. """

from vasl_templates.webapp.tests.utils import find_child

# ---------------------------------------------------------------------

def test_generate( webapp, webdriver ):
    """Test response generation."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # try saying something
    textbox = find_child( webdriver, "input[type='text']" )
    textbox.clear()
    textbox.send_keys( "Hi, there!" )
    submit = find_child( webdriver, "input[type='submit']" )
    submit.click()
    response = find_child( webdriver, "#response" )
    assert response.text == 'You said: "Hi, there!"'

    # try saying something else
    textbox = find_child( webdriver, "input[type='text']" )
    textbox.clear()
    textbox.send_keys( "Yo mama so big..." )
    submit = find_child( webdriver, "input[type='submit']" )
    submit.click()
    response = find_child( webdriver, "#response" )
    assert response.text == 'You said: "Yo mama so big..."'

    # try saying nothing
    textbox = find_child( webdriver, "input[type='text']" )
    textbox.clear()
    submit = find_child( webdriver, "input[type='submit']" )
    submit.click()
    response = find_child( webdriver, "#response" )
    assert response.text == "You said: nothing!"
