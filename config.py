import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def get_setting(name, default=None):
    """Read configuration from the environment first, then Streamlit secrets."""
    value = os.getenv(name)
    if value is not None:
        return value

    try:
        return st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default
