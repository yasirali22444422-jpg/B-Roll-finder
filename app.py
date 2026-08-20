import streamlit as st
import requests
import re
import zipfile
import io
import os

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="B-Roll Finder Pro",
    page_icon="🎬",
    layout="wide"
)

# -----------------------------
# TITLE
# -----------------------------
st.title("🎬 B-Roll Finder Pro")
st.write("Paste your script and get B-roll videos for each scene.")

# -----------------------------
# SIDEBAR - API KEY
# -----------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input(
        "Pexels API Key",
        value="AbqSkVbZko07cGsPYZbQgm7SVvwhKPqqYV8bYZs254tAF5OKHcFBQHQl",
        type="password"
    )
    
    st.subheader("Search Options")
    per_scene = st.slider("Videos per scene", 1, 5, 3)
    min_res = st.selectbox("Minimum Resolution", ["720p", "1080p", "4K"])
    
    # Resolution mapping
    res_map = {
        "720p": 720,
        "1080p": 1080,
        "4K": 2160
    }
    min_height = res_map[min_res]

# -----------------------------
# MAIN - SCRIPT INPUT
# -----------------------------
tab1, tab2 = st.tabs(["📝 Script Input", "🔍 Keyword Search"])

with tab1:
    script = st.text_area(
        "Paste your script here",
        placeholder="Example: In 2020, the global economy faced an unprecedented crisis. Stock markets crashed worldwide. Businesses struggled to survive.",
        height=200
    )
    
    split_method = st.radio(
        "Split script by:",
        ["Sentence (.)", "2 Sentences", "Paragraph"]
    )
    
    if st.button("🎬 Generate B-roll", type="primary"):
        if not script.strip():
            st.warning("Please paste a script.")
            st.stop()
            
        if not api_key:
            st.warning("Please enter Pexels API key.")
            st.stop()
            
        # Split script
        if split_method == "Sentence (.)":
            scenes = [s.strip() for s in script.split('.') if s.strip()]
        elif split_method == "2 Sentences":
            sentences = [s.strip() for s in script.split('.') if s.strip()]
            scenes = [' '.join(sentences[i:i+2]) for i in range(0, len(sentences), 2)]
        else:  # Paragraph
            scenes = [p.strip() for p in script.split('\n') if p.strip()]
        
        st.success(f"📝 Script split into {len(scenes)} scenes")
        
        # Generate keywords (simple version)
        st.info("🤖 Generating keywords for each scene...")
        
        # Store results
        all_results = []
        
        for idx, scene in enumerate(scenes, 1):
            with st.spinner(f"Searching scene {idx}..."):
                # Simple keyword extraction (words > 3 chars)
                words = re.findall(r'\b[a-zA-Z]{4,}\b', scene)
                keywords = list(set([w.lower() for w in words]))[:3]
                
                if not keywords:
                    keywords = ["business", "people", "work"]
                
                # Search Pexels
                url = "https://api.pexels.com/videos/search"
                headers = {"Authorization": api_key}
                
                scene_results = []
                
                for kw in keywords:
                    params = {"query": kw, "per_page": per_scene}
                    try:
                        response = requests.get(url, headers=headers, params=params, timeout=30)
                        if response.status_code == 200:
                            data = response.json()
                            videos = data.get("videos", [])
                            scene_results.extend(videos)
                    except:
                        pass
                
                # Remove duplicates
                seen = set()
                unique_results = []
                for v in scene_results:
                    vid = v.get('id')
                    if vid not in seen:
                        seen.add(vid)
                        unique_results.append(v)
                
                all_results.append({
                    "scene": scene,
                    "scene_num": idx,
                    "videos": unique_results[:per_scene]
                })
        
        # Display results
        st.subheader("🎥 B-roll Results")
        
        for result in all_results:
            with st.expander(f"Scene {result['scene_num']}: {result['scene'][:50]}..."):
                st.caption(f"Full: {result['scene']}")
                
                if not result['videos']:
                    st.warning("No videos found for this scene.")
                    continue
                
                # Display videos in grid
                cols = st.columns(min(3, len(result['videos'])))
                
                for idx, col in enumerate(cols):
                    if idx < len(result['videos']):
                        video = result['videos'][idx]
                        
                        with col:
                            # Get best quality video
                            video_files = video.get("video_files", [])
                            selected_file = None
                            
                            for file in video_files:
                                height = file.get("height", 0)
                                if height >= min_height:
                                    selected_file = file
                                    break
                            
                            if selected_file is None and video_files:
                                selected_file = video_files[0]
                            
                            if selected_file:
                                video_url = selected_file.get("link")
                                st.video(video_url)
                                st.caption(f"🎬 {selected_file.get('width', '?')}×{selected_file.get('height', '?')}")
                                
                                # Download button
                                if st.button(f"⬇️ Download", key=f"down_{result['scene_num']}_{idx}"):
                                    # Simple download (would need actual download logic)
                                    st.info("Download link: " + video_url)
        
        # Bulk download
        st.subheader("📦 Bulk Download")
        if st.button("📥 Download All (ZIP)"):
            st.info("ZIP download feature coming soon!")

with tab2:
    # Old keyword search
    keyword = st.text_input("Search single keyword", placeholder="business")
    if st.button("🔍 Search"):
        if keyword and api_key:
            url = "https://api.pexels.com/videos/search"
            headers = {"Authorization": api_key}
            params = {"query": keyword, "per_page": 12}
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])
                
                for row_start in range(0, len(videos), 3):
                    cols = st.columns(3)
                    for col, video in zip(cols, videos[row_start:row_start+3]):
                        with col:
                            video_files = video.get("video_files", [])
                            for file in video_files:
                                if file.get("height", 0) >= 720:
                                    st.video(file.get("link"))
                                    break

# -----------------------------
# FOOTER
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.caption("🎬 B-Roll Finder Pro v1.1")
st.sidebar.caption("Made with ❤️ for YouTube Automation")
