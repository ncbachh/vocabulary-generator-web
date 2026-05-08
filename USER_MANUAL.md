# 🚀 Your Vocabulary Workflow, Simplified

Ever found yourself manually copying and pasting word definitions, IPA transcriptions, and examples into a Word document? 

**Vocabulary Generator Web** is a powerful productivity tool designed for language learners, teachers, and enthusiasts. In just a few clicks, it transforms a simple list of words into a professionally formatted study guide, complete with reliable dictionary data and AI-powered translations.

---

## ✨ Why You'll Love It

- **Save Time:** Forget about switching between browser tabs and Word. Just enter your words and let the app do the heavy lifting.
- **Reliable Data:** All information is sourced from the **Oxford Learner's Dictionary**, ensuring accuracy and academic quality.
- **Standardized IPA:** Includes phonetic transcriptions for both British and American accents.
- **Clear Examples:** Context is everything. Each word comes with real-world examples to help you understand usage.
- **Smart Translations:** Optionally add Vietnamese translations for definitions using advanced AI technology.

---

## 🛠 How It Works

The app follows a refined 3-step workflow to give you full control over your vocabulary list:

1.  **📥 Input:** Enter your word list and fetch data from the dictionary.
2.  **🔍 Review & Edit:** Inspect the results in an interactive table. You can modify definitions, add translations, or manually fix words that weren't found.
3.  **🚀 Export:** Download your customized list as a professionally formatted `.docx` file.

---

## 🔑 Getting Started with AI Translation

To enable the **Vietnamese Translation** feature, the app uses **OpenRouter**, a gateway to modern AI models.
The default model is `nvidia/nemotron-3-nano-30b-a3b:free`, which provides fast and reliable translations.

### 1. How to get an OpenRouter API Key
1.  Go to [OpenRouter.ai](https://openrouter.ai/).
2.  Sign up or log in.
3.  Navigate to the **Keys** section (usually under your profile settings).
4.  Click **"Create Key"**, give it a name (e.g., "Vocabulary App"), and copy the generated key.

### 2. How to use your API Key in the app
1.  Open the **Vocabulary Generator Web** app.
2.  In the left sidebar, check the box: **"Enable Vietnamese Translation"**.
3.  Paste your copied API key into the **"OpenRouter API Key"** field.

---

## 📝 Step-by-Step Guide

### Step 1: Enter Your Words (Tab 1)
In the **"📥 1. Enter Words"** tab, type or paste your list of English words. Please enter **one word per line**.
> **Example:**
> ```text
> serendipity
> resilient
> ambiguous
> ```
Click **"Fetch Word Data"**. The app will scrape the dictionary (and translate if enabled) and then automatically move you to the next step.

### Step 2: Review and Customize (Tab 2)
In the **"🔍 2. Review & Edit"** tab, you'll see a table containing all the fetched information.

-   **Edit Data:** Click on any cell in the **Word**, **POS**, **Meaning**, or **Translation** columns to edit the text directly.
-   **Manual Entry:** If a word was marked as `❌ Not Found`, you can manually type in its meaning and translation. Its status will change to `📝 Manual`.
-   **Fetch Missing:** If you edited a word or want to retry a failed fetch, click **"🔍 Fetch Missing/Unfetched Data"** at the top.
-   **Syncing:** To add or remove words from your list, go back to **Tab 1**, update the text area, and click **"Fetch"** again.

Once you are happy with the data, click **"Confirm & Go to Export ➔"**.

### Step 3: Download Your List (Tab 3)
In the **"🚀 3. Export"** tab:
1.  Enter your desired **Filename** (without the `.docx` extension).
2.  Click the **"📥 Download .docx File"** button.

---

## 💡 Pro Tips
- **Inflections Handled:** The app now automatically handles plural or inflected forms (e.g., searching for `books` will correctly find `book`).
- **Multiple Meanings:** For many words, the app fetches multiple parts of speech (e.g., both the noun and verb forms of `present`).
- **Format Matters:** The final document uses a clean table layout, making it easy to add your own notes or highlight important sections.

---

*Happy Learning!* 🎓
