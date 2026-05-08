import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import time
import copy
import re

def get_pos_ipa(soup):
    # Try multiple common POS tag structures
    pos_tag = soup.find(['span', 'pos', 'pos-g'], class_='pos') or \
              soup.find(['span', 'pos', 'pos-g'], hclass='pos') or \
              soup.find('pos')
              
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

def _parse_senses_from_soup(soup, word_info):
    """Internal helper to extract senses from a BeautifulSoup object."""
    main_container = soup.find('div', id='main-container')
    if not main_container:
        main_container = soup
        
    # Remove Idioms section to avoid extracting idiom meanings
    for idioms_section in main_container.find_all(['div', 'span'], class_='idioms'):
        idioms_section.decompose()
        
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
                "examples": "\n".join([f"• {ex}" for ex in examples]) if examples else ""
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
                "examples": "\n".join([f"• {ex}" for ex in examples]) if examples else ""
            })
    return senses_data

def fetch_word_data(word):
    # Normalize word for URL construction
    clean_word = word.strip().lower()
    url_word = clean_word
    
    # If exactly two words separated by space and no hyphen exists, use hyphenated version for URL
    parts = clean_word.split()
    if (len(parts) == 2 or len(parts) == 3) and '-' not in clean_word:
        url_word = "-".join(parts)
        
    base_url = f"https://www.oxfordlearnersdictionaries.com/definition/english/{url_word}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(base_url, headers=headers)
        if response.status_code != 200:
            # Fallback to search URL if direct path fails (for inflected words)
            search_url = f"https://www.oxfordlearnersdictionaries.com/search/english/?q={url_word}"
            response = requests.get(search_url, headers=headers)
            if response.status_code != 200:
                return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract headword from the page (Normalization)
        headword_tag = soup.find('h1', class_='headword')
        headword = headword_tag.get_text().strip() if headword_tag else clean_word

        # 1. Fetch current page data
        word_info = get_pos_ipa(soup)
        all_senses = _parse_senses_from_soup(soup, word_info)
        
        # 2. Look for other POS entries
        def normalize_url(url):
            return url.split('?')[0].split('#')[0].rstrip('/')

        seen_urls = {normalize_url(response.url), normalize_url(base_url)}
        related_entries_div = soup.find('div', id='relatedentries')
        
        if related_entries_div:
            # Look for "All matches" header (dt or div)
            all_matches_header = related_entries_div.find(['dt', 'div'], string=re.compile(r'All matches', re.I))
            if not all_matches_header:
                all_matches_header = related_entries_div.find(lambda tag: tag.name in ['dt', 'div'] and 'All matches' in tag.get_text())
            
            if all_matches_header:
                list_ul = all_matches_header.find_next(['ul', 'ol'])
                if list_ul:
                    other_links = []
                    for li in list_ul.find_all('li'):
                        a = li.find('a')
                        if not a: continue
                        
                        # Flexible POS tag search
                        pos_tag = a.find(['span', 'pos', 'pos-g'], class_='pos') or \
                                  a.find(['span', 'pos', 'pos-g'], hclass='pos') or \
                                  a.find('pos')
                                  
                        if pos_tag:
                            link_text = a.get_text(separator=' ', strip=True).lower()
                            pos_text = pos_tag.get_text().strip().lower()
                            expected_text = f"{clean_word} {pos_text}"
                            
                            if link_text == expected_text:
                                href = a.get('href')
                                if href:
                                    if not href.startswith('http'):
                                        href = "https://www.oxfordlearnersdictionaries.com" + href
                                    
                                    norm_href = normalize_url(href)
                                    if norm_href not in seen_urls:
                                        other_links.append(href)
                                        seen_urls.add(norm_href)
                    
                    for link in other_links:
                        time.sleep(0.5)
                        try:
                            res = requests.get(link, headers=headers)
                            if res.status_code == 200:
                                s_soup = BeautifulSoup(res.content, 'html.parser')
                                s_info = get_pos_ipa(s_soup)
                                all_senses.extend(_parse_senses_from_soup(s_soup, s_info))
                        except Exception:
                            continue
                
        if not all_senses:
            return None
                            
        return headword, all_senses
    except Exception:
        return None

