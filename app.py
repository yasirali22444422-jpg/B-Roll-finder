import streamlit as st
import requests
import re
import io
import json
import zipfile
import time
from datetime import datetime

# -----------------------------
# PAGE CONFIG - Clean UI
# -----------------------------
st.set_page_config(
    page_title="B-Roll Collector",
    page_icon="🎬",
    layout="wide"
)

# -----------------------------
# HIDE STREAMLIT ELEMENTS
# -----------------------------
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp > header {display: none;}
        .stApp > footer {display: none;}
        .stAlert {display: none;}
        .stSpinner {display: none;}
        
        /* Hide API key value */
        .stTextInput input[type="password"] {
            -webkit-text-security: disc !important;
        }
        
        /* Clean expander */
        .streamlit-expanderHeader {
            font-weight: bold;
            color: #ff4b4b;
        }
        
        /* Custom styling */
        .stApp {
            background: #0e1117;
        }
        .stButton > button {
            background: #ff4b4b;
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 10px 30px;
        }
        .stButton > button:hover {
            background: #ff6b6b;
            color: white;
        }
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
# SESSION STATE
# -----------------------------
if 'selected_clips' not in st.session_state:
    st.session_state.selected_clips = []
if 'all_results' not in st.session_state:
    st.session_state.all_results = []
if 'downloaded_zip' not in st.session_state:
    st.session_state.downloaded_zip = None

# -----------------------------
# HEADER
# -----------------------------
st.title("🎬 B-Roll Collector")
st.markdown("**Script se B-Roll ready in 2 minutes**")
st.markdown("---")

# -----------------------------
# SIDEBAR - SETTINGS (HIDDEN API)
# -----------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key - Hidden properly
    api_key = st.text_input(
        "API Key",
        value="",
        type="password",
        placeholder="Enter your Pexels API key",
        help="Get free API key from pexels.com/api"
    )
    
    # If key exists, show status only
    if api_key:
        st.success("✅ API Key configured")
    
    st.markdown("---")
    
    # -----------------------------
    # DURATION FILTER - Seconds + Minutes
    # -----------------------------
    st.subheader("⏱️ Video Duration")
    
    duration_type = st.radio(
        "Select duration type:",
        ["Seconds", "Minutes"],
        horizontal=True
    )
    
    if duration_type == "Seconds":
        duration_sec = st.selectbox(
            "Duration (seconds)",
            ["Any", "5s", "10s", "15s", "20s", "30s", "45s", "60s"]
        )
        duration_min = None
    else:
        duration_min = st.selectbox(
            "Duration (minutes)",
            ["Any", "1 min", "2 min", "3 min", "5 min", "10 min"]
        )
        duration_sec = None
    
    st.markdown("---")
    
    # -----------------------------
    # SEARCH CAPACITY
    # -----------------------------
    st.subheader("🔍 Search Capacity")
    per_page = st.number_input(
        "Videos per search",
        min_value=1,
        max_value=80,
        value=12
    )
    
    st.markdown("---")
    
    # -----------------------------
    # RESOLUTION
    # -----------------------------
    st.subheader("📐 Resolution")
    resolution = st.selectbox(
        "Select Resolution",
        ["440p", "720p", "1080p", "4K", "4K+"]
    )
    
    res_map = {
        "440p": 440,
        "720p": 720,
        "1080p": 1080,
        "4K": 2160,
        "4K+": 4320
    }
    min_height = res_map[resolution]
    
    st.markdown("---")
    
    # -----------------------------
    # PLATFORM / ASPECT RATIO
    # -----------------------------
    st.subheader("📱 Platform")
    platform = st.selectbox(
        "Select Platform",
        ["YouTube (16:9)", "Instagram Reels (9:16)", "YouTube Shorts (9:16)", "Instagram Feed (1:1)", "Facebook (16:9)", "Custom"]
    )
    
    if platform == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            custom_w = st.number_input("Width", value=1920)
        with col2:
            custom_h = st.number_input("Height", value=1080)
    else:
        platform_map = {
            "YouTube (16:9)": {"w": 1920, "h": 1080},
            "Instagram Reels (9:16)": {"w": 1080, "h": 1920},
            "YouTube Shorts (9:16)": {"w": 1080, "h": 1920},
            "Instagram Feed (1:1)": {"w": 1080, "h": 1080},
            "Facebook (16:9)": {"w": 1920, "h": 1080}
        }
        custom_w = platform_map[platform]["w"]
        custom_h = platform_map[platform]["h"]
    
    st.markdown("---")
    
    # -----------------------------
    # MEDIA TYPE
    # -----------------------------
    st.subheader("🖼️ Media Type")
    media_type = st.radio(
        "Select:",
        ["Videos", "Images", "Both"],
        horizontal=True
    )

