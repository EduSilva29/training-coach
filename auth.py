import hmac
from collections.abc import Mapping

import streamlit as st

from config import get_setting


def verify_credentials(username, password, expected_username, expected_password):
    return (
        isinstance(username, str)
        and isinstance(password, str)
        and hmac.compare_digest(username.encode("utf-8"), expected_username.encode("utf-8"))
        and hmac.compare_digest(password.encode("utf-8"), expected_password.encode("utf-8"))
    )


def require_login():
    auth_config = get_setting("auth")
    if not isinstance(auth_config, Mapping):
        st.error("Login is not configured. Add an [auth] section to Streamlit secrets.")
        st.stop()

    expected_username = auth_config.get("username")
    expected_password = auth_config.get("password")
    if not isinstance(expected_username, str) or not expected_username or not isinstance(expected_password, str) or not expected_password:
        st.error("Login is not configured. Set auth.username and auth.password in Streamlit secrets.")
        st.stop()

    if st.session_state.get("authenticated", False):
        return

    st.title("AI Endurance Coach")
    st.subheader("Sign in")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        if verify_credentials(username, password, expected_username, expected_password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect username or password.")
    st.stop()
