import streamlit as st
import requests

# Set page config for a wider layout and custom title
st.set_page_config(page_title="SmartBrief AI", page_icon="🧠", layout="centered")

st.title("SmartBrief AI 🧠")
st.write("Your Personalized Daily Knowledge Digest")
st.divider()

# Define the backend URL (make sure Uvicorn is running!)
API_URL = "http://127.0.0.1:8000"

# Create the three main navigation tabs
tab1, tab2, tab3 = st.tabs(["🗞️ Live News Feed", "📬 Subscribe", "⚙️ Manage Profile"])

# ==========================================
# TAB 1: LIVE NEWS FEED (READ)
# ==========================================
with tab1:
    st.header("Browse Top Headlines")
    # Categories align with GNews/RSS supported topics
    category = st.selectbox(
        "Choose Category",
        ["technology", "business", "sports", "health", "entertainment"]
    )

    if st.button("Get News"):
        with st.spinner(f"Fetching and summarizing {category} news..."):
            try:
                response = requests.get(f"{API_URL}/news?category={category}")
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    
                    if not articles:
                        st.warning("No articles found for this category today.")
                    
                    for article in articles:
                        st.subheader(article["title"])
                        st.write(article["summary"])
                        st.markdown(f"[Read Full Article]({article['url']})")
                        st.divider()
                else:
                    st.error("Failed to fetch news from the backend.")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend. Is your Uvicorn server running?")

# ==========================================
# TAB 2: SUBSCRIBE (CREATE)
# ==========================================
with tab2:
    st.header("Automate Your Reading")
    st.write("Register to receive a customized daily email digest based on your interests.")
    
    with st.form("registration_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        interests = st.text_input("Your Interests (e.g., ai, startups, cricket)")
        
        submitted = st.form_submit_button("Subscribe Now")
        
        if submitted:
            if name and email and interests:
                payload = {
                    "name": name,
                    "email": email,
                    "interests": interests
                }
                try:
                    response = requests.post(f"{API_URL}/users/", json=payload)
                    if response.status_code == 200:
                        st.success(f"Welcome aboard, {name}! Your preferences have been saved.")
                        st.balloons() # Add a little flair for successful registration!
                    elif response.status_code == 400:
                        st.warning("This email is already registered!")
                    else:
                        st.error("Something went wrong on the server.")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to the backend. Is your Uvicorn server running?")
            else:
                st.error("Please fill out all fields before submitting.")

# ==========================================
# TAB 3: MANAGE PROFILE (UPDATE & DELETE)
# ==========================================
with tab3:
    st.header("Manage Your Subscription")
    st.write("View your profile, update your specific interests, or unsubscribe.")
    
    # Step 1: Fetch the user profile
    manage_email = st.text_input("Enter your registered email to load profile:")
    
    if st.button("Load Profile"):
        try:
            response = requests.get(f"{API_URL}/users/{manage_email}")
            if response.status_code == 200:
                st.session_state['current_user'] = response.json()
                st.success("Profile loaded successfully!")
            elif response.status_code == 404:
                st.error("No account found with that email address.")
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the backend. Is your Uvicorn server running?")

    # Step 2: Display Update and Delete options IF a profile is loaded in session state
    if 'current_user' in st.session_state:
        user_data = st.session_state['current_user']
        
        st.divider()
        st.subheader(f"Welcome back, {user_data['name']}")
        
        # --- Update Form ---
        with st.form("update_form"):
            new_interests = st.text_input("Update Your Interests", value=user_data['interests'])
            submitted_update = st.form_submit_button("Save New Interests")
            
            if submitted_update:
                try:
                    payload = {"interests": new_interests}
                    res = requests.put(f"{API_URL}/users/{user_data['email']}", json=payload)
                    if res.status_code == 200:
                        st.success("Interests updated successfully! Your next digest will reflect these changes.")
                        st.session_state['current_user']['interests'] = new_interests
                    else:
                        st.error("Failed to update interests.")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()
        
        # --- Delete/Unsubscribe Action ---
        st.write("### Danger Zone")
        st.warning("Unsubscribing will permanently delete your profile and stop all future automated emails.")
        
        if st.button("Unsubscribe (Delete Account)", type="primary"):
            try:
                res = requests.delete(f"{API_URL}/users/{user_data['email']}")
                if res.status_code == 200:
                    st.success("You have been successfully unsubscribed. We're sad to see you go!")
                    # Clear the screen by removing the user from session state
                    del st.session_state['current_user']
                    st.rerun() # Refresh the UI instantly
                else:
                    st.error("Failed to delete account.")
            except Exception as e:
                st.error(f"Error: {e}")