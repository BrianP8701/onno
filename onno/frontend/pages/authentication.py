import streamlit as st
from onno.frontend.utils.user_utils import initialize_user_info

class Authentication:
    def __init__(self):
        pass
    
    def display(self):
        login_tab, signup_tab = st.tabs(
            ["Log In", "Sign Up"]
        )
        with login_tab:
            st.title("Login")
            username = st.text_input("Username", key='login_username')
            password = st.text_input("Password", key='login_password', type="password")
            if st.button("Login"):
                if st.session_state['DATABASE'].check_username_exists(username):
                    hashed_password = st.session_state['DATABASE'].get_password(username)
                    if hashed_password and st.session_state['DATABASE'].check_password(password, hashed_password):
                        st.success("Logged In as {}".format(username))
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username
                        st.session_state['user_info'] = st.session_state['DATABASE'].retrieve_user_info(username)
                        st.rerun()
                    else:
                        st.error(f"Incorrect Password: {str(st.session_state['DATABASE'].hash_password(password))} != {st.session_state['DATABASE'].get_password(username)}")
                else:
                    st.error("Username does not exist")

        with signup_tab:
            st.title("Sign Up")
            username = st.text_input("Username", key='signup_username')
            password = st.text_input("Password", key='signup_password', type="password")
            email = st.text_input("Email")
            if st.button("Sign Up"):
                if st.session_state['DATABASE'].check_username_exists(username):
                    st.error("Username already exists")
                else:
                    user_info = initialize_user_info(username, st.session_state['DATABASE'].hash_password(password), email)
                    st.success("Signed up as {}".format(username))
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['user_info'] = user_info
                    st.rerun()
