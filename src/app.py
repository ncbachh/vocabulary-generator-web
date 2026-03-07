import streamlit as st
import io
import sys
import os
import re
import time
import uuid

# Ensure src is in path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from docx_logic import fetch_word_data, translate_meaning_to_vi, generate_docx_from_data
from streamlit_local_storage import LocalStorage

st.set_page_config(page_title="Vocabulary Generator", page_icon="📝", layout="wide")

def is_valid_filename(filename):
    invalid_chars = r'[\\/:*?"<>|]'
    if re.search(invalid_chars, filename):
        return False
    return True

def flatten_senses(word, senses):
    """Converts nested senses into flat rows for the data editor."""
    rows = []
    if not senses:
        rows.append({
            "id": str(uuid.uuid4()),
            "word": word,
            "pos": "",
            "ipa": "",
            "meaning": "",
            "examples": "",
            "translation": "",
            "status": "❌ Not Found",
            "last_fetched_word": word
        })
    else:
        for sense in senses:
            info = sense.get('word_info', {})
            m_data = sense.get('meaning_data', {})
            
            # Construct full meaning text including prefix and cf
            meaning_text = ""
            if m_data.get('prefix'):
                meaning_text += m_data['prefix'] + " "
            meaning_text += m_data.get('def', '')
            
            rows.append({
                "id": str(uuid.uuid4()),
                "word": word,
                "pos": info.get('pos', ''),
                "ipa": f"{info.get('ipa_bre', '')} {info.get('ipa_ame', '')}".strip(),
                "cf": m_data.get('cf', ''),
                "meaning": meaning_text,
                "examples": sense.get('examples', ''),
                "translation": sense.get('vi_translation', ''),
                "status": "✅ Synced",
                "last_fetched_word": word
            })
    return rows

def reconstruct_data_for_docx(df_rows):
    """Groups flat rows back into (word, senses) structure for docx generation."""
    reconstructed = []
    current_word = None
    current_senses = []
    
    for row in df_rows:
        word = row['word'].strip().lower()
        
        # Sense data structure matching docx_logic expectations
        # Handle IPA split
        ipa_parts = row['ipa'].split()
        ipa_bre = ipa_parts[0] if len(ipa_parts) > 0 else ""
        ipa_ame = ipa_parts[1] if len(ipa_parts) > 1 else ""
        
        sense = {
            "word_info": {
                "pos": row.get('pos', ''),
                "ipa_bre": ipa_bre,
                "ipa_ame": ipa_ame
            },
            "meaning_data": {
                "cf": row.get('cf', ''),
                "prefix": "", # We merged prefix into meaning for editing
                "def": row.get('meaning', '')
            },
            "examples": row.get('examples', ''),
            "vi_translation": row.get('translation', '')
        }
        
        if word == current_word:
            current_senses.append(sense)
        else:
            if current_word is not None:
                reconstructed.append((current_word, current_senses))
            current_word = word
            current_senses = [sense]
            
    if current_word is not None:
        reconstructed.append((current_word, current_senses))
        
    return reconstructed

