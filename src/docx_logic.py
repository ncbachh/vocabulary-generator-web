import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.table import WD_TABLE_ALIGNMENT
import time
import copy
import re

def get_pos_ipa(soup):
    pos_tag = soup.find('span', class_='pos')
    pos = ""
    if pos_tag:
        pos_text = pos_tag.get_text().strip().lower()
        mapping = {
            "noun": "n",
            "verb": "v",
            "adjective": "adj",
            "adverb": "adv",
            "phrasal verb": "phrv",
            "phr v": "phrv"
        }
        pos = f"({mapping.get(pos_text, pos_text)})"
        
    ipa_bre = ""
    phons_br = soup.find('div', class_='phons_br')
    if phons_br:
        ipa_br_tag = phons_br.find('span', class_='phon')
        if ipa_br_tag:
            ipa_bre = ipa_br_tag.get_text().strip()
            
    ipa_ame = ""
    phons_n_am = soup.find('div', class_='phons_n_am')
    if phons_n_am:
        ipa_ame_tag = phons_n_am.find('span', class_='phon')
        if ipa_ame_tag:
            ipa_ame = ipa_ame_tag.get_text().strip()
            
    return {
        "pos": pos,
        "ipa_bre": ipa_bre,
        "ipa_ame": ipa_ame
    }

def extract_meaning(container):
    meaning_tag = container.find('span', class_='def')
    if not meaning_tag:
        return None
    
    # Check for complement patterns (cf)
    cf_tag = container.find('span', class_='cf')
    # If not found directly, check inside sensetop
    if not cf_tag:
        sensetop = container.find('span', class_='sensetop')
        if sensetop:
            cf_tag = sensetop.find('span', class_='cf')
    
    cf_text = ""
    if cf_tag:
        text = cf_tag.get_text().strip()
        # Only apply special formatting to cf that contains somebody/something or prepositional patterns
        if re.search(r'\b(somebody|something|sb|sth)\b', text, re.I) or '(' in text:
            cf_text = text

    # Handle standard prefixes (like dtxt)
    prefix = ""
    sensetop_tag = container.find('span', class_='sensetop')
    if sensetop_tag:
        sensetop_clone = copy.copy(sensetop_tag)
        # Remove definition and also the cf if we're treating it specially
        def_in_clone = sensetop_clone.find('span', class_='def')
        if def_in_clone:
            def_in_clone.decompose()
        
        if cf_text:
            cf_in_clone = sensetop_clone.find('span', class_='cf')
            if cf_in_clone:
                cf_in_clone.decompose()
        
        prefix = sensetop_clone.get_text().strip()
    
    # If no sensetop prefix, check for dtxt
    if not prefix:
        dtxt_tag = container.find('span', class_='dtxt')
        if dtxt_tag and (not sensetop_tag or dtxt_tag not in sensetop_tag.descendants):
            parent = dtxt_tag.parent
            if parent and ('dis-g' in parent.get('class', []) or 'wrap' in [c.get('class', []) for c in parent.find_all('span', class_='wrap')]):
                prefix = parent.get_text().strip()
            else:
                prefix = dtxt_tag.get_text().strip()

    definition = meaning_tag.get_text().strip()
    
    return {
        "cf": cf_text,
        "prefix": prefix,
        "def": definition
    }

def fetch_word_data(word):
    # Normalize word for URL construction
    clean_word = word.strip().lower()
    url_word = clean_word
    
    # If exactly two words separated by space and no hyphen exists, use hyphenated version for URL
    parts = clean_word.split()
    if len(parts) == 2 and '-' not in clean_word:
        url_word = "-".join(parts)
        
    url = f"https://www.oxfordlearnersdictionaries.com/definition/english/{url_word}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        main_container = soup.find('div', id='main-container')
        if not main_container:
            main_container = soup
            
        # Get word info (POS, IPA)
        word_info = get_pos_ipa(soup)
        
        senses_data = []
        
        # Find all sense items
        senses = main_container.find_all('li', class_='sense')
        
        if not senses:
            meaning_data = extract_meaning(main_container)
            if meaning_data:
                example_tags = main_container.find_all('span', class_='x', limit=2)
                examples = [ex.get_text().strip() for ex in example_tags]
                senses_data.append({
                    "word_info": word_info,
                    "meaning_data": meaning_data,
                    "examples": "\n".join([f"• {ex}" for ex in examples]) if examples else "No examples found"
                })
        else:
            for i, sense in enumerate(senses[:3]):
                meaning_data = extract_meaning(sense)
                if not meaning_data:
                    continue
                
                example_tags = sense.find_all('span', class_='x', limit=2)
                examples = [ex.get_text().strip() for ex in example_tags]
                
                senses_data.append({
                    "word_info": word_info,
                    "meaning_data": meaning_data,
                    "examples": "\n".join([f"• {ex}" for ex in examples]) if examples else "No examples found"
                })
                
        return senses_data
    except Exception:
        return None

