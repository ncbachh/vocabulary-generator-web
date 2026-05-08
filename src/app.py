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
    current_key = None # (word, pos)
    current_senses = []
    
    for row in df_rows:
        word = row['word'].strip().lower()
        pos = row.get('pos', '').strip()
        key = (word, pos)
        
        # Sense data structure matching docx_logic expectations
        # Handle IPA split
        ipa_parts = row['ipa'].split()
        ipa_bre = ipa_parts[0] if len(ipa_parts) > 0 else ""
        ipa_ame = ipa_parts[1] if len(ipa_parts) > 1 else ""
        
        sense = {
            "word_info": {
                "pos": pos,
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
        
        if key == current_key:
            current_senses.append(sense)
        else:
            if current_key is not None:
                reconstructed.append((current_key[0], current_senses))
            current_key = key
            current_senses = [sense]
            
    if current_key is not None:
        reconstructed.append((current_key[0], current_senses))
        
    return reconstructed

def main():
    st.title("📝 Vocabulary Generator")
    
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
    if "step" not in st.session_state:
        st.session_state.step = 1

    # Define tabs based on progress
    tab_titles = ["📥 1. Enter Words"]
    if st.session_state.vocab_data:
        tab_titles.append("🔍 2. Review & Edit")
    if st.session_state.step >= 3 and st.session_state.vocab_data:
        tab_titles.append("🚀 3. Export")
    
    tabs = st.tabs(tab_titles)

    # 1. Input Section
    with tabs[0]:
        st.subheader("Step 1: Enter Your Word List")
        word_input = st.text_area(
            "Enter words (one per line):", 
            height=200, 
            placeholder="apple\nbanana\ncherry",
            key="word_input_area",
            value=st.session_state.word_input
        )
        
        # Update session state word_input from the text area
        if word_input != st.session_state.word_input:
            st.session_state.word_input = word_input

        if st.button("Fetch Word Data", type="primary", use_container_width=True):
            input_words = [w.strip() for w in word_input.split('\n') if w.strip()]
            if not input_words:
                st.session_state.vocab_data = []
                st.info("List cleared.")
                st.rerun()
            else:
                input_words_lower = {w.lower() for w in input_words}
                
                # 1. Synchronize Deletions: Remove rows no longer in the input text area
                # We check against 'last_fetched_word' which is the key for what we requested
                st.session_state.vocab_data = [
                    row for row in st.session_state.vocab_data 
                    if row.get('last_fetched_word', '').lower() in input_words_lower
                ]
                
                # 2. Identify New Words to Fetch
                existing_words = {row['last_fetched_word'].lower() for row in st.session_state.vocab_data}
                words_to_fetch = [w for w in input_words if w.lower() not in existing_words]
                
                if not words_to_fetch:
                    st.success("List synchronized (deletions applied). No new words to fetch.")
                    st.session_state.step = 2
                    st.rerun()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                new_fetched_data = []
                for i, word in enumerate(words_to_fetch):
                    status_text.text(f"Fetching: {word}...")
                    result = fetch_word_data(word)
                    
                    if result:
                        headword, senses = result
                        if use_vi and api_key:
                            for sense in senses:
                                pos = sense['word_info']['pos']
                                definition = sense['meaning_data']['def']
                                translation = translate_meaning_to_vi(headword, pos, definition, api_key)
                                sense['vi_translation'] = translation
                        
                        # Store 'word' (exactly as user typed it) as the tracking key
                        new_fetched_data.extend(flatten_senses(word, senses))
                    else:
                        # Add failure record so it's not re-fetched unless removed/re-added in Tab 1
                        new_fetched_data.extend(flatten_senses(word, None))
                        
                    progress_bar.progress((i + 1) / len(words_to_fetch))
                    time.sleep(0.5)
                
                # Append new data
                st.session_state.vocab_data.extend(new_fetched_data)
                st.session_state.step = 2
                status_text.success(f"Synchronized! Added {len(words_to_fetch)} new word(s).")
                st.rerun()

    # 2. Editor Section
    if len(tab_titles) > 1:
        with tabs[1]:
            st.subheader("Step 2: Review and Customize")
            st.info("💡 **Tip:** To add or remove words, update your list in Tab 1 and click Fetch again. This table is fixed for editing existing data.")
            
            # Status Detection Logic
            for row in st.session_state.vocab_data:
                # If the word field was edited manually and differs from the last successful fetch
                if row.get('last_fetched_word') and row['word'].lower() != row['last_fetched_word'].lower():
                    row['status'] = "⚠️ Unfetched"
                # If it was a 'Not Found' but now has a meaning, it's 'Manual'
                elif "Not Found" in row['status'] and row['meaning']:
                    row['status'] = "📝 Manual"
            
            # Action Buttons for the Editor
            col_btn1, col_btn2 = st.columns([1, 1])
            
            with col_btn1:
                if st.button("🔍 Fetch Missing/Unfetched Data", use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    rows_to_fetch = [r for r in st.session_state.vocab_data if "Unfetched" in r['status'] or "Not Found" in r['status']]
                    
                    if not rows_to_fetch:
                        st.info("No missing or unfetched words found.")
                    else:
                        for i, row in enumerate(rows_to_fetch):
                            target_word = row['word'].strip()
                            status_text.text(f"Fetching: {target_word}...")
                            
                            result = fetch_word_data(target_word)
                            if result:
                                headword, senses = result
                                # Take the first sense found for manual row updates
                                sense = senses[0]
                                info = sense.get('word_info', {})
                                m_data = sense.get('meaning_data', {})
                                
                                if use_vi and api_key:
                                    translation = translate_meaning_to_vi(headword, info.get('pos', ''), m_data.get('def', ''), api_key)
                                else:
                                    translation = ""

                                row.update({
                                    "word": headword,
                                    "pos": info.get('pos', ''),
                                    "ipa": f"{info.get('ipa_bre', '')} {info.get('ipa_ame', '')}".strip(),
                                    "cf": m_data.get('cf', ''),
                                    "meaning": m_data.get('def', ''),
                                    "examples": sense.get('examples', ''),
                                    "translation": translation,
                                    "status": "✅ Synced",
                                    "last_fetched_word": headword
                                })
                            else:
                                row['status'] = "❌ Not Found"
                            
                            progress_bar.progress((i + 1) / len(rows_to_fetch))
                            time.sleep(0.5)
                        
                        status_text.success("Processing complete!")
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
                    "ipa": None, # Hide IPA
                    "cf": None, # Hide Context (cf)
                    "meaning": st.column_config.TextColumn("Meaning", width="large"),
                    "translation": st.column_config.TextColumn("Translation", width="medium"),
                    "examples": None, # Hide Examples
                },
                num_rows="fixed", # Disable manual Add/Delete
                key="vocab_editor",
                use_container_width=True
            )
            
            # Sync changes back to session state
            st.session_state.vocab_data = edited_df
            
            st.markdown("---")
            if st.button("Confirm & Go to Export ➔", type="primary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()

    # 3. Export Section
    if len(tab_titles) > 2:
        with tabs[2]:
            st.subheader("Step 3: Download Your List")
            
            filename_base = st.text_input("Enter filename (without extension):", value="vocabulary_list")
            
            if not is_valid_filename(filename_base):
                st.error("Invalid filename. Please avoid special characters.")
            else:
                # Generate document bytes automatically
                # This is fast since it only involves local data processing
                reconstructed = reconstruct_data_for_docx(st.session_state.vocab_data)
                doc = generate_docx_from_data(reconstructed, title=filename_base.upper())
                
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                st.write("") # Spacer
                st.download_button(
                    label="📥 Download .docx File",
                    data=buffer,
                    file_name=f"{filename_base}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary"
                )


if __name__ == "__main__":
    main()
