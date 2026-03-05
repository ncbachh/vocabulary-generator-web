import streamlit as st
import io
import sys
import os
import re

# Ensure src is in path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from docx_logic import create_vocabulary_docx
from streamlit_local_storage import LocalStorage

st.set_page_config(page_title="Vocabulary Generator", page_icon="📝")

def is_valid_filename(filename):
    # Characters not allowed in Windows/Unix filenames
    invalid_chars = r'[\\/:*?"<>|]'
    if re.search(invalid_chars, filename):
        return False
    return True

def main():
    st.title("📝 Vocabulary Generator")
    st.markdown("""
    Convert your list of English words into a professionally formatted Word document with definitions, 
    pronunciations, and examples from the Oxford Learner's Dictionary.
    """)

    # Initialize LocalStorage
    local_storage = LocalStorage()

    # Sidebar for Settings
    st.sidebar.title("Settings")
    use_vi = st.sidebar.checkbox("Enable Vietnamese Translation", value=False, help="Use AI to translate English definitions into Vietnamese.")
    
    api_key = ""
    if use_vi:
        # Check for secret first, otherwise show input
        api_key = st.sidebar.text_input("OpenRouter API Key", type="password", help="Get your key from https://openrouter.ai/keys")
        if not api_key and "OPENROUTER_API_KEY" in st.secrets:
            api_key = st.secrets["OPENROUTER_API_KEY"]
            st.sidebar.info("Using API key from secrets.")
        elif not api_key:
            st.sidebar.warning("Please enter your OpenRouter API Key to enable translation.")

    # Initialize session state
    if "docx_file" not in st.session_state:
        st.session_state.docx_file = None
    if "failed_words" not in st.session_state:
        st.session_state.failed_words = []
    if "word_input" not in st.session_state:
        st.session_state.word_input = ""
    if "storage_loaded" not in st.session_state:
        st.session_state.storage_loaded = False
    
    # Load saved words from local storage on startup
    if not st.session_state.storage_loaded:
        try:
            saved_val = local_storage.getItem("vocabulary_words")
            # If saved_val is not None, the component has responded (even if it's an empty string)
            if saved_val is not None:
                if saved_val: # Only update if there is actual data to restore
                    st.session_state.word_input = saved_val
                st.session_state.storage_loaded = True
                st.rerun()
            elif st.session_state.word_input != "":
                # If the user started typing before storage responded, stop trying to load
                # to prevent overwriting their new work with old (or empty) data.
                st.session_state.storage_loaded = True
        except:
            st.session_state.storage_loaded = True

    # Input Section
    st.subheader("1. Enter Words")
    
    # Use key for the widget to manage its own state in session_state
    word_input = st.text_area(
        "Enter words (one per line):", 
        height=200, 
        placeholder="apple\nbanana\ncherry",
        key="word_input"
    )
    
    # Update local storage if input changes
    if "last_persisted_words" not in st.session_state:
        st.session_state.last_persisted_words = None

    if st.session_state.word_input != st.session_state.last_persisted_words:
        local_storage.setItem("vocabulary_words", st.session_state.word_input)
        st.session_state.last_persisted_words = st.session_state.word_input

    words = [w.strip() for w in word_input.split('\n') if w.strip()]
    
    col1, col2 = st.columns([1, 4])
    with col1:
        filename_base = st.text_input("Filename:", value="vocabulary", placeholder="e.g. my_words")

    with col2:
        st.write("") # Spacer
        st.write("") # Spacer
        generate_btn = st.button("Generate Document", type="primary", disabled=not words)

    if generate_btn:
        # Validations
        if not filename_base.strip():
            st.error("❌ Filename is required.")
            return

        if not is_valid_filename(filename_base):
            st.error('❌ Invalid filename. Please avoid using special characters: \\ / : * ? " < > |')
            return
            
        if use_vi and not api_key:
            st.error("❌ OpenRouter API Key is required for Vietnamese translation.")
            return

        st.session_state.docx_file = None
        st.session_state.failed_words = []
        
        doc_title = filename_base.upper()
        
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        def update_progress(current, total, word, status):
            percent = (current + 1) / total
            progress_bar.progress(percent)
            status_text.text(f"{status}: {word} ({current + 1}/{total})")

        try:
            with st.spinner("Fetching data and generating document..."):
                doc, failed_words = create_vocabulary_docx(
                    words, 
                    title=doc_title, 
                    use_vi_translation=use_vi, 
                    api_key=api_key,
                    progress_callback=update_progress
                )
                
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                st.session_state.docx_file = buffer
                st.session_state.failed_words = failed_words
                st.session_state.final_filename = filename_base + ".docx" if not filename_base.lower().endswith(".docx") else filename_base
                
            st.success("Generation complete!")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    # Output Section
    if st.session_state.docx_file:
        st.divider()
        st.subheader("2. Download Result")
        
        if st.session_state.failed_words:
            st.warning(f"Could not process the following words: {', '.join(st.session_state.failed_words)}")
        
        st.download_button(
            label="Download .docx File",
            data=st.session_state.docx_file,
            file_name=st.session_state.get("final_filename", "vocabulary.docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

if __name__ == "__main__":
    main()
