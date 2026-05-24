import streamlit as st
import requests

st.set_page_config(page_title="SmartBrief AI", page_icon="🧠", layout="centered")

API_URL = "http://127.0.0.1:8000"

# Helper function to easily attach the JWT badge to requests
def get_auth_headers():
    if 'token' in st.session_state:
        return {"Authorization": f"Bearer {st.session_state['token']}"}
    return {}

# ==========================================
# AUTHENTICATION GATEWAY (Modern UI)
# ==========================================
if 'token' not in st.session_state:
    # Use columns to create a centered box (1 part empty, 2 parts form, 1 part empty)
    col1, center_col, col3 = st.columns([1, 2, 1])
    
    with center_col:
        st.title("SmartBrief AI 🧠")
        st.write("Your Personalized Daily Knowledge Digest")
        st.divider()
        
        # Toggle between Login and Signup
        auth_mode = st.radio("Select an option:", ["Log In", "Sign Up"], horizontal=True)
        
        if auth_mode == "Log In":
            with st.form("login_form"):
                st.subheader("Welcome Back")
                login_email = st.text_input("Email")
                login_password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
                
                if submitted:
                    try:
                        res = requests.post(f"{API_URL}/login", json={"email": login_email, "password": login_password})
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state['token'] = data['access_token']
                            st.session_state['current_user'] = data['user']
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                    except Exception:
                        st.error("Could not connect to the server.")
                        
        else: # Sign Up Mode
            with st.form("registration_form"):
                st.subheader("Create an Account")
                name = st.text_input("Full Name")
                email = st.text_input("Email Address")
                password = st.text_input("Create a Password", type="password")
                interests = st.text_input("Your Interests (e.g., ai, startups, sports)")
                submitted = st.form_submit_button("Subscribe Now", type="primary", use_container_width=True)
                
                if submitted:
                    if name and email and interests and password:
                        payload = {"name": name, "email": email, "password": password, "interests": interests}
                        try:
                            response = requests.post(f"{API_URL}/users/", json=payload)
                            if response.status_code == 200:
                                st.success("Registered successfully! Please switch to 'Log In' above.")
                                st.balloons()
                            elif response.status_code == 400:
                                st.warning("This email is already registered! Please log in.")
                        except Exception:
                            st.error("Connection error.")
                    else:
                        st.error("Please fill out all fields.")

else:
    # ==========================================
    # LOGGED IN VIEW 
    # ==========================================
    
    # 1. Sidebar Logic (Logout only)
    with st.sidebar:
        st.success(f"Logged in as {st.session_state['current_user']['name']}")
        if st.button("Log Out"):
            del st.session_state['token']
            del st.session_state['current_user']
            st.rerun()

    # 2. Main Page Logic (Dashboard and Profile)
    user_data = st.session_state['current_user']
    tab1, tab2 = st.tabs(["🗞️ Dashboard", "⚙️ Manage Profile"])

    with tab1:
        st.header(f"Welcome back, {user_data['name']}! 🚀")
        st.caption(f"Curating live articles for: **{user_data['interests']}**")
        
        if st.button("Refresh Feed", type="primary"):
            with st.spinner("Summarizing your personalized articles..."):
                news_res = requests.get(f"{API_URL}/news?category={user_data['interests']}")
                if news_res.status_code == 200:
                    articles = news_res.json().get("articles", [])
                    for article in articles:
                        st.subheader(article["title"])
                        st.write(article["summary"])
                        st.markdown(f"[Read Full Article]({article['url']})")
                        st.divider()
                else:
                    st.error("Failed to generate feed.")

    with tab2:
        st.header("Manage Your Subscription")
        with st.form("update_form"):
            new_interests = st.text_input("Update Your Interests", value=user_data['interests'])
            submitted_update = st.form_submit_button("Save New Interests")
            
            if submitted_update:
                try:
                    res = requests.put(f"{API_URL}/users/me", json={"interests": new_interests}, headers=get_auth_headers())
                    if res.status_code == 200:
                        st.success("Interests updated!")
                        st.session_state['current_user']['interests'] = new_interests
                    else:
                        st.error("Failed to update interests.")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()
        st.warning("Danger Zone")
        if st.button("Unsubscribe (Delete Account)"):
            try:
                res = requests.delete(f"{API_URL}/users/me", headers=get_auth_headers())
                if res.status_code == 200:
                    st.success("Unsubscribed successfully.")
                    del st.session_state['token']
                    del st.session_state['current_user']
                    st.rerun()
            except Exception as e:
                st.error("Error deleting account.")