def main():
    st.title("📝 Vocabulary Generator")
    
    # Initialize LocalStorage
    local_storage = LocalStorage()

    # Sidebar for Settings
    st.sidebar.title("Settings")
    use_vi = st.sidebar.checkbox("Enable Vietnamese Translation", value=False)
    
    api_key = ""
    if use_vi:
        api_key = st.sidebar.text_input("OpenRouter API Key", type="password")
        if not api_key and "OPENROUTER_API_KEY" in st.secrets:
            api_key = st.secrets["OPENROUTER_API_KEY"]
            st.sidebar.info("Using API key from secrets.")

    # Initialize session state
    if "vocab_data" not in st.session_state:
        st.session_state.vocab_data = []
    if "word_input" not in st.session_state:
        st.session_state.word_input = ""
    if "storage_loaded" not in st.session_state:
        st.session_state.storage_loaded = False
    
    # Load saved words from local storage
    if not st.session_state.storage_loaded:
        try:
            saved_val = local_storage.getItem("vocabulary_words")
            if saved_val is not None:
                if saved_val:
                    st.session_state.word_input = saved_val
                st.session_state.storage_loaded = True
                st.rerun()
        except:
            st.session_state.storage_loaded = True

    # 1. Input Section
    st.subheader("1. Enter Words")
    word_input = st.text_area(
        "Enter words (one per line):", 
        height=150, 
        placeholder="apple\nbanana",
        key="word_input"
    )
    
    # Persist input
    if "last_persisted_words" not in st.session_state:
        st.session_state.last_persisted_words = None
    if st.session_state.word_input != st.session_state.last_persisted_words:
        local_storage.setItem("vocabulary_words", st.session_state.word_input)
        st.session_state.last_persisted_words = st.session_state.word_input

    if st.button("Initial Fetch", type="primary"):
        words = [w.strip() for w in word_input.split('\n') if w.strip()]
        if not words:
            st.error("Please enter some words first.")
        else:
            new_data = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, word in enumerate(words):
                status_text.text(f"Fetching: {word}...")
                senses = fetch_word_data(word)
                
                if senses and use_vi and api_key:
                    for sense in senses:
                        pos = sense['word_info']['pos']
                        definition = sense['meaning_data']['def']
                        translation = translate_meaning_to_vi(word, pos, definition, api_key)
                        sense['vi_translation'] = translation
                
                new_data.extend(flatten_senses(word, senses))
                progress_bar.progress((i + 1) / len(words))
                time.sleep(0.5)
            
            st.session_state.vocab_data = new_data
            status_text.success("Initial fetch complete!")

    # 2. Editor Section
    if st.session_state.vocab_data:
        st.divider()
        st.subheader("2. Review & Edit")
        
        # Detection logic for status
        for row in st.session_state.vocab_data:
            if row['word'].lower() != row['last_fetched_word'].lower():
                row['status'] = "⚠️ Unfetched"
            elif "Not Found" in row['status'] and row['meaning']:
                row['status'] = "📝 Manual"
        
        # Action Buttons for the Editor
        col_btn1, col_btn2, _ = st.columns([2, 2, 6])
        
        with col_btn1:
            if st.button("🔍 Fetch Missing Data"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                rows_to_fetch = [r for r in st.session_state.vocab_data if "Unfetched" in r['status'] or "Not Found" in r['status']]
                
                for i, row in enumerate(rows_to_fetch):
                    word = row['word'].strip()
                    status_text.text(f"Fetching: {word}...")
                    
                    senses = fetch_word_data(word)
                    if senses:
                        # For simplicity in partial fetch, we'll just update the first sense found
                        # or ideally we'd replace the row with multiple rows if senses > 1
                        # But for now, let's update the current row with the first sense
                        sense = senses[0]
                        info = sense.get('word_info', {})
                        m_data = sense.get('meaning_data', {})
                        
                        if use_vi and api_key:
                            translation = translate_meaning_to_vi(word, info.get('pos', ''), m_data.get('def', ''), api_key)
                        else:
                            translation = ""

                        row.update({
                            "pos": info.get('pos', ''),
                            "ipa": f"{info.get('ipa_bre', '')} {info.get('ipa_ame', '')}".strip(),
                            "cf": m_data.get('cf', ''),
                            "meaning": m_data.get('def', ''),
                            "examples": sense.get('examples', ''),
                            "translation": translation,
                            "status": "✅ Synced",
                            "last_fetched_word": word
                        })
                    else:
                        row['status'] = "❌ Not Found"
                    
                    progress_bar.progress((i + 1) / len(rows_to_fetch))
                    time.sleep(0.5)
                
                status_text.success("Fetch complete!")
                st.rerun()

        # Display Data Editor
        edited_df = st.data_editor(
            st.session_state.vocab_data,
            column_config={
                "id": None, # Hide ID
                "last_fetched_word": None, # Hide tracking
                "status": st.column_config.TextColumn("Status", disabled=True),
                "word": st.column_config.TextColumn("Word", width="medium"),
                "pos": st.column_config.TextColumn("POS", width="small"),
                # "ipa": st.column_config.TextColumn("IPA", width="small"),
                "ipa": None,
                # "cf": st.column_config.TextColumn("Context (cf)", width="small"),
                "cf": None,
                # "meaning": st.column_config.TextColumn("Meaning", width="large"),
                "meaning": None,
                # "translation": st.column_config.TextColumn("Translation (Vi)", width="medium"),
                "translation": None,
                # "examples": st.column_config.TextColumn("Examples", width="large"),
                "examples": None,
            },
            num_rows="dynamic",
            key="vocab_editor",
            use_container_width=True
        )
        
        # Sync changes back to session state
        st.session_state.vocab_data = edited_df

        # 3. Export Section
        st.divider()
        st.subheader("3. Export")
        
        col_ex1, col_ex2 = st.columns([1, 4])
        with col_ex1:
            filename_base = st.text_input("Filename:", value="vocabulary")
        
        with col_ex2:
            st.write("") # Spacer
            st.write("") # Spacer
            if st.button("Generate .docx", type="primary"):
                if not is_valid_filename(filename_base):
                    st.error("Invalid filename.")
                else:
                    reconstructed = reconstruct_data_for_docx(st.session_state.vocab_data)
                    doc = generate_docx_from_data(reconstructed, title=filename_base.upper())
                    
                    buffer = io.BytesIO()
                    doc.save(buffer)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="Download .docx File",
                        data=buffer,
                        file_name=f"{filename_base}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

if __name__ == "__main__":
    main()
