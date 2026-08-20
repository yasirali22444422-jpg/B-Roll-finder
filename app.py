import streamlit as st
import requests

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="B-Roll Finder",
    page_icon="🎬",
    layout="wide"
)

# -----------------------------
# TITLE
# -----------------------------
st.title("🎬 B-Roll Finder")
st.write("Search free stock videos from Pexels.")

# -----------------------------
# SEARCH BOX
# -----------------------------
keyword = st.text_input(
    "Enter B-roll keyword",
    placeholder="Example: business meeting"
)

# -----------------------------
# SEARCH BUTTON
# -----------------------------
if st.button("🔍 Search Videos", type="primary"):

    if not keyword.strip():
        st.warning("Please enter a keyword.")
        st.stop()

    # Get API key from Streamlit Secrets
    try:
        api_key = st.secrets["AbqSkVbZko07cGsPYZbQgm7SVvwhKPqqYV8bYZs254tAF5OKHcFBQHQl"]
    except Exception:
        st.error("Pexels API key is missing.")
        st.info(
            "Go to Streamlit → App Settings → Secrets "
            "and add PEXELS_API_KEY."
        )
        st.stop()

    # Pexels API
    url = "https://api.pexels.com/videos/search"

    headers = {
        "Authorization": api_key
    }

    params = {
        "query": keyword.strip(),
        "per_page": 12
    }

    # Request
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )
    except requests.RequestException as e:
        st.error("Could not connect to Pexels.")
        st.write(str(e))
        st.stop()

    # Check response
    if response.status_code != 200:
        st.error(
            f"Pexels API Error: {response.status_code}"
        )
        st.write(response.text)
        st.stop()

    data = response.json()

    videos = data.get("videos", [])

    if not videos:
        st.warning("No videos found.")
        st.stop()

    st.success(
        f"Found {len(videos)} videos for: {keyword}"
    )

    # -----------------------------
    # DISPLAY VIDEOS
    # -----------------------------
    for row_start in range(0, len(videos), 3):

        cols = st.columns(3)

        row_videos = videos[row_start:row_start + 3]

        for col, video in zip(cols, row_videos):

            with col:

                video_files = video.get(
                    "video_files", []
                )

                # Find a reasonable video file
                selected_file = None

                for file in video_files:

                    width = file.get("width", 0)
                    height = file.get("height", 0)

                    if width >= 1280 and height >= 720:
                        selected_file = file
                        break

                # Fallback
                if selected_file is None and video_files:
                    selected_file = video_files[0]

                if selected_file:

                    video_url = selected_file.get("link")

                    st.video(video_url)

                    st.caption(
                        f"🎬 {selected_file.get('width', '?')} × "
                        f"{selected_file.get('height', '?')}"
                    )

                else:
                    st.warning(
                        "No playable video found."
                    )
