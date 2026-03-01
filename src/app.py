import streamlit as st
import io
import sys
import os

# Ensure src is in path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from docx_logic import create_vocabulary_docx

st.set_page_config(page_title="Vocabulary Generator", page_icon="📝")

def main():
    st.title("📝 Vocabulary Generator")
    st.markdown("""
    Convert your list of English words into a professionally formatted Word document with definitions, 
    pronunciations, and examples from the Oxford Learner's Dictionary.
    """)

    # Initialize session state
    if "docx_file" not in st.session_state:
        st.session_state.docx_file = None
    if "failed_words" not in st.session_state:
        st.session_state.failed_words = []

    # Input Section
    st.subheader("1. Enter Words")
    word_input = st.text_area("Enter words (one per line):", height=200, placeholder="apple\nbanana\ncherry")
    
    words = [w.strip() for w in word_input.split('\n') if w.strip()]
    
    col1, col2 = st.columns([1, 4])
    with col1:
        filename_base = st.text_input("Filename:", placeholder="vocabulary")
        filename = filename_base + ".docx" if not filename_base.endswith(".docx") else filename_base

    with col2:
        st.write("") # Spacer
        st.write("") # Spacer
        generate_btn = st.button("Generate Document", type="primary", disabled=not words)

    if generate_btn:
        st.session_state.docx_file = None
        st.session_state.failed_words = []
        
        # 4. Title Formatting: Derived from filename
        # - Convert to uppercase
        # - Remove .docx extension (filename_base handles this)
        doc_title = filename_base.upper()
        
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        def update_progress(current, total, word, status):
            percent = (current + 1) / total
            progress_bar.progress(percent)
            status_text.text(f"{status}: {word} ({current + 1}/{total})")

        try:
            with st.spinner("Fetching data and generating document..."):
                doc, failed_words = create_vocabulary_docx(words, title=doc_title, progress_callback=update_progress)
                
                # Save to memory buffer
                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                st.session_state.docx_file = buffer
                st.session_state.failed_words = failed_words
                
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
            label=f"Download {filename}",
            data=st.session_state.docx_file,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

if __name__ == "__main__":
    main()
