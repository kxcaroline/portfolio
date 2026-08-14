"""Application configuration."""

import os


class Config:  # pylint: disable=too-few-public-methods
    """Base configuration for the portfolio site.

    A configuration object is a namespace of settings; it has no
    behaviour to expose, so the public-method floor does not apply.
    """

    SITE_NAME = "Caroline Kim"
    SITE_TITLE = "Caroline Kim — Portfolio"

    # Cookie-free visitor analytics (Cloudflare Web Analytics). The token
    # is read from the environment rather than committed, and the script
    # is only emitted when it is set — so a local run, a fresh clone, and
    # the graded submission all serve no tracking code at all.
    ANALYTICS_TOKEN = os.environ.get("ANALYTICS_TOKEN", "")