def translate_meaning_to_vi(word, pos, definition, api_key):
    """Translates an English definition to Vietnamese using OpenRouter."""
    if not api_key:
        return None
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501", # Required for OpenRouter free models
        "X-Title": "Vocabulary Generator Web"
    }
    
    prompt = f"""
        You are given an English dictionary definition of the {pos} "{word}".

        Your task is to identify the SINGLE most appropriate Vietnamese word that matches the concept described by this definition.

        Return ONLY one Vietnamese word (or a short fixed expression if necessary) that a Vietnamese dictionary would use as the translation of "{word}" in this meaning.

        DO NOT translate the full definition into Vietnamese.
        DO NOT explain anything.
        DO NOT return a sentence.
        ONLY return the equivalent Vietnamese word.

        Definition: "{definition}"
        """
    
    payload = {
        "model": "nvidia/nemotron-3-nano-30b-a3b:free",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        translation = result['choices'][0]['message']['content'].strip()
        # Remove any unexpected quotes or prefixes the LLM might include
        translation = re.sub(r'^["\']|["\']$', '', translation)
        return translation
    except Exception as e:
        print(f"Translation Error: {e}")
        return None

def set_cell_width(cell, width_cm):
    cell.width = Cm(width_cm)

def generate_docx_from_data(all_word_data, title="VOCABULARY LIST"):
    """
    Generates a .docx file from a list of word data.
    all_word_data should be a list of tuples/dicts containing (word, senses).
    """
    doc = Document()
    
    # Global Paragraph Formatting: Spacing After: 8pt
    style = doc.styles['Normal']
    style.paragraph_format.space_after = Pt(8)
    
    # Page Margins
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.bottom_margin = Cm(1.27)
    section.right_margin = Cm(1.27)

    # Title Formatting
    heading = doc.add_heading(title, 0)

    # Add a table with 4 columns
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    table.allow_autofit = False

    # Header cells and Fixed Widths
    widths = [0.85, 3.8, 6.88, 6.88]
    hdr_cells = table.rows[0].cells
    headers = ['No', 'WORDS', 'MEANING', 'EXAMPLES']
    
    for idx, (cell, text) in enumerate(zip(hdr_cells, headers)):
        cell.text = text
        set_cell_width(cell, widths[idx])
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.size = Pt(12)
                run.bold = True

    # Fill data
    for i, item in enumerate(all_word_data, 1):
        # Support both tuple (word, senses) and dict format
        if isinstance(item, tuple):
            word, senses = item
        else:
            word = item.get('word', '')
            senses = item.get('senses', [])

        if not senses:
            continue
            
        start_row_idx = len(table.rows)
        
        for j, sense in enumerate(senses):
            row_cells = table.add_row().cells
            for idx, cell in enumerate(row_cells):
                set_cell_width(cell, widths[idx])

            if j == 0:
                row_cells[0].text = str(i)
                word_cell = row_cells[1]
                p_word = word_cell.paragraphs[0]
                info = sense['word_info']
                
                word_text = f"{word} {info['pos']}"
                p_word.add_run(word_text)
                
                ipa_bre = info.get('ipa_bre', '')
                ipa_ame = info.get('ipa_ame', '')
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
            
            meaning_cell = row_cells[2]
            p = meaning_cell.paragraphs[0]
            m_data = sense['meaning_data']
            
            if m_data.get('cf'):
                p.add_run(m_data['cf']).bold = True
                p.add_run('\n')
            
            definition_text = ""
            if m_data.get('prefix'):
                definition_text += m_data['prefix'] + " "
            definition_text += m_data.get('def', '')
            p.add_run(definition_text)
            
            # Vietnamese Translation
            if sense.get('vi_translation'):
                p.add_run('\n')
                run_vi = p.add_run(f"({sense['vi_translation']})")
                run_vi.italic = True
            
            row_cells[3].text = sense.get('examples', '')
            
            # Apply 12pt font size to all paragraphs
            for cell in row_cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(12)
            
        end_row_idx = len(table.rows) - 1
        if start_row_idx != end_row_idx:
            table.cell(start_row_idx, 0).merge(table.cell(end_row_idx, 0))
            table.cell(start_row_idx, 1).merge(table.cell(end_row_idx, 1))

    return doc

def create_vocabulary_docx(words: list[str], title: str = "VOCABULARY LIST", use_vi_translation: bool = False, api_key: str = None, progress_callback=None) -> tuple[Document, list[str]]:
    all_word_data = []
    failed_words = []
    
    for i, word in enumerate(words):
        norm_word = word.strip().lower()
        if progress_callback:
            progress_callback(i, len(words), norm_word, status="Fetching...")
        
        result = fetch_word_data(norm_word)
        if result:
            headword, senses = result
            # Handle translation if requested
            if use_vi_translation and api_key:
                if progress_callback:
                    progress_callback(i, len(words), headword, status="Translating...")
                
                for sense in senses:
                    pos = sense['word_info']['pos']
                    definition = sense['meaning_data']['def']
                    translation = translate_meaning_to_vi(headword, pos, definition, api_key)
                    sense['vi_translation'] = translation
            
            all_word_data.append((headword, senses))
            if progress_callback:
                progress_callback(i, len(words), headword, status="Success")
        else:
            failed_words.append(word)
            if progress_callback:
                progress_callback(i, len(words), norm_word, status="Failed")
        
        time.sleep(1) # Respectful delay
        
    if not all_word_data:
        raise ValueError("No data could be fetched for any of the provided words.")

    doc = generate_docx_from_data(all_word_data, title=title)
    return doc, failed_words
