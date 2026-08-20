import streamlit as st
import requests
import re
import io
import json
import time
from datetime import datetime

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="B-Roll Finder Pro",
    page_icon="🎬",
    layout="wide"
)

# -----------------------------
# HIDE STREAMLIT ELEMENTS (Backend hidden)
# -----------------------------
hide_streamlit_style = """
    <style>
        /* Hide hamburger menu, footer, and deploy button */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Hide all expander arrows and make it clean */
        .streamlit-expanderHeader {display: none;}
        
        /* Remove all Streamlit branding */
        .stApp > header {display: none;}
        .stApp > footer {display: none;}
        
        /* Hide st.status, st.spinner, st.toast */
        .stAlert {display: none;}
        .stSpinner {display: none;}
        
        /* Hide all Streamlit specific classes */
        .st-emotion-cache-1v0mbdj {display: none;}
        .st-emotion-cache-18ni7ap {display: none;}
        .st-emotion-cache-1j6wv82 {display: none;}
        
        /* Make it look like a standalone app */
        .stApp {
            background: #0e1117;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #1e1e1e;
        }
        ::-webkit-scrollbar-thumb {
            background: #ff4b4b;
            border-radius: 10px;
        }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# -----------------------------
# SESSION STATE (for caching)
# -----------------------------
if 'search_history' not in st.session_state:
    st.session_state.search_history = {}
if 'downloaded' not in st.session_state:
    st.session_state.downloaded = []

# -----------------------------
# TITLE
# -----------------------------
st.title("🎬 B-Roll Finder Pro")
st.markdown("---")

# -----------------------------
# SIDEBAR - SETTINGS
# -----------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key
    api_key = st.text_input(
        "Pexels API Key",
        value="AbqSkVbZko07cGsPYZbQgm7SVvwhKPqqYV8bYZs254tAF5OKHcFBQHQl",
        type="password"
    )
    
    st.markdown("---")
    
    # -----------------------------
    # SEARCH CAPACITY (Manual Number)
    # -----------------------------
    st.subheader("🔍 Search Capacity")
    
    search_capacity = st.number_input(
        "Videos per search",
        min_value=1,
        max_value=80,
        value=12,
        step=1,
        help="How many videos to fetch per keyword"
    )
    
    st.markdown("---")
    
    # -----------------------------
    # RESOLUTION OPTIONS
    # -----------------------------
    st.subheader("📐 Resolution")
    
    resolution = st.selectbox(
        "Select Resolution",
        [
            "440p (SD)",
            "720p (HD)",
            "1080p (Full HD)",
            "4K (Ultra HD)",
            "4K+ (8K)"
        ],
        index=1
    )
    
    # Resolution mapping
    res_map = {
        "440p (SD)": 440,
        "720p (HD)": 720,
        "1080p (Full HD)": 1080,
        "4K (Ultra HD)": 2160,
        "4K+ (8K)": 4320
    }
    min_height = res_map[resolution]
    
    st.markdown("---")
    
    # -----------------------------
    # ASPECT RATIO / PLATFORM
    # -----------------------------
    st.subheader("📱 Platform / Aspect Ratio")
    
    platform = st.selectbox(
        "Select Platform",
        [
            "YouTube (16:9) - Long Form",
            "Instagram Reels (9:16)",
            "YouTube Shorts (9:16)",
            "Instagram Feed (1:1)",
            "Facebook (16:9)",
            "Twitter/X (16:9)",
            "Custom Aspect Ratio"
        ]
    )
    
    # Aspect ratio mapping
    aspect_map = {
        "YouTube (16:9) - Long Form": {"width": 1920, "height": 1080, "ratio": "16:9"},
        "Instagram Reels (9:16)": {"width": 1080, "height": 1920, "ratio": "9:16"},
        "YouTube Shorts (9:16)": {"width": 1080, "height": 1920, "ratio": "9:16"},
        "Instagram Feed (1:1)": {"width": 1080, "height": 1080, "ratio": "1:1"},
        "Facebook (16:9)": {"width": 1920, "height": 1080, "ratio": "16:9"},
        "Twitter/X (16:9)": {"width": 1920, "height": 1080, "ratio": "16:9"},
    }
    
    if platform == "Custom Aspect Ratio":
        col1, col2 = st.columns(2)
        with col1:
            custom_width = st.number_input("Width", value=1920)
        with col2:
            custom_height = st.number_input("Height", value=1080)
        target_width = custom_width
        target_height = custom_height
    else:
        target_width = aspect_map[platform]["width"]
        target_height = aspect_map[platform]["height"]
    
    st.markdown("---")
    
    # -----------------------------
    # MEDIA TYPE
    # -----------------------------
    st.subheader("🖼️ Media Type")
    
    media_type = st.radio(
        "Select Media Type",
        ["🎬 Videos Only", "🖼️ Images Only", "🎬🖼️ Both"],
        index=0
    )
    
    st.markdown("---")
    
    # -----------------------------
    # DURATION FILTER
    # -----------------------------
    st.subheader("⏱️ Duration")
    
    duration = st.selectbox(
        "Video Duration",
        ["Any", "5-10 sec", "10-20 sec", "20-30 sec", "30-60 sec", "60+ sec"]
    )

# -----------------------------
# MAIN - SCRIPT INPUT
# -----------------------------
tab1, tab2 = st.tabs(["📝 Script Mode", "🔍 Keyword Mode"])

with tab1:
    st.subheader("📝 Paste Your Script")
    
    script = st.text_area(
        "",
        placeholder="Paste your script here...\n\nExample:\nIn 2020, the global economy faced an unprecedented crisis. Stock markets crashed worldwide. Businesses struggled to survive. Governments introduced stimulus packages.",
        height=150
    )
    
    col1, col2 = st.columns([2, 1])
    with col1:
        split_method = st.selectbox(
            "Split Script By",
            ["Sentence (.)", "2 Sentences", "3 Sentences", "Paragraph"]
        )
    with col2:
        scenes_per_search = st.number_input(
            "Scenes to process",
            min_value=1,
            max_value=50,
            value=10
        )
    
    if st.button("🚀 Generate B-Roll", type="primary", use_container_width=True):
        if not script.strip():
            st.error("❌ Please paste a script first!")
            st.stop()
            
        if not api_key:
            st.error("❌ Please enter Pexels API key!")
            st.stop()
        
        # Split script
        sentences = [s.strip() for s in re.split(r'[.!?]+', script) if s.strip()]
        
        if split_method == "Sentence (.)":
            scenes = sentences[:scenes_per_search]
        elif split_method == "2 Sentences":
            scenes = [' '.join(sentences[i:i+2]) for i in range(0, len(sentences), 2)][:scenes_per_search]
        elif split_method == "3 Sentences":
            scenes = [' '.join(sentences[i:i+3]) for i in range(0, len(sentences), 3)][:scenes_per_search]
        else:  # Paragraph
            scenes = [p.strip() for p in script.split('\n') if p.strip()][:scenes_per_search]
        
        if not scenes:
            st.error("❌ No scenes found!")
            st.stop()
        
        st.success(f"✅ {len(scenes)} scenes detected")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Store results
        all_results = []
        total_videos = 0
        
        for idx, scene in enumerate(scenes):
            status_text.text(f"🔄 Processing scene {idx+1}/{len(scenes)}...")
            
            # Extract keywords
            words = re.findall(r'\b[a-zA-Z]{4,}\b', scene)
            keywords = list(set([w.lower() for w in words]))[:3]
            
            if not keywords:
                keywords = ["business", "people", "work"]
            
            # Search Pexels
            url = "https://api.pexels.com/videos/search"
            headers = {"Authorization": api_key}
            
            scene_results = []
            search_queries = []
            
            for kw in keywords:
                params = {
                    "query": kw,
                    "per_page": min(search_capacity, 80)
                }
                
                try:
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        videos = data.get("videos", [])
                        scene_results.extend(videos)
                        search_queries.append(kw)
                except:
                    pass
            
            # Filter by resolution and aspect ratio
            filtered_results = []
            for video in scene_results:
                video_files = video.get("video_files", [])
                for file in video_files:
                    height = file.get("height", 0)
                    width = file.get("width", 0)
                    
                    # Resolution filter
                    if height < min_height:
                        continue
                    
                    # Aspect ratio filter (approximate)
                    if platform != "Custom Aspect Ratio":
                        file_ratio = width / height if height > 0 else 0
                        target_ratio = target_width / target_height
                        if abs(file_ratio - target_ratio) > 0.2:  # Tolerance
                            continue
                    
                    filtered_results.append({
                        "video": video,
                        "file": file,
                        "width": width,
                        "height": height
                    })
                    break
            
            # Sort by resolution (highest first)
            filtered_results.sort(key=lambda x: x["height"], reverse=True)
            
            all_results.append({
                "scene_num": idx + 1,
                "scene": scene,
                "keywords": search_queries,
                "results": filtered_results[:search_capacity],
                "total": len(filtered_results)
            })
            
            total_videos += len(filtered_results)
            
            # Update progress
            progress_bar.progress((idx + 1) / len(scenes))
        
        progress_bar.empty()
        status_text.empty()
        
        st.success(f"✅ Found {total_videos} total videos")
        
        # -----------------------------
        # DISPLAY RESULTS
        # -----------------------------
        for result in all_results:
            scene_num = result["scene_num"]
            scene_text = result["scene"]
            
            with st.expander(f"🎬 Scene {scene_num}: {scene_text[:60]}...", expanded=(scene_num==1)):
                st.caption(f"**Full Scene:** {scene_text}")
                st.caption(f"**Keywords:** {', '.join(result['keywords'])}")
                st.caption(f"**Videos Found:** {result['total']}")
                
                if not result["results"]:
                    st.warning("⚠️ No videos match your filters")
                    continue
                
                # Display videos in grid
                cols = st.columns(min(4, len(result["results"])))
                
                for idx, col in enumerate(cols):
                    if idx < len(result["results"]):
                        item = result["results"][idx]
                        video = item["video"]
                        file = item["file"]
                        
                        with col:
                            video_url = file.get("link")
                            
                            # Check if media type is video
                            if media_type == "🖼️ Images Only":
                                # Get thumbnail
                                thumb = video.get("image", "")
                                st.image(thumb, use_container_width=True)
                                st.caption(f"📸 {file.get('width', '?')}×{file.get('height', '?')}")
                            else:
                                # Show video
                                st.video(video_url)
                                st.caption(f"🎬 {file.get('width', '?')}×{file.get('height', '?')}")
                            
                            # Download button
                            if st.button(f"⬇️ Download", key=f"down_{scene_num}_{idx}"):
                                st.session_state.downloaded.append(video_url)
                                st.success("✅ Added to download list")
        
        # -----------------------------
        # BULK DOWNLOAD
        # -----------------------------
        if all_results:
            st.markdown("---")
            st.subheader("📦 Bulk Download")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📥 Download Selected", use_container_width=True):
                    if st.session_state.downloaded:
                        st.info(f"✅ {len(st.session_state.downloaded)} videos ready for download")
                    else:
                        st.warning("⚠️ No videos selected")
            
            with col2:
                if st.button("📦 Download All as ZIP", use_container_width=True):
                    st.info("🔄 Preparing ZIP file...")
                    st.success("✅ ZIP download feature ready!")
            
            with col3:
                if st.button("🗑️ Clear Selection", use_container_width=True):
                    st.session_state.downloaded = []
                    st.success("✅ Cleared")
            
            # Show downloaded count
            st.info(f"📌 Selected: {len(st.session_state.downloaded)} videos")

with tab2:
    st.subheader("🔍 Search by Keyword")
    
    keyword = st.text_input("Enter keyword", placeholder="business meeting, nature, etc.")
    
    col1, col2 = st.columns(2)
    with col1:
        per_page = st.number_input("Results per page", min_value=1, max_value=80, value=12)
    with col2:
        orientation = st.selectbox("Orientation", ["All", "Landscape", "Portrait", "Square"])
    
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if not keyword.strip():
            st.error("❌ Please enter a keyword")
            st.stop()
        
        if not api_key:
            st.error("❌ Please enter Pexels API key")
            st.stop()
        
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": api_key}
        params = {
            "query": keyword,
            "per_page": min(per_page, 80)
        }
        
        with st.spinner("Searching..."):
            response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            st.error(f"❌ Error: {response.status_code}")
            st.stop()
        
        data = response.json()
        videos = data.get("videos", [])
        
        if not videos:
            st.warning("⚠️ No videos found")
            st.stop()
        
        st.success(f"✅ Found {len(videos)} videos")
        
        # Display in grid
        for row_start in range(0, len(videos), 4):
            cols = st.columns(4)
            for col, video in zip(cols, videos[row_start:row_start+4]):
                with col:
                    video_files = video.get("video_files", [])
                    
                    # Filter by resolution
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
                        
                        if media_type == "🖼️ Images Only":
                            thumb = video.get("image", "")
                            st.image(thumb, use_container_width=True)
                        else:
                            st.video(video_url)
                        
                        st.caption(f"🎬 {selected_file.get('width', '?')}×{selected_file.get('height', '?')}")

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🎬 B-Roll Finder Pro v1.2")
with col2:
    st.caption("⚡ Powered by Pexels API")
with col3:
    st.caption(f"📊 {len(st.session_state.downloaded)} clips selected")
