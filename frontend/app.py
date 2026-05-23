import streamlit as st
import requests

st.title("SmartBrief AI 🧠")
st.write("Your Personalized Daily Knowledge Digest")

# Create two tabs for a cleaner UI
tab1, tab2 = st.tabs(["🗞️ Live News Feed", "📬 Subscribe to Digest"])

# --- TAB 1: Live News Feed ---
with tab1:
    st.header("Browse Top Headlines")
    category = st.selectbox(
        "Choose Category",
        ["technology", "business", "sports", "health", "science", "entertainment"]
    )

    if st.button("Get News"):
        with st.spinner("Fetching and summarizing articles..."):
            try:
                response = requests.get(f"http://127.0.0.1:8000/news?category={category}")
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    
                    if not articles:
                        st.warning("No articles found for this category today.")
                    
                    for article in articles:
                        st.subheader(article["title"])
                        st.write(article["summary"])
                        st.markdown(f"[Read More]({article['url']})")
                        st.divider()
                else:
                    st.error("Failed to fetch news from the backend.")
            except Exception as e:
                st.error(f"Could not connect to the backend API: {e}")

# --- TAB 2: User Registration Form ---
with tab2:
    st.header("Automate Your Reading")
    st.write("Register to receive a customized daily email digest based on your interests.")
    
    with st.form("registration_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        interests = st.text_input("Your Interests (e.g., ai, finance, startups)")
        
        submitted = st.form_submit_button("Subscribe")
        
        if submitted:
            if name and email and interests:
                # Prepare the payload to match your Pydantic schema
                payload = {
                    "name": name,
                    "email": email,
                    "interests": interests
                }
                
                try:
                    response = requests.post("http://127.0.0.1:8000/users/", json=payload)
                    
                    if response.status_code == 200:
                        st.success(f"Welcome aboard, {name}! Your preferences have been saved.")
                    elif response.status_code == 400:
                        st.warning("This email is already registered!")
                    else:
                        st.error("Something went wrong on the server.")
                except Exception as e:
                    st.error(f"Could not connect to the backend API: {e}")
            else:
                st.error("Please fill out all fields before submitting.")