def set_cell_width(cell, width_cm):
    cell.width = Cm(width_cm)

def create_vocabulary_docx(words: list[str], title: str = "VOCABULARY LIST", progress_callback=None) -> tuple[Document, list[str]]:
    all_word_data = []
    failed_words = []
    
    for i, word in enumerate(words):
        norm_word = word.strip().lower()
        if progress_callback:
            progress_callback(i, len(words), norm_word, status="Fetching...")
        
        senses = fetch_word_data(norm_word)
        if senses:
            all_word_data.append((norm_word, senses))
            if progress_callback:
                progress_callback(i, len(words), norm_word, status="Success")
        else:
            failed_words.append(word)
            if progress_callback:
                progress_callback(i, len(words), norm_word, status="Failed")
        
        time.sleep(1)
        
    if not all_word_data:
        raise ValueError("No data could be fetched for any of the provided words.")

    doc = Document()
    
    # 1. Page Margins
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.bottom_margin = Cm(1.27)
    section.right_margin = Cm(1.27)

    # 4. Title Formatting (derived from app.py)
    heading = doc.add_heading(title, 0)
    # 3. Font Size for Title
    for run in heading.runs:
        run.font.size = Pt(12)

    # Add a table with 4 columns
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    table.allow_autofit = False # 2. Fixed Widths

    # Define header cells and 2. Set Column Widths
    widths = [0.85, 3.8, 6.88, 6.88]
    hdr_cells = table.rows[0].cells
    headers = ['No', 'Words', 'Meaning', 'Examples']
    
    for idx, (cell, text) in enumerate(zip(hdr_cells, headers)):
        cell.text = text
        set_cell_width(cell, widths[idx])
        # 3. Font Size for Header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(12)

    # Fill data
    for i, (word, senses) in enumerate(all_word_data, 1):
        if not senses:
            continue
            
        start_row_idx = len(table.rows)
        
        for j, sense in enumerate(senses):
            row_cells = table.add_row().cells
            # 2. Set Fixed Widths for each new row
            for idx, cell in enumerate(row_cells):
                set_cell_width(cell, widths[idx])

            if j == 0:
                row_cells[0].text = str(i)
                
                # Words column: Word (POS) + IPAs
                word_cell = row_cells[1]
                p_word = word_cell.paragraphs[0]
                info = sense['word_info']
                
                word_text = f"{word} {info['pos']}"
                run_word = p_word.add_run(word_text)
                
                # IPA logic
                ipa_bre = info['ipa_bre']
                ipa_ame = info['ipa_ame']
                clean_bre = ipa_bre.strip('/')
                clean_ame = ipa_ame.strip('/')
                
                ipa_text = ""
                if ipa_bre and ipa_ame:
                    ipa_text = f"\n{ipa_bre}" if clean_bre == clean_ame else f"\n{ipa_bre}\n{ipa_ame}"
                elif ipa_bre:
                    ipa_text = f"\n{ipa_bre}"
                elif ipa_ame:
                    ipa_text = f"\n{ipa_ame}"
                
                if ipa_text:
                    p_word.add_run(ipa_text)
            
            # Formatting meaning cell
            meaning_cell = row_cells[2]
            p = meaning_cell.paragraphs[0]
            m_data = sense['meaning_data']
            
            if m_data['cf']:
                p.add_run(m_data['cf']).bold = True
                p.add_run('\n')
            
            definition_text = ""
            if m_data['prefix']:
                definition_text += m_data['prefix'] + " "
            definition_text += m_data['def']
            p.add_run(definition_text)
            
            row_cells[3].text = sense['examples']
            
            # 3. Apply 12pt font size to all paragraphs in the row
            for cell in row_cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(12)
            
        end_row_idx = len(table.rows) - 1
        
        # Merge 'No' and 'Word' cells if there are multiple meanings
        if start_row_idx != end_row_idx:
            table.cell(start_row_idx, 0).merge(table.cell(end_row_idx, 0))
            table.cell(start_row_idx, 1).merge(table.cell(end_row_idx, 1))

    return doc, failed_words
