import streamlit as st
import requests

st.title("SmartBrief AI")

category = st.selectbox(
    "Choose Category",
    ["technology", "business", "sports", "health"]
)

if st.button("Get News"):

    response = requests.get(
        f"http://127.0.0.1:8000/news?category={category}"
    )

    data = response.json()

    articles = data["articles"]

    for article in articles:

        st.subheader(article["title"])

        st.write(article["summary"])

        st.markdown(f"[Read More]({article['url']})")

        st.divider()