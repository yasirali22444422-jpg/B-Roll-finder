import streamlit as st

st.set_page_config(
    page_title="B-Roll Finder",
    page_icon="🎬"
)

st.title("🎬 B-Roll Finder")

st.write("Our B-Roll Finder is working!")

keyword = st.text_input("Enter B-roll keyword")

if st.button("Search"):
    st.write("Searching for:", keyword)
