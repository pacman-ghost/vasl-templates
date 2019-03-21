""" Global variables. """

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import APP_NAME, APP_VERSION

template_pack = None
vasl_mod = None
vo_listings = None
vo_notes = None
vo_notes_file_server = None

cleanup_handlers = []

# ---------------------------------------------------------------------

@app.context_processor
def inject_template_params():
    """Inject template parameters into Jinja2."""
    return {
        "APP_NAME": APP_NAME,
        "APP_VERSION": APP_VERSION,
    }
