import streamlit as st
import requests
import re
import io
import json
import time
import zipfile
import os
from datetime import datetime
from typing import List, Dict, Any

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
        .stAlert {display: none;}
        .stSpinner {display: none;}
        .st-emotion-cache-1v0mbdj {display: none;}
        .st-emotion-cache-18ni7ap {display: none;}
        .st-emotion-cache-1j6wv82 {display: none;}
        .stApp {
            background: #0e1117;
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
        .stButton > button {
            background: #ff4b4b;
            color: white;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .stButton > button:hover {
            background: #ff6b6b;
            transform: scale(1.02);
        }
        .video-container {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            margin-bottom: 15px;
        }
        .scene-card {
            background: #1e1e1e;
            padding: 15px;
            border-radius: 12px;
            border-left: 4px solid #ff4b4b;
            margin-bottom: 10px;
        }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# -----------------------------
# SESSION STATE INITIALIZATION
# -----------------------------
if 'search_history' not in st.session_state:
    st.session_state.search_history = {}
if 'downloaded' not in st.session_state:
    st.session_state.downloaded = []
if 'scene_results' not in st.session_state:
    st.session_state.scene_results = []
if 'project_data' not in st.session_state:
    st.session_state.project_data = {}
if 'current_scenes' not in st.session_state:
    st.session_state.current_scenes = []
if 'selected_scenes' not in st.session_state:
    st.session_state.selected_scenes = set()

# -----------------------------
# AI KEYWORD GENERATION (Simulated)
# -----------------------------
def generate_ai_keywords(scene_text: str) -> List[str]:
    """
    Generate relevant keywords from scene text using AI-like processing
    """
    # Common B-roll keywords mapping
    keyword_map = {
        'business': ['office', 'meeting', 'corporate', 'professional', 'executive', 'boardroom'],
        'economy': ['finance', 'stock market', 'trading', 'business', 'money', 'bank'],
        'technology': ['tech', 'digital', 'computer', 'innovation', 'code', 'ai', 'robot'],
        'nature': ['forest', 'ocean', 'mountain', 'sunset', 'wildlife', 'flowers'],
        'city': ['urban', 'street', 'architecture', 'traffic', 'skyscraper', 'night'],
        'people': ['crowd', 'walking', 'interaction', 'diverse', 'community', 'portrait'],
        'health': ['hospital', 'doctor', 'fitness', 'wellness', 'medicine', 'care'],
        'education': ['school', 'student', 'teacher', 'learning', 'classroom', 'knowledge'],
        'food': ['restaurant', 'cooking', 'cuisine', 'dining', 'chef', 'ingredients'],
        'travel': ['tourist', 'landmark', 'adventure', 'explore', 'culture', 'vacation'],
        'sports': ['fitness', 'athlete', 'game', 'competition', 'team', 'training'],
        'fashion': ['style', 'design', 'clothing', 'model', 'runway', 'elegant'],
        'music': ['concert', 'instrument', 'performance', 'band', 'studio', 'rhythm'],
        'art': ['creative', 'painting', 'museum', 'sculpture', 'exhibition', 'colorful'],
        'family': ['home', 'children', 'together', 'love', 'bonding', 'happy'],
        'wedding': ['ceremony', 'couple', 'romance', 'reception', 'flowers', 'decor'],
        'realestate': ['building', 'construction', 'property', 'architecture', 'urban'],
        'automotive': ['car', 'vehicle', 'drive', 'road', 'transportation', 'speed']
    }
    
    # Extract main keywords from text
    words = re.findall(r'\b[a-zA-Z]{4,}\b', scene_text.lower())
    
    # Check for keyword matches
    found_keywords = []
    for word in words:
        for category, keywords in keyword_map.items():
            if word in category or any(keyword in scene_text.lower() for keyword in keywords[:2]):
                found_keywords.extend(keywords[:3])
                break
    
    # If no keywords found, use default
    if not found_keywords:
        found_keywords = ['modern', 'people', 'technology', 'work']
    
    # Return unique keywords (max 5)
    unique_keywords = list(set(found_keywords))[:5]
    return unique_keywords

# -----------------------------
# MULTIPLE STOCK SOURCES
# -----------------------------
def search_pexels_videos(query: str, api_key: str, per_page: int = 12) -> List[Dict]:
    """Search videos on Pexels"""
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": min(per_page, 80)
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            return videos
    except Exception as e:
        st.warning(f"⚠️ Pexels API error: {str(e)}")
    return []

def search_pixabay_videos(query: str, api_key: str, per_page: int = 12) -> List[Dict]:
    """Search videos on Pixabay (free alternative)"""
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": api_key,
        "q": query,
        "per_page": per_page
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("hits", [])
    except:
        pass
    return []

def search_combined_sources(query: str, source_type: str, api_keys: Dict, per_page: int = 12) -> List[Dict]:
    """Search across multiple stock sources"""
    results = []
    
    if source_type in ["pexels", "both"] and api_keys.get("pexels"):
        pexels_results = search_pexels_videos(query, api_keys["pexels"], per_page)
        # Convert to common format
        for video in pexels_results:
            if "video_files" in video:
                video["source"] = "pexels"
                results.append(video)
    
    if source_type in ["pixabay", "both"] and api_keys.get("pixabay"):
        pixabay_results = search_pixabay_videos(query, api_keys["pixabay"], per_page)
        # Convert to common format
        for video in pixabay_results:
            if "videos" in video:
                video["source"] = "pixabay"
                results.append(video)
    
    return results

# -----------------------------
# SCRIPT SPLITTING FUNCTIONS
# -----------------------------
def split_script_into_scenes(script: str, method: str, max_scenes: int = 10) -> List[str]:
    """
    Split script into scenes based on selected method
    """
    if not script.strip():
        return []
    
    if method == "Sentence":
        # Split by sentence boundaries
        sentences = [s.strip() for s in re.split(r'[.!?]+', script) if s.strip()]
        scenes = sentences[:max_scenes]
    
    elif method == "2 Sentences":
        sentences = [s.strip() for s in re.split(r'[.!?]+', script) if s.strip()]
        scenes = [' '.join(sentences[i:i+2]) for i in range(0, len(sentences), 2)][:max_scenes]
    
    elif method == "3 Sentences":
        sentences = [s.strip() for s in re.split(r'[.!?]+', script) if s.strip()]
        scenes = [' '.join(sentences[i:i+3]) for i in range(0, len(sentences), 3)][:max_scenes]
    
    elif method == "Paragraph":
        scenes = [p.strip() for p in script.split('\n') if p.strip()][:max_scenes]
    
    elif method == "AI Auto-Split":
        # Use AI-like splitting (smart segmentation)
        scenes = smart_scene_splitting(script, max_scenes)
    
    else:
        scenes = [script[:500]]  # Default: first 500 chars
    
    return scenes

def smart_scene_splitting(script: str, max_scenes: int = 10) -> List[str]:
    """
    Smart scene splitting using AI-like analysis
    """
    sentences = [s.strip() for s in re.split(r'[.!?]+', script) if s.strip()]
    
    if len(sentences) <= max_scenes:
        return sentences
    
    # Group sentences by topic (simplified)
    scenes = []
    current_scene = []
    topic_changes = 0
    
    for sentence in sentences:
        current_scene.append(sentence)
        
        # Check for topic change indicators
        if any(word in sentence.lower() for word in ['meanwhile', 'however', 'additionally', 'finally']):
            topic_changes += 1
        
        # Create scene when topic changes or enough sentences
        if topic_changes >= 2 or len(current_scene) >= 3:
            if current_scene:
                scenes.append(' '.join(current_scene))
                current_scene = []
                topic_changes = 0
        
        if len(scenes) >= max_scenes:
            break
    
    # Add remaining sentences
    if current_scene and len(scenes) < max_scenes:
        scenes.append(' '.join(current_scene))
    
    return scenes[:max_scenes]

# -----------------------------
# SCENE PROCESSING
# -----------------------------
def process_scenes(scenes: List[str], settings: Dict) -> List[Dict]:
    """
    Process all scenes to find matching B-roll footage
    """
    results = []
    total_scenes = len(scenes)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, scene in enumerate(scenes):
        status_text.text(f"🔄 Processing scene {idx+1}/{total_scenes}...")
        
        # Generate keywords
        if settings.get('use_ai_keywords', True):
            keywords = generate_ai_keywords(scene)
        else:
            # Extract simple keywords
            words = re.findall(r'\b[a-zA-Z]{4,}\b', scene)
            keywords = list(set([w.lower() for w in words]))[:5]
        
        # Search for videos
        api_keys = {
            "pexels": settings.get('pexels_api_key', ''),
            "pixabay": settings.get('pixabay_api_key', '')
        }
        
        source = settings.get('stock_source', 'pexels')
        per_page = settings.get('videos_per_scene', 12)
        
        all_videos = []
        for keyword in keywords[:3]:  # Limit to first 3 keywords
            videos = search_combined_sources(keyword, source, api_keys, per_page // 2)
            all_videos.extend(videos)
        
        # Remove duplicates
        seen = set()
        unique_videos = []
        for video in all_videos:
            video_id = video.get('id', '')
            if video_id and video_id not in seen:
                seen.add(video_id)
                unique_videos.append(video)
        
        # Filter by resolution and aspect ratio
        filtered_videos = filter_videos_by_settings(unique_videos, settings)
        
        # Save scene result
        scene_result = {
            'scene_num': idx + 1,
            'scene_text': scene,
            'keywords': keywords,
            'videos': filtered_videos[:per_page],
            'total_found': len(filtered_videos),
            'selected': False
        }
        
        results.append(scene_result)
        
        # Update progress
        progress_bar.progress((idx + 1) / total_scenes)
    
    progress_bar.empty()
    status_text.empty()
    
    return results

def filter_videos_by_settings(videos: List[Dict], settings: Dict) -> List[Dict]:
    """
    Filter videos by resolution, aspect ratio, and duration
    """
    filtered = []
    min_height = settings.get('min_height', 720)
    target_ratio = settings.get('target_ratio', 1.78)  # 16:9 default
    duration_filter = settings.get('duration', 'Any')
    
    for video in videos:
        # Extract video files
        video_files = video.get('video_files', [])
        if not video_files:
            continue
        
        for file in video_files:
            height = file.get('height', 0)
            width = file.get('width', 0)
            
            # Resolution filter
            if height < min_height:
                continue
            
            # Aspect ratio filter
            if height > 0:
                file_ratio = width / height
                if abs(file_ratio - target_ratio) > 0.2:  # 20% tolerance
                    continue
            
            # Duration filter
            if duration_filter != 'Any':
                duration = video.get('duration', 0)
                if duration_filter == '5-10 sec' and not (5 <= duration <= 10):
                    continue
                elif duration_filter == '10-20 sec' and not (10 <= duration <= 20):
                    continue
                elif duration_filter == '20-30 sec' and not (20 <= duration <= 30):
                    continue
                elif duration_filter == '30-60 sec' and not (30 <= duration <= 60):
                    continue
                elif duration_filter == '60+ sec' and duration < 60:
                    continue
            
            # Add video with selected file
            video['selected_file'] = file
            filtered.append(video)
            break
    
    # Sort by resolution (highest first)
    filtered.sort(key=lambda x: x.get('selected_file', {}).get('height', 0), reverse=True)
    
    return filtered

# -----------------------------
# ZIP EXPORT FUNCTION
# -----------------------------
def create_zip_export(scenes_data: List[Dict], selected_only: bool = True) -> bytes:
    """
    Create a ZIP file with selected videos and metadata
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add metadata
        metadata = {
            'project_name': st.session_state.get('project_name', 'B-Roll_Project'),
            'created_date': datetime.now().isoformat(),
            'total_scenes': len(scenes_data),
            'scenes': []
        }
        
        video_count = 0
        for scene in scenes_data:
            if selected_only and not scene.get('selected', False):
                continue
            
            scene_metadata = {
                'scene_num': scene['scene_num'],
                'scene_text': scene['scene_text'],
                'keywords': scene['keywords'],
                'videos': []
            }
            
            for video in scene['videos'][:3]:  # Max 3 per scene for ZIP
                video_url = video.get('selected_file', {}).get('link', '')
                if video_url:
                    # Download video
                    try:
                        response = requests.get(video_url, timeout=60)
                        if response.status_code == 200:
                            # Get filename
                            filename = f"scene_{scene['scene_num']}_video_{video_count+1}.mp4"
                            zip_file.writestr(filename, response.content)
                            video_count += 1
                            
                            scene_metadata['videos'].append({
                                'filename': filename,
                                'source': video.get('source', 'unknown'),
                                'resolution': f"{video.get('selected_file', {}).get('width', '?')}x{video.get('selected_file', {}).get('height', '?')}"
                            })
                    except:
                        pass
            
            metadata['scenes'].append(scene_metadata)
        
        # Save metadata
        zip_file.writestr('project_metadata.json', json.dumps(metadata, indent=2))
        
        # Add readme
        readme = f"""
# B-Roll Project: {metadata['project_name']}
Created: {metadata['created_date']}

## Summary
- Total Scenes: {len(scenes_data)}
- Videos Downloaded: {video_count}

## Instructions
1. Import these videos into your video editor
2. Use the scene numbers to match with your script
3. Adjust timing as needed

## Sources
Videos sourced from Pexels, Pixabay, and other stock providers.
        """
        zip_file.writestr('README.txt', readme)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# -----------------------------
# SAVE/LOAD PROJECT
# -----------------------------
def save_project(project_name: str, scenes_data: List[Dict]) -> Dict:
    """
    Save project data to session state
    """
    project = {
        'name': project_name,
        'created': datetime.now().isoformat(),
        'scenes': scenes_data,
        'settings': {
            'resolution': st.session_state.get('resolution', '720p'),
            'platform': st.session_state.get('platform', 'YouTube')
        }
    }
    
    st.session_state.project_data[project_name] = project
    return project

def load_project(project_name: str) -> List[Dict]:
    """
    Load project data from session state
    """
    if project_name in st.session_state.project_data:
        project = st.session_state.project_data[project_name]
        return project.get('scenes', [])
    return []

# -----------------------------
# REGENERATE SCENE FUNCTION
# -----------------------------
def regenerate_scene(scene_data: Dict, settings: Dict) -> Dict:
    """
    Regenerate a specific scene with new keywords
    """
    scene_text = scene_data['scene_text']
    
    # Generate new keywords
    new_keywords = generate_ai_keywords(scene_text)
    
    # Search for new videos
    api_keys = {
        "pexels": settings.get('pexels_api_key', ''),
        "pixabay": settings.get('pixabay_api_key', '')
    }
    
    source = settings.get('stock_source', 'pexels')
    per_page = settings.get('videos_per_scene', 12)
    
    all_videos = []
    for keyword in new_keywords[:3]:
        videos = search_combined_sources(keyword, source, api_keys, per_page // 2)
        all_videos.extend(videos)
    
    # Filter and return
    filtered_videos = filter_videos_by_settings(all_videos, settings)
    
    scene_data['keywords'] = new_keywords
    scene_data['videos'] = filtered_videos[:per_page]
    scene_data['total_found'] = len(filtered_videos)
    scene_data['regenerated'] = True
    
    return scene_data

# -----------------------------
# DISPLAY SCENE RESULTS FUNCTION
# -----------------------------
def display_scene_results(results: List[Dict]):
    """
    Display scene results in a nice grid layout with selection and regeneration options
    """
    if not results:
        return
    
    # Bulk actions
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("✅ Select All", use_container_width=True):
            for scene in results:
                scene['selected'] = True
            st.rerun()
    with col2:
        if st.button("❌ Deselect All", use_container_width=True):
            for scene in results:
                scene['selected'] = False
            st.rerun()
    with col3:
        selected_count = sum(1 for s in results if s.get('selected', False))
        st.info(f"Selected: {selected_count}/{len(results)}")
    with col4:
        if selected_count > 0:
            if st.button("📦 Download Selected as ZIP", use_container_width=True):
                with st.spinner("Creating ZIP file..."):
                    zip_data = create_zip_export(results, selected_only=True)
                    st.download_button(
                        label="⬇️ Download ZIP",
                        data=zip_data,
                        file_name=f"broll_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
    
    # Display each scene
    for idx, scene_result in enumerate(results):
        scene_num = scene_result['scene_num']
        scene_text = scene_result['scene_text']
        videos = scene_result['videos']
        total_found = scene_result['total_found']
        keywords = scene_result['keywords']
        is_selected = scene_result.get('selected', False)
        
        # Scene header with selection
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            with st.expander(f"🎬 Scene {scene_num}: {scene_text[:60]}...", expanded=(idx==0)):
                # Scene details
                st.markdown(f"<div class='scene-card'>", unsafe_allow_html=True)
                st.caption(f"**Full Scene:** {scene_text}")
                st.caption(f"**Keywords:** {', '.join(keywords)}")
                st.caption(f"**Videos Found:** {total_found}")
                st.markdown("</div>", unsafe_allow_html=True)
                
                if not videos:
                    st.warning("⚠️ No videos match your filters")
                    continue
                
                # Display videos in grid
                cols = st.columns(min(4, len(videos)))
                for col_idx, col in enumerate(cols):
                    if col_idx < len(videos):
                        video = videos[col_idx]
                        selected_file = video.get('selected_file', {})
                        video_url = selected_file.get('link', '')
                        
                        with col:
                            if video_url:
                                st.video(video_url)
                                st.caption(f"🎬 {selected_file.get('width', '?')}×{selected_file.get('height', '?')}")
                                st.caption(f"📦 {video.get('source', 'unknown')}")
                                
                                # Download button
                                if st.button(f"⬇️ Download", key=f"dl_scene{scene_num}_vid{col_idx}"):
                                    st.session_state.downloaded.append(video_url)
                                    st.success("✅ Added to download list")
        with col2:
            # Selection checkbox
            selected = st.checkbox("✅ Select", value=is_selected, key=f"sel_{scene_num}")
            scene_result['selected'] = selected
        with col3:
            # Regenerate button
            if st.button("🔄 Regenerate", key=f"reg_{scene_num}"):
                with st.spinner("Regenerating scene..."):
                    settings = {
                        'pexels_api_key': pexels_api_key,
                        'pixabay_api_key': pixabay_api_key,
                        'stock_source': stock_source.lower(),
                        'videos_per_scene': videos_per_scene,
                        'use_ai_keywords': use_ai_keywords,
                        'min_height': min_height,
                        'target_ratio': target_ratio,
                        'duration': duration
                    }
                    new_scene = regenerate_scene(scene_result, settings)
                    results[idx] = new_scene
                    st.success("✅ Scene regenerated!")
                    st.rerun()

# -----------------------------
# MAIN APP LAYOUT
# -----------------------------
st.title("🎬 B-Roll Finder Pro")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Keys
    with st.expander("🔑 API Keys", expanded=True):
        pexels_api_key = st.text_input(
            "Pexels API Key",
            value="AbqSkVbZko07cGsPYZbQgm7SVvwhKPqqYV8bYZs254tAF5OKHcFBQHQl",
            type="password"
        )
        
        pixabay_api_key = st.text_input(
            "Pixabay API Key (Optional)",
            value="",
            type="password",
            help="Get free API key from pixabay.com"
        )
    
    # Stock Source
    stock_source = st.selectbox(
        "📦 Stock Source",
        ["Pexels", "Pixabay", "Both"],
        index=0
    )
    
    # Search Settings
    with st.expander("🎯 Search Settings", expanded=True):
        videos_per_scene = st.slider(
            "Videos per scene",
            min_value=1,
            max_value=20,
            value=10
        )
        
        use_ai_keywords = st.checkbox("🧠 AI Keyword Generation", value=True)
    
    # Resolution
    resolution = st.selectbox(
        "📐 Resolution",
        ["440p", "720p", "1080p", "4K", "8K"],
        index=1
    )
    
    resolution_map = {
        "440p": 440,
        "720p": 720,
        "1080p": 1080,
        "4K": 2160,
        "8K": 4320
    }
    min_height = resolution_map[resolution]
    
    # Platform/Aspect Ratio
    platform = st.selectbox(
        "📱 Platform",
        ["YouTube (16:9)", "Instagram Reels (9:16)", "YouTube Shorts (9:16)", 
         "Instagram Feed (1:1)", "Facebook (16:9)", "Custom"]
    )
    
    aspect_ratios = {
        "YouTube (16:9)": 16/9,
        "Instagram Reels (9:16)": 9/16,
        "YouTube Shorts (9:16)": 9/16,
        "Instagram Feed (1:1)": 1,
        "Facebook (16:9)": 16/9,
    }
    
    if platform == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            custom_w = st.number_input("Width", value=1920)
        with col2:
            custom_h = st.number_input("Height", value=1080)
        target_ratio = custom_w / custom_h if custom_h > 0 else 16/9
    else:
        target_ratio = aspect_ratios.get(platform, 16/9)
    
    # Duration
    duration = st.selectbox(
        "⏱️ Duration",
        ["Any", "5-10 sec", "10-20 sec", "20-30 sec", "30-60 sec", "60+ sec"]
    )

# Main Tabs
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "📝 Script Mode",
    "🔍 Keyword Mode",
    "📂 Projects",
    "📊 History"
])

# -----------------------------
# TAB 1: SCRIPT MODE
# -----------------------------
with main_tab1:
    st.subheader("📝 Script to B-Roll")
    
    # Script Input
    script_input = st.text_area(
        "Paste your script here",
        placeholder="Write or paste your video script here...\n\nExample:\nIn 2020, the global economy faced an unprecedented crisis. Stock markets crashed worldwide. Businesses struggled to survive. Governments introduced stimulus packages.",
        height=200
    )
    
    # Split Settings
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        split_method = st.selectbox(
            "🔪 Split Method",
            ["Sentence", "2 Sentences", "3 Sentences", "Paragraph", "AI Auto-Split"],
            index=0
        )
    with col2:
        max_scenes = st.number_input("Max Scenes", min_value=1, max_value=30, value=10)
    with col3:
        project_name = st.text_input("Project Name", value=f"Project_{datetime.now().strftime('%Y%m%d')}")
    
    # Process Button
    process_button = st.button("🚀 Generate B-Roll", type="primary", use_container_width=True)
    
    if process_button:
        if not script_input.strip():
            st.error("❌ Please paste a script first!")
            st.stop()
        
        if not pexels_api_key:
            st.error("❌ Please enter Pexels API key!")
            st.stop()
        
        # Split script
        scenes = split_script_into_scenes(script_input, split_method, max_scenes)
        
        if not scenes:
            st.error("❌ No scenes found in script!")
            st.stop()
        
        st.success(f"✅ Split into {len(scenes)} scenes")
        
        # Process scenes
        settings = {
            'pexels_api_key': pexels_api_key,
            'pixabay_api_key': pixabay_api_key,
            'stock_source': stock_source.lower(),
            'videos_per_scene': videos_per_scene,
            'use_ai_keywords': use_ai_keywords,
            'min_height': min_height,
            'target_ratio': target_ratio,
            'duration': duration
        }
        
        results = process_scenes(scenes, settings)
        st.session_state.scene_results = results
        st.session_state.current_scenes = results
        
        # Save project automatically
        save_project(project_name, results)
        
        # Display results
        st.success(f"✅ Found videos for all {len(results)} scenes!")
        
        # Show results
        display_scene_results(results)

# -----------------------------
# TAB 2: KEYWORD MODE
# -----------------------------
with main_tab2:
    st.subheader("🔍 Search by Keyword")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        keyword_input = st.text_input("Enter keyword", placeholder="business meeting, nature, technology...")
    with col2:
        keyword_results = st.number_input("Results", min_value=1, max_value=80, value=12)
    
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if not keyword_input.strip():
            st.error("❌ Please enter a keyword")
            st.stop()
        
        if not pexels_api_key:
            st.error("❌ Please enter Pexels API key")
            st.stop()
        
        with st.spinner(f"Searching for '{keyword_input}'..."):
            # Search across sources
            api_keys = {"pexels": pexels_api_key, "pixabay": pixabay_api_key}
            videos = search_combined_sources(keyword_input, stock_source.lower(), api_keys, keyword_results)
            
            # Filter by settings
            settings = {
                'min_height': min_height,
                'target_ratio': target_ratio,
                'duration': duration
            }
            filtered_videos = filter_videos_by_settings(videos, settings)
        
        if not filtered_videos:
            st.warning("⚠️ No videos found matching your criteria")
            st.stop()
        
        st.success(f"✅ Found {len(filtered_videos)} videos")
        
        # Display in grid
        for row_start in range(0, len(filtered_videos), 4):
            cols = st.columns(4)
            for col, video in zip(cols, filtered_videos[row_start:row_start+4]):
                with col:
                    selected_file = video.get('selected_file', {})
                    video_url = selected_file.get('link', '')
                    
                    if video_url:
                        st.video(video_url)
                        st.caption(f"🎬 {selected_file.get('width', '?')}×{selected_file.get('height', '?')}")
                        
                        if st.button(f"⬇️ Download", key=f"kw_dl_{video.get('id', '')}"):
                            st.session_state.downloaded.append(video_url)
                            st.success("✅ Added to download list")

# -----------------------------
# TAB 3: PROJECTS
# -----------------------------
with main_tab3:
    st.subheader("📂 Saved Projects")
    
    if st.session_state.project_data:
        project_names = list(st.session_state.project_data.keys())
        selected_project = st.selectbox("Select Project", project_names)
        
        if selected_project:
            project_data = st.session_state.project_data[selected_project]
            st.info(f"📁 **{selected_project}** | Created: {project_data.get('created', 'Unknown')}")
            
            scenes = project_data.get('scenes', [])
            st.write(f"**{len(scenes)} scenes** | {sum(len(s.get('videos', [])) for s in scenes)} videos total")
            
            if st.button("📂 Load Project"):
                st.session_state.scene_results = scenes
                st.session_state.current_scenes = scenes
                st.success("✅ Project loaded successfully!")
                
                # Display loaded scenes
                for scene in scenes:
                    with st.expander(f"🎬 Scene {scene['scene_num']}: {scene['scene_text'][:50]}..."):
                        st.caption(f"**Keywords:** {', '.join(scene['keywords'])}")
                        st.caption(f"**Videos:** {scene['total_found']}")
                        
                        # Show first video
                        if scene['videos']:
                            first_video = scene['videos'][0]
                            video_file = first_video.get('selected_file', {})
                            if video_file.get('link'):
                                st.video(video_file['link'])
    else:
        st.info("💡 No saved projects yet. Generate B-Roll in Script Mode to create one!")

# -----------------------------
# TAB 4: HISTORY
# -----------------------------
with main_tab4:
    st.subheader("📊 History & Downloads")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("📌 Selected Videos", len(st.session_state.downloaded))
        st.metric("🎬 Total Videos Found", sum(s.get('total_found', 0) for s in st.session_state.scene_results))
    
    with col2:
        st.metric("📁 Scenes Processed", len(st.session_state.scene_results))
        st.metric("🔄 Regenerations", sum(1 for s in st.session_state.scene_results if s.get('regenerated', False)))
    
    # Download list
    if st.session_state.downloaded:
        st.subheader("📥 Download Queue")
        for i, url in enumerate(st.session_state.downloaded[-5:]):  # Show last 5
            st.caption(f"{i+1}. {url[:50]}...")
        
        if st.button("🗑️ Clear All Downloads"):
            st.session_state.downloaded = []
            st.success("✅ Cleared download queue")
    else:
        st.info("💡 No videos in download queue")

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🎬 B-Roll Finder Pro v2.0")
with col2:
    st.caption("⚡ Powered by Pexels & Pixabay")
with col3:
    st.caption(f"📊 {len(st.session_state.downloaded)} clips selected")