# -----------------------------
# MAIN - COMPETITOR LIKE UI
# -----------------------------
st.subheader("📝 Step 1: Choose Your Niche")

niche = st.selectbox(
    "Select Niche",
    ["Finance", "Technology", "Health", "Real Estate", "Travel", "Motivation", "Business", "Education", "Food", "Fashion", "Sports", "Nature", "History", "Celebrity", "Geopolitics", "Other"]
)

st.subheader("📝 Step 2: Add Your Script")

# Title input
video_title = st.text_input(
    "Video Title",
    placeholder="Example: Financial Strategies for Seniors After Retirement"
)

# Script input
script = st.text_area(
    "Paste Your Script Here",
    placeholder="Paste your full script here...\n\nExample:\nIn 2020, the global economy faced an unprecedented crisis. Stock markets crashed worldwide. Governments introduced stimulus packages...",
    height=200
)

# Script info display (like competitor)
if script:
    char_count = len(script)
    sentence_count = len([s for s in re.split(r'[.!?]+', script) if s.strip()])
    estimated_clips = (sentence_count // 2) + (sentence_count % 2)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Characters", char_count)
    with col2:
        st.metric("Sentences", sentence_count)
    with col3:
        st.metric("Estimated B-rolls", estimated_clips)

# Split option (competitor uses 2 sentences)
st.subheader("📝 Split Settings")
split_type = st.radio(
    "Split Script By:",
    ["2 Sentences (Recommended)", "1 Sentence", "3 Sentences", "Custom"],
    horizontal=True
)

if split_type == "Custom":
    custom_split = st.number_input("Sentences per clip", min_value=1, max_value=10, value=2)

# -----------------------------
# GENERATE B-ROLL BUTTON
# -----------------------------
if st.button("🎬 Collect B-Rolls", type="primary", use_container_width=True):
    if not script.strip():
        st.error("❌ Please paste a script!")
        st.stop()
    
    if not api_key:
        st.error("❌ Please add your API key in sidebar!")
        st.stop()
    
    # Split script
    sentences = [s.strip() for s in re.split(r'[.!?]+', script) if s.strip()]
    
    if split_type == "1 Sentence":
        scenes = sentences
    elif split_type == "2 Sentences (Recommended)":
        scenes = [' '.join(sentences[i:i+2]) for i in range(0, len(sentences), 2)]
    elif split_type == "3 Sentences":
        scenes = [' '.join(sentences[i:i+3]) for i in range(0, len(sentences), 3)]
    else:  # Custom
        scenes = [' '.join(sentences[i:i+custom_split]) for i in range(0, len(sentences), custom_split)]
    
    st.success(f"✅ Script split into {len(scenes)} scenes")
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Store results
    all_results = []
    all_video_urls = []
    
    for idx, scene in enumerate(scenes):
        status_text.text(f"🔄 Splitting Script... Extracting Keywords... Fetching B-rolls for scene {idx+1}/{len(scenes)}")
        
        # Extract keywords (like competitor)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', scene)
        keywords = list(set([w.lower() for w in words]))[:3]
        
        if not keywords:
            keywords = ["business", "people", "work"]
        
        # Search Pexels
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": api_key}
        
        scene_results = []
        
        for kw in keywords:
            params = {
                "query": kw,
                "per_page": min(per_page, 80)
            }
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    videos = data.get("videos", [])
                    scene_results.extend(videos)
            except:
                pass
        
        # Filter by resolution and aspect ratio
        filtered_results = []
        for video in scene_results:
            video_files = video.get("video_files", [])
            for file in video_files:
                height = file.get("height", 0)
                width = file.get("width", 0)
                
                if height < min_height:
                    continue
                
                # Check aspect ratio
                file_ratio = width / height if height > 0 else 0
                target_ratio = custom_w / custom_h
                if abs(file_ratio - target_ratio) > 0.3:
                    continue
                
                filtered_results.append({
                    "video": video,
                    "file": file,
                    "url": file.get("link"),
                    "width": width,
                    "height": height
                })
                break
        
        # Sort by quality
        filtered_results.sort(key=lambda x: x["height"], reverse=True)
        
        # Get top result (like competitor gives 1 per scene)
        best_result = filtered_results[0] if filtered_results else None
        
        if best_result:
            all_video_urls.append(best_result["url"])
        
        all_results.append({
            "scene_num": idx + 1,
            "scene": scene,
            "keywords": keywords,
            "best": best_result,
            "all": filtered_results[:per_page],
            "total": len(filtered_results)
        })
        
        progress_bar.progress((idx + 1) / len(scenes))
    
    progress_bar.empty()
    status_text.empty()
    
    # Store in session
    st.session_state.all_results = all_results
    st.session_state.video_urls = all_video_urls
    
    st.success(f"✅ Found {len(all_video_urls)} B-roll clips!")

# -----------------------------
# DISPLAY RESULTS (Like Competitor)
# -----------------------------
if st.session_state.all_results:
    st.markdown("---")
    st.subheader("🎥 Your B-Roll Clips")
    st.caption("Numbered clips ready for download")
    
    # Display in grid with numbering
    for idx, result in enumerate(st.session_state.all_results):
        scene_num = result["scene_num"]
        scene_text = result["scene"]
        best = result["best"]
        
        if best:
            with st.expander(f"Clip {scene_num:03d} - {scene_text[:50]}...", expanded=(scene_num<=3)):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.video(best["url"])
                
                with col2:
                    st.caption(f"**Scene:** {scene_text}")
                    st.caption(f"**Keywords:** {', '.join(result['keywords'])}")
                    st.caption(f"**Resolution:** {best['width']}×{best['height']}")
                    st.caption(f"**Status:** ✅ Ready")
                    
                    # Download individual
                    if st.button(f"⬇️ Download Clip {scene_num:03d}", key=f"down_{scene_num}"):
                        st.info(f"Downloading clip {scene_num:03d}...")
                        st.markdown(f"[Click here to download]({best['url']})")
    
    # -----------------------------
    # BULK DOWNLOAD - ZIP
    # -----------------------------
    st.markdown("---")
    st.subheader("📦 Bulk Download")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("📥 Download ZIP", use_container_width=True):
            if st.session_state.video_urls:
                st.info(f"🔄 Preparing ZIP with {len(st.session_state.video_urls)} clips...")
                
                # Create ZIP in memory
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                    for idx, url in enumerate(st.session_state.video_urls, 1):
                        try:
                            response = requests.get(url, timeout=30)
                            if response.status_code == 200:
                                filename = f"clip_{idx:03d}.mp4"
                                zip_file.writestr(filename, response.content)
                        except:
                            pass
                
                zip_buffer.seek(0)
                st.session_state.downloaded_zip = zip_buffer.getvalue()
                
                st.success("✅ ZIP ready!")
            else:
                st.warning("⚠️ No clips to download")
    
    with col2:
        if st.session_state.downloaded_zip:
            st.download_button(
                label="💾 Save ZIP",
                data=st.session_state.downloaded_zip,
                file_name=f"broll_clips_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
                use_container_width=True
            )
    
    with col3:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.all_results = []
            st.session_state.video_urls = []
            st.session_state.downloaded_zip = None
            st.success("✅ Cleared")
    
    # Show count
    st.info(f"📌 Total clips ready: {len(st.session_state.video_urls)}")

# -----------------------------
# FOOTER (Like Competitor)
# -----------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🎬 B-Roll Collector")
with col2:
    st.caption("⚡ Script to B-Roll in 2 Minutes")
with col3:
    st.caption(f"📊 {len(st.session_state.video_urls) if hasattr(st.session_state, 'video_urls') else 0} clips ready")
