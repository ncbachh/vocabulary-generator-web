import streamlit as st
import io
import sys
import os
import re
import time
import pandas as pd

# Ensure src is in path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from docx_logic import fetch_full_word_data, generate_vocabulary_docx
from streamlit_local_storage import LocalStorage

st.set_page_config(page_title="Vocabulary Generator", page_icon="📝", layout="wide")

def is_valid_filename(filename):
    # Characters not allowed in Windows/Unix filenames
    invalid_chars = r'[\\/:*?"<>|]'
    if re.search(invalid_chars, filename):
        return False
    return True

def main():
    st.title("📝 Vocabulary Generator")
    st.markdown("""
    Create a professionally formatted Word document from your English word list. 
    Dictionary data is fetched from the *Oxford Learner's Dictionary*.
    """)

    with st.expander("📖 How to use", expanded=False):
        st.markdown("""
        1. **Step 1:** Paste your words into the text area (one per line) and click **Initialize**.
        2. **Step 2:** Click **Fetch / Update Data**. This fetches definitions, pronunciations, and examples.
        3. **Review:** If a word fails (❌), you can click its name in the table to fix typos.
        4. **Step 3:** Once your list is ready (✅), enter a filename and click **Download**.
        """)

    # Initialize LocalStorage
    local_storage = LocalStorage()

    # Sidebar for Settings
    st.sidebar.title("Settings")
    use_vi = st.sidebar.checkbox("Enable Vietnamese Translation", value=False, help="Use AI to translate English definitions into Vietnamese.")
    
    api_key = ""
    if use_vi:
        api_key = st.sidebar.text_input("OpenRouter API Key", type="password", help="Get your key from https://openrouter.ai/keys")
        if not api_key and "OPENROUTER_API_KEY" in st.secrets:
            api_key = st.secrets["OPENROUTER_API_KEY"]
            st.sidebar.info("Using API key from secrets.")
        elif not api_key:
            st.sidebar.warning("Please enter your OpenRouter API Key to enable translation.")

    # Initialize session state
    if "word_registry" not in st.session_state:
        st.session_state.word_registry = pd.DataFrame(columns=["Word", "Status"])
    if "fetched_data" not in st.session_state:
        st.session_state.fetched_data = {} # word -> senses
    if "word_input" not in st.session_state:
        st.session_state.word_input = ""
    if "storage_loaded" not in st.session_state:
        st.session_state.storage_loaded = False
    if "is_fetching" not in st.session_state:
        st.session_state.is_fetching = False
    
    # Load saved words from local storage
    if not st.session_state.storage_loaded:
        try:
            saved_val = local_storage.getItem("vocabulary_words")
            if saved_val is not None:
                if saved_val:
                    st.session_state.word_input = saved_val
                st.session_state.storage_loaded = True
                st.rerun()
            elif st.session_state.word_input != "":
                st.session_state.storage_loaded = True
        except:
            st.session_state.storage_loaded = True

    # 1. Input Section
    st.subheader("Step 1: Input Word List")
    word_input = st.text_area(
        "Enter words (one per line):", 
        height=150, 
        placeholder="apple\nbanana\ncherry",
        key="word_input",
        disabled=st.session_state.is_fetching
    )
    
    # Persistence
    if "last_persisted_words" not in st.session_state:
        st.session_state.last_persisted_words = None
    if st.session_state.word_input != st.session_state.last_persisted_words:
        local_storage.setItem("vocabulary_words", st.session_state.word_input)
        st.session_state.last_persisted_words = st.session_state.word_input

    if st.button("Initialize", disabled=st.session_state.is_fetching, help="Start the process with the words above."):
        new_words = [w.strip() for w in word_input.split('\n') if w.strip()]
        if new_words:
            # Create a new registry, keeping existing data if word is the same
            new_df = pd.DataFrame([
                {"Word": w, "Status": "⏳ Pending"} for w in new_words
            ])
            st.session_state.word_registry = new_df
            st.success(f"Loaded {len(new_words)} words. Proceed to Step 2 below.")
        else:
            st.warning("Please enter some words first.")

    # 2. Interactive Registry Section
    if not st.session_state.word_registry.empty:
        st.divider()
        st.subheader("Step 2: Get Dictionary Data")
        # st.info("Fetch data for the list. You can edit words in the 'Word' column to fix typos.")
        
        # Display Data Editor
        edited_registry = st.data_editor(
            st.session_state.word_registry,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Status": st.column_config.TextColumn(help="✅ Success, ❌ Failed, ⏳ Pending (Ready to fetch)", disabled=True),
                "Word": st.column_config.TextColumn(help="Double-click to edit and retry a failed word")
            },
            key="registry_editor",
            disabled=st.session_state.is_fetching
        )
        
        # Check if user edited words - if they did, reset their status to Pending
        if not edited_registry.equals(st.session_state.word_registry):
            for i in range(min(len(edited_registry), len(st.session_state.word_registry))):
                if edited_registry.iloc[i]["Word"] != st.session_state.word_registry.iloc[i]["Word"]:
                    edited_registry.at[i, "Status"] = "⏳ Pending"
            st.session_state.word_registry = edited_registry

        col_f1, col_f2 = st.columns([1, 4])
        
        with col_f1:
            if st.session_state.is_fetching:
                if st.button("Stop Fetching", type="secondary", help="Stop the current operation immediately."):
                    st.session_state.is_fetching = False
                    st.rerun()
            else:
                if st.button("Start Fetching", type="primary", help="Download data for all words marked 'Pending' or 'Failed'."):
                    st.session_state.is_fetching = True
                    st.rerun()

        if st.session_state.is_fetching:
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            # Use local copies to avoid partial updates if stopped
            temp_registry = st.session_state.word_registry.copy()
            temp_fetched_data = st.session_state.fetched_data.copy()
            
            rows_to_fetch = temp_registry[temp_registry["Status"] != "✅ Success"]
            total = len(rows_to_fetch)
            
            if total == 0:
                st.session_state.is_fetching = False
                st.rerun()
            else:
                for i, (idx, row) in enumerate(rows_to_fetch.iterrows()):
                    # Double check if user clicked Stop mid-loop
                    if not st.session_state.is_fetching:
                        break
                        
                    word = row["Word"]
                    status_text.text(f"Processing: {word} ({i+1}/{total})")
                    progress_bar.progress((i + 1) / total)
                    
                    try:
                        senses = fetch_full_word_data(word, use_vi, api_key)
                        if senses:
                            temp_registry.at[idx, "Status"] = "✅ Success"
                            temp_fetched_data[word] = senses
                        else:
                            temp_registry.at[idx, "Status"] = "❌ Failed"
                    except Exception:
                        temp_registry.at[idx, "Status"] = "❌ Error"
                    
                    time.sleep(0.5)
                
                # Only commit if we actually finished the entire loop and weren't stopped
                if st.session_state.is_fetching:
                    st.session_state.word_registry = temp_registry
                    st.session_state.fetched_data = temp_fetched_data
                    st.session_state.is_fetching = False
                    st.success(f"Finished processing {total} words.")
                    st.rerun()

        # 3. Export Section
        st.divider()
        st.subheader("Step 3: Download Word Document")
        
        col_e1, col_e2 = st.columns([1, 4])
        with col_e1:
            filename_base = st.text_input("Filename:", value="vocabulary", disabled=st.session_state.is_fetching)
        
        with col_e2:
            st.write("") # Spacer
            st.write("") # Spacer
            
            export_data = []
            for _, row in st.session_state.word_registry.iterrows():
                word = row["Word"]
                if row["Status"] == "✅ Success" and word in st.session_state.fetched_data:
                    export_data.append((word, st.session_state.fetched_data[word]))
            
            if export_data and not st.session_state.is_fetching:
                if is_valid_filename(filename_base):
                    try:
                        # Pre-generate buffer for one-click download
                        doc = generate_vocabulary_docx(export_data, title=filename_base.upper())
                        buffer = io.BytesIO()
                        doc.save(buffer)
                        buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Download",
                            data=buffer,
                            file_name=f"{filename_base}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary"
                        )
                    except Exception as e:
                        st.error(f"Prepare export failed: {e}")
                else:
                    st.error("Invalid filename.")
            else:
                st.button("Generate DOCX", disabled=True, help="Fetch data successfully first.")

if __name__ == "__main__":
    main()
