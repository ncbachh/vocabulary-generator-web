# 📝 Vocabulary Generator Web

A Streamlit-based web application that converts a list of English words into a professionally formatted Word document (.docx) with definitions, pronunciations (IPA), and example sentences from the Oxford Learner's Dictionary.

## ✨ Features

- **Batch Word Processing:** Input a list of English words (one per line) and process them all at once.
- **Accurate Definitions:** Scrapes the Oxford Learner's Dictionary for high-quality, up-to-date word data.
- **Multi-Sense Support:** Fetches up to three different senses/meanings for each word.
- **IPA Pronunciations:** Includes both British (BrE) and American (NAmE) phonetic transcriptions.
- **Contextual Examples:** Provides up to two example sentences for each word meaning.
- **AI-Powered Translation (Optional):** Uses OpenRouter API to generate natural-sounding Vietnamese translations for each definition.
- **Professional Formatting:** Outputs a clean, tabular Word document ready for printing or study.
- **Progress Tracking:** Real-time feedback and a progress bar during document generation.

## 🛠 Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/) (Interactive web app framework)
- **Scraping:** [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) & `requests`
- **Document Generation:** [python-docx](https://python-docx.readthedocs.io/)
- **AI Integration:** [OpenRouter API](https://openrouter.ai/) (via `requests`)
- **Testing:** `unittest`

## 📂 Project Structure

```text
vocabulary-generator-web/
├── .streamlit/
│   └── secrets.toml         # For OpenRouter API key (local development)
├── src/
│   ├── app.py               # Main Streamlit application and UI
│   └── docx_logic.py        # Core scraping and .docx generation logic
├── tests/
│   └── test_app_logic.py    # Unit tests for the core logic
├── requirements.txt         # Project dependencies
└── README.md                # Technical documentation
```

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.9 or higher
- (Optional) An [OpenRouter API key](https://openrouter.ai/keys) for the Vietnamese translation feature.

### 2. Clone the Repository
```bash
git clone https://github.com/ncbachh/vocabulary-generator-web.git
cd vocabulary-generator-web
```

### 3. Create a Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Variable Configuration
To use the Vietnamese translation feature, you need an OpenRouter API key. You can provide it in two ways:

1.  **Through the App UI:** Enter the key in the sidebar of the web application.
2.  **Through Streamlit Secrets:** Create a `.streamlit/secrets.toml` file in the root directory:
    ```toml
    OPENROUTER_API_KEY = "your-openrouter-api-key-here"
    ```

## 💻 Running the App Locally

To start the Streamlit server:
```bash
streamlit run src/app.py
```
The app will open in your default browser at `http://localhost:8501`.

## 🤖 How the Translation Feature Works

The application uses the `arcee-ai/trinity-large-preview:free` model via OpenRouter to translate English definitions. The prompt is specifically engineered to return only the single most appropriate Vietnamese equivalent, avoiding lengthy explanations or full-sentence translations.

## 🧪 Running Tests

To ensure the scraping and document logic is working correctly:
```bash
python -m unittest tests/test_app_logic.py
```

## 🌐 Deployment (Streamlit Cloud)

1.  Push your code to a GitHub repository.
2.  Connect your repository to [Streamlit Cloud](https://share.streamlit.io/).
3.  Add your `OPENROUTER_API_KEY` to the **Secrets** section in the Streamlit Cloud dashboard.
4.  Deploy!

## 📜 License
This project is for educational purposes. Please respect the Terms of Use of the [Oxford Learner's Dictionary](https://www.oxfordlearnersdictionaries.com/).
