import streamlit as st
import requests

st.set_page_config(page_title="B-Roll Test", layout="wide")

st.title("🔧 B-Roll Test - Debug Mode")

# API Key
api_key = st.text_input("Pexels API Key", type="password")

keyword = st.text_input("Search Keyword", value="business meeting")

if st.button("🔍 Test Search"):
    if not api_key:
        st.error("❌ API key daalo!")
        st.stop()
    
    if not keyword:
        st.error("❌ Keyword daalo!")
        st.stop()
    
    # Show what we're sending
    st.write("📤 **Sending Request:**")
    st.code(f"URL: https://api.pexels.com/videos/search?query={keyword}&per_page=5")
    
    # Make request
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": keyword, "per_page": 5}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        st.write("📥 **Response Status:**", response.status_code)
        
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            
            st.success(f"✅ {len(videos)} videos found!")
            
            # Show first video details
            if videos:
                first = videos[0]
                st.write("**First Video Details:**")
                st.json({
                    "id": first.get("id"),
                    "duration": first.get("duration"),
                    "video_files": len(first.get("video_files", [])),
                    "image": first.get("image", "No thumbnail")
                })
                
                # Try to show video
                video_files = first.get("video_files", [])
                for file in video_files:
                    height = file.get("height", 0)
                    width = file.get("width", 0)
                    st.write(f"🎬 {width}x{height} - {file.get('link', 'No link')[:50]}...")
                    
                    if height >= 720:
                        st.video(file.get("link"))
                        break
            else:
                st.warning("⚠️ No videos found for this keyword")
        else:
            st.error(f"❌ API Error: {response.status_code}")
            st.write("**Response:**", response.text)
            
    except Exception as e:
        st.error(f"❌ Connection Error: {str(e)}")

st.markdown("---")
st.caption("🔧 Debug Mode - Check your API key and connection")
