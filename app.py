import streamlit as st
import requests
import re
import io
import json
import zipfile
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
# HIDE STREAMLIT ELEMENTS
# -----------------------------
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .streamlit-expanderHeader {display: none;}
        .stApp > header {display: none;}
        .stApp > footer {display: none;}
        .stApp { background: #0e1117; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #1e1e1e; }
        ::-webkit-scrollbar-thumb { background: #ff4b4b; border-radius: 10px; }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# -----------------------------
# SESSION STATE
# -----------------------------
if "downloaded" not in st.session_state:
    st.session_state.downloaded = []  # list of dicts: {url, filename}
if "all_results" not in st.session_state:
    st.session_state.all_results = []
if "script_input" not in st.session_state:
    st.session_state.script_input = ""

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

    # API Key - no hardcoded default (security fix)
    api_key = st.text_input(
        "Pexels API Key",
        value=st.session_state.get("api_key_saved", ""),
        type="password",
        help="Apni Pexels API key yahan daalein. Ye kahin save nahi hoti, sirf is session mein use hoti hai."
    )

    st.markdown("---")
    st.subheader("🔍 Search Capacity")
    search_capacity = st.number_input(
        "Videos per search", min_value=1, max_value=80, value=12, step=1,
        help="Har keyword ke liye kitni videos fetch karni hain"
    )

    st.markdown("---")
    st.subheader("📐 Resolution")
    resolution = st.selectbox(
        "Select Resolution",
        ["440p (SD)", "720p (HD)", "1080p (Full HD)", "4K (Ultra HD)", "4K+ (8K)"],
        index=1
    )
    res_map = {"440p (SD)": 440, "720p (HD)": 720, "1080p (Full HD)": 1080,
               "4K (Ultra HD)": 2160, "4K+ (8K)": 4320}
    min_height = res_map[resolution]

    st.markdown("---")
    st.subheader("📱 Platform / Aspect Ratio")
    platform = st.selectbox(
        "Select Platform",
        ["YouTube (16:9) - Long Form", "Instagram Reels (9:16)", "YouTube Shorts (9:16)",
         "Instagram Feed (1:1)", "Facebook (16:9)", "Twitter/X (16:9)", "Custom Aspect Ratio"]
    )
    aspect_map = {
        "YouTube (16:9) - Long Form": {"width": 1920, "height": 1080},
        "Instagram Reels (9:16)": {"width": 1080, "height": 1920},
        "YouTube Shorts (9:16)": {"width": 1080, "height": 1920},
        "Instagram Feed (1:1)": {"width": 1080, "height": 1080},
        "Facebook (16:9)": {"width": 1920, "height": 1080},
        "Twitter/X (16:9)": {"width": 1920, "height": 1080},
    }
    if platform == "Custom Aspect Ratio":
        col1, col2 = st.columns(2)
        with col1:
            target_width = st.number_input("Width", value=1920)
        with col2:
            target_height = st.number_input("Height", value=1080)
    else:
        target_width = aspect_map[platform]["width"]
        target_height = aspect_map[platform]["height"]

    st.markdown("---")
    st.subheader("🖼️ Media Type")
    media_type = st.radio("Select Media Type", ["🎬 Videos Only", "🖼️ Images Only", "🎬🖼️ Both"], index=0)

    st.markdown("---")
    st.subheader("💾 Project Save / Load")

    # SAVE PROJECT (real - exports actual JSON with script + settings + scene metadata)
    project_data = {
        "saved_at": datetime.now().isoformat(),
        "script": st.session_state.script_input,
        "settings": {
            "resolution": resolution,
            "platform": platform,
            "media_type": media_type,
            "search_capacity": search_capacity
        },
        "results": [
            {
                "scene_num": r["scene_num"],
                "scene": r["scene"],
                "keywords": r["keywords"],
                "videos": [
                    {"id": item["video"].get("id"), "link": item["file"].get("link"),
                     "width": item["width"], "height": item["height"]}
                    for item in r["results"]
                ]
            }
            for r in st.session_state.all_results
        ]
    }
    st.download_button(
        "📥 Save Project (.json)",
        data=json.dumps(project_data, indent=2),
        file_name=f"broll_project_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        use_container_width=True
    )

    # LOAD PROJECT
    uploaded_project = st.file_uploader("📤 Load Project (.json)", type=["json"])
    if uploaded_project is not None:
        if st.button("✅ Restore this project", use_container_width=True):
            try:
                loaded = json.load(uploaded_project)
                st.session_state.script_input = loaded.get("script", "")
                st.success("Script restore ho gaya! (Videos dobara search honge kyunki links expire ho sakte hain)")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Invalid project file: {e}")


# -----------------------------
# HELPER: fetch bytes for download
# -----------------------------
def fetch_video_bytes(url):
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


def make_zip(items):
    """items: list of dicts {url, filename}. Returns BytesIO of zip."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            content = fetch_video_bytes(item["url"])
            if content:
                zf.writestr(item["filename"], content)
    buffer.seek(0)
    return buffer


def search_pexels(keyword, api_key, per_page):
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": keyword, "per_page": min(per_page, 80)}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get("videos", [])
    except Exception:
        pass
    return []


def filter_and_sort(videos, min_height, target_width, target_height, platform):
    filtered = []
    for video in videos:
        for file in video.get("video_files", []):
            height = file.get("height", 0)
            width = file.get("width", 0)
            if height < min_height:
                continue
            if platform != "Custom Aspect Ratio":
                file_ratio = width / height if height > 0 else 0
                target_ratio = target_width / target_height
                if abs(file_ratio - target_ratio) > 0.2:
                    continue
            filtered.append({"video": video, "file": file, "width": width, "height": height})
            break
    filtered.sort(key=lambda x: x["height"], reverse=True)
    return filtered


def process_scene(scene, api_key, search_capacity, min_height, target_width, target_height, platform, exclude_keywords=None):
    exclude_keywords = exclude_keywords or []
    words = re.findall(r"\b[a-zA-Z]{4,}\b", scene)
    keywords = [w.lower() for w in dict.fromkeys(words) if w.lower() not in exclude_keywords][:3]
    if not keywords:
        fallback = ["business", "people", "work", "city", "nature", "office"]
        keywords = [k for k in fallback if k not in exclude_keywords][:3]

    scene_results = []
    used_keywords = []
    for kw in keywords:
        videos = search_pexels(kw, api_key, search_capacity)
        if videos:
            scene_results.extend(videos)
            used_keywords.append(kw)

    filtered = filter_and_sort(scene_results, min_height, target_width, target_height, platform)
    return {
        "keywords": used_keywords,
        "results": filtered[:search_capacity],
        "total": len(filtered)
    }


# -----------------------------
# MAIN - SCRIPT INPUT
# -----------------------------
tab1, tab2 = st.tabs(["📝 Script Mode", "🔍 Keyword Mode"])

with tab1:
    st.subheader("📝 Paste Your Script")

    script = st.text_area(
        "",
        placeholder="Paste your script here...",
        height=150,
        key="script_input"
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        split_method = st.selectbox("Split Script By", ["Sentence (.)", "2 Sentences", "3 Sentences", "Paragraph"])
    with col2:
        scenes_per_search = st.number_input("Scenes to process", min_value=1, max_value=50, value=10)

    if st.button("🚀 Generate B-Roll", type="primary", use_container_width=True):
        if not script.strip():
            st.error("❌ Please paste a script first!")
            st.stop()
        if not api_key:
            st.error("❌ Please enter Pexels API key!")
            st.stop()

        sentences = [s.strip() for s in re.split(r"[.!?]+", script) if s.strip()]
        if split_method == "Sentence (.)":
            scenes = sentences[:scenes_per_search]
        elif split_method == "2 Sentences":
            scenes = [" ".join(sentences[i:i + 2]) for i in range(0, len(sentences), 2)][:scenes_per_search]
        elif split_method == "3 Sentences":
            scenes = [" ".join(sentences[i:i + 3]) for i in range(0, len(sentences), 3)][:scenes_per_search]
        else:
            scenes = [p.strip() for p in script.split("\n") if p.strip()][:scenes_per_search]

        if not scenes:
            st.error("❌ No scenes found!")
            st.stop()

        st.success(f"✅ {len(scenes)} scenes detected")

        progress_bar = st.progress(0)
        status_text = st.empty()
        all_results = []

        for idx, scene in enumerate(scenes):
            status_text.text(f"🔄 Processing scene {idx + 1}/{len(scenes)}...")
            out = process_scene(scene, api_key, search_capacity, min_height, target_width, target_height, platform)
            all_results.append({
                "scene_num": idx + 1,
                "scene": scene,
                "keywords": out["keywords"],
                "results": out["results"],
                "total": out["total"],
                "excluded_keywords": []
            })
            progress_bar.progress((idx + 1) / len(scenes))

        progress_bar.empty()
        status_text.empty()
        st.session_state.all_results = all_results
        st.success(f"✅ Found {sum(r['total'] for r in all_results)} total videos")

    # -----------------------------
    # DISPLAY RESULTS (persisted in session_state so buttons don't wipe them)
    # -----------------------------
    for result in st.session_state.all_results:
        scene_num = result["scene_num"]
        scene_text = result["scene"]

        with st.expander(f"🎬 Scene {scene_num}: {scene_text[:60]}...", expanded=(scene_num == 1)):
            st.caption(f"**Full Scene:** {scene_text}")
            st.caption(f"**Keywords:** {', '.join(result['keywords'])}")
            st.caption(f"**Videos Found:** {result['total']}")

            # REGENERATE - real: re-searches excluding previously used keywords
            if st.button("🔁 Regenerate this scene", key=f"regen_{scene_num}"):
                if not api_key:
                    st.error("❌ Please enter Pexels API key!")
                else:
                    with st.spinner("Regenerating..."):
                        exclude = result.get("excluded_keywords", []) + result["keywords"]
                        out = process_scene(scene_text, api_key, search_capacity, min_height,
                                             target_width, target_height, platform, exclude_keywords=exclude)
                        result["keywords"] = out["keywords"] if out["keywords"] else result["keywords"]
                        result["results"] = out["results"]
                        result["total"] = out["total"]
                        result["excluded_keywords"] = exclude
                    st.rerun()

            if not result["results"]:
                st.warning("⚠️ No videos match your filters")
                continue

            cols = st.columns(min(4, len(result["results"])))
            for idx, col in enumerate(cols):
                if idx >= len(result["results"]):
                    continue
                item = result["results"][idx]
                video = item["video"]
                file = item["file"]
                with col:
                    video_url = file.get("link")
                    if media_type == "🖼️ Images Only":
                        st.image(video.get("image", ""), use_container_width=True)
                    else:
                        st.video(video_url)
                    st.caption(f"{file.get('width', '?')}×{file.get('height', '?')}")

                    filename = f"scene{scene_num}_{video.get('id')}.mp4"

                    # REAL single download button (fetches bytes, no round trip needed for zip later)
                    if st.button("⬇️ Prepare Download", key=f"prep_{scene_num}_{idx}"):
                        with st.spinner("Fetching video..."):
                            content = fetch_video_bytes(video_url)
                        if content:
                            st.download_button(
                                "💾 Save File",
                                data=content,
                                file_name=filename,
                                mime="video/mp4",
                                key=f"save_{scene_num}_{idx}"
                            )
                        else:
                            st.error("❌ Could not fetch video")

                    # Add to bulk ZIP selection
                    already_added = any(d["url"] == video_url for d in st.session_state.downloaded)
                    if not already_added:
                        if st.button("➕ Add to ZIP list", key=f"add_{scene_num}_{idx}"):
                            st.session_state.downloaded.append({"url": video_url, "filename": filename})
                            st.rerun()
                    else:
                        st.caption("✅ In ZIP list")

    # -----------------------------
    # BULK DOWNLOAD (real zip)
    # -----------------------------
    if st.session_state.all_results:
        st.markdown("---")
        st.subheader("📦 Bulk Download")
        st.info(f"📌 Selected: {len(st.session_state.downloaded)} videos for ZIP")

        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.downloaded and st.button("📦 Build ZIP now", use_container_width=True):
                with st.spinner("Downloading and zipping videos... this can take a while"):
                    zip_buffer = make_zip(st.session_state.downloaded)
                st.download_button(
                    "💾 Download ZIP",
                    data=zip_buffer,
                    file_name=f"broll_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        with col2:
            if st.button("🗑️ Clear ZIP Selection", use_container_width=True):
                st.session_state.downloaded = []
                st.rerun()

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

        with st.spinner("Searching..."):
            videos = search_pexels(keyword, api_key, per_page)

        if not videos:
            st.warning("⚠️ No videos found")
            st.stop()

        st.success(f"✅ Found {len(videos)} videos")

        for row_start in range(0, len(videos), 4):
            cols = st.columns(4)
            for col, video in zip(cols, videos[row_start:row_start + 4]):
                with col:
                    video_files = video.get("video_files", [])
                    selected_file = next((f for f in video_files if f.get("height", 0) >= min_height), None)
                    if selected_file is None and video_files:
                        selected_file = video_files[0]
                    if selected_file:
                        video_url = selected_file.get("link")
                        if media_type == "🖼️ Images Only":
                            st.image(video.get("image", ""), use_container_width=True)
                        else:
                            st.video(video_url)
                        st.caption(f"{selected_file.get('width', '?')}×{selected_file.get('height', '?')}")

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🎬 B-Roll Finder Pro v1.3")
with col2:
    st.caption("⚡ Powered by Pexels API")
with col3:
    st.caption(f"📊 {len(st.session_state.downloaded)} clips in ZIP list")
