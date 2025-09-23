#!/usr/bin/env python3
import shutil
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup, Tag
import re
import sys
import copy
import os
import json
import ast

# --- Parse command-line arguments ---
if len(sys.argv) < 2:
    print("Usage: python script.py <source_url> [include_subsection] [destination_file] [question_filter_json | filter1 filter2 ...]")
    sys.exit(1)

source_url = sys.argv[1]
include_subsection = True if len(sys.argv) > 2 and sys.argv[2] == "True" else False
destination_file = sys.argv[3] if len(sys.argv) > 3 else "copy.html"

# Parse filters robustly:
question_filter = None
if len(sys.argv) > 4:
    # If there are multiple args after argv[4], treat them as separate filters
    if len(sys.argv) > 5:
        question_filter = [s.strip() for s in sys.argv[4:]]
    else:
        raw = sys.argv[4]
        # Try JSON
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, (list, tuple)):
                question_filter = [str(x).strip() for x in parsed]
            else:
                question_filter = [str(parsed).strip()]
        except Exception:
            # Try Python literal eval (handles single-quoted list etc.)
            try:
                parsed = ast.literal_eval(raw)
                if isinstance(parsed, (list, tuple)):
                    question_filter = [str(x).strip() for x in parsed]
                else:
                    question_filter = [str(parsed).strip()]
            except Exception:
                # Fallback: comma-separated or single value; strip surrounding quotes
                raw2 = raw.strip()
                if (raw2.startswith("'") and raw2.endswith("'")) or (raw2.startswith('"') and raw2.endswith('"')):
                    raw2 = raw2[1:-1]
                question_filter = [s.strip() for s in raw2.split(',') if s.strip()]

if question_filter:
    print(f"Filtering for {len(question_filter)} question(s): {question_filter}")

# --- Copy source file to destination (same as you had) ---
parsed_url = urlparse(source_url)
file_path = unquote(parsed_url.path).strip()

try:
    shutil.copy(file_path, destination_file)
    print(f"Copied {file_path} to {destination_file}")
except FileNotFoundError:
    print(f"Source file not found: {file_path}")
    sys.exit(1)

script_dir = os.path.dirname(os.path.abspath(__file__))

relative_path = os.path.relpath(file_path, script_dir)
edition = relative_path.split(os.sep)[0]
# NOTE: the index 6 is from your original script; if this fails adjust appropriately
subject = relative_path.split(os.sep)[6]

with open(destination_file, 'r', encoding='utf-8') as f:
    content = f.read()
soup = BeautifulSoup(content, "html.parser")

for tag in soup.find_all(['link', 'script', 'img', 'a']):
    for attr in ['href', 'src']:
        if tag.has_attr(attr):
            if tag[attr].startswith('../../../../../../'):
                if edition == "5. Fifth Edition - TOPIC":
                    tag[attr] = tag[attr].replace('../../../../../../', f'{edition}/questionbank.ibo.org/')
                elif edition == "6. Sixth Edition - Group 4 2025":
                    tag[attr] = tag[attr].replace('../../../../../../', f'{edition}/questionbank/')

def parse_question_code(code):
    parts = code.split('.')

    if len(parts) < 3:
        return ('ZZ', '', '', '')

    level = 'HL' if 'HL' in code else 'SL'
    paper = parts[1]
    year_part = parts[0]

    question = parts[-1]
    question_sort = ''.join([i.zfill(3) if i.isdigit() else i for i in re.findall(r'\d+|\D+', question)])
    return (level, paper, year_part, question_sort)

if edition == "5. Fifth Edition - TOPIC":
    rows = soup.find_all(class_="module")
elif edition == "6. Sixth Edition - Group 4 2025":
    rows = soup.find_all(class_="row")
else:
    rows = []

# Build links_dict from the page
links_dict = {}
for row in rows:
    header = row.find('h3')
    if (header and not "questions" in header.text) or not header:
        continue
    if header and "Sub sections" in header.text and not include_subsection:
        continue
    for li in row.find_all("li"):
        question_code = li.text.split(":")[0].strip()
        link_tag = li.find("a")
        if link_tag and "href" in link_tag.attrs:
            original_link = link_tag["href"]
            if re.search(r"\.\./question_node_trees/\d+\.html", original_link) or re.search(r"\.\./questions/\d+\.html", original_link):
                if edition == "5. Fifth Edition - TOPIC":
                    correct_path = f'{edition}/questionbank.ibo.org/en/teachers/00000/questionbanks/{subject}/questions/{original_link.split("/")[-1]}'
                elif edition == "6. Sixth Edition - Group 4 2025":
                    correct_path = f'{edition}/questionbank/en/teachers/ibdocs2/questionbanks/{subject}/question_node_trees/{original_link.split("/")[-1]}'
                links_dict[question_code] = correct_path

# --- Apply substring filter IMMEDIATELY after building links_dict ---
if question_filter:
    def matches_filter(code):
        return any(filt in code for filt in question_filter)

    before = len(links_dict)
    links_dict = {k: v for k, v in links_dict.items() if matches_filter(k)}
    after = len(links_dict)
    print(f"links_dict filtered: {before} -> {after} entries")

if not links_dict:
    print("Warning: no links remain after filtering. Exiting.")
    # Optionally exit or continue with empty output; here we exit to avoid writing huge page.
    sys.exit(0)

# Recompute sorted_questions from the filtered links_dict
sorted_questions = sorted(links_dict.keys(), key=parse_question_code)

def is_valid_question_format(code):
    parts = code.split('.')
    if len(parts) < 5:
        return False
    question_part = parts[4]
    if '_' in question_part:
        underscore_parts = question_part.split('_')
        if len(underscore_parts) > 1:
            question_number = underscore_parts[1]
        else:
            question_number = question_part
    else:
        question_number = question_part
    return len(question_number) > 0 and question_number[0].isdigit()

sorted_questions = [q for q in sorted_questions if is_valid_question_format(q)]

# --- Build all_questions using the same logic you had, but using the filtered sorted_questions ---
all_questions = []
if edition == "5. Fifth Edition - TOPIC":
    def get_base_question(code):
        parts = code.split('.')
        if len(parts) < 5:
            return code
        question_part_index = 4
        if question_part_index >= len(parts):
            return code
        question_part = parts[question_part_index]
        if '_' in question_part:
            prefix, suffix = question_part.split('_', 1)
            base_number = ''
            for char in suffix:
                if char.isdigit():
                    base_number += char
                else:
                    break
            if base_number:
                new_question_part = f"{prefix}_{base_number}"
                new_parts = parts[:question_part_index] + [new_question_part]
                return '.'.join(new_parts)
        else:
            base_number = ''
            for char in question_part:
                if char.isdigit():
                    base_number += char
                else:
                    break
            if base_number:
                new_parts = parts[:question_part_index] + [base_number]
                return '.'.join(new_parts)
        return code

    # Only group the filtered questions
    question_groups = {}
    filtered_sorted_questions = [q for q in sorted_questions if q in links_dict]
    
    for code in filtered_sorted_questions:
        base = get_base_question(code)
        question_groups.setdefault(base, []).append(code)

    for base, codes in question_groups.items():
        if base in links_dict:
            all_questions.append(base)
        else:
            sorted_codes = sorted(codes, key=lambda x: x.split('.')[-1])
            all_questions.append(sorted_codes[0])
            if sorted_codes[0] not in links_dict and codes:
                for code in codes:
                    if code in links_dict:
                        links_dict[sorted_codes[0]] = links_dict[code]
                        break

    all_questions = sorted(all_questions, key=parse_question_code)

elif edition == "6. Sixth Edition - Group 4 2025" and include_subsection == True:
    directory = os.path.join(script_dir, edition, 'questionbank/en/teachers/ibdocs2/questionbanks', subject, 'question_node_trees')
    exam_codes = set()
    for filename in os.listdir(directory):
        if filename.endswith('.html'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            file_soup = BeautifulSoup(file_content, 'html.parser')
            reference_code_label = file_soup.find('td', class_='info_label', string='Reference code')
            if reference_code_label:
                reference_code = reference_code_label.find_next_sibling('td', class_='info_value')
                if reference_code:
                    code = reference_code.get_text(strip=True)
                    exam_codes.add(code)
                    if code not in links_dict:
                        links_dict[code] = f'{edition}/questionbank/en/teachers/ibdocs2/questionbanks/{subject}/question_node_trees/{filename}'

    question_groups = {}
    for q in exam_codes:
        parts = q.split('.')
        last_part = parts[-1]
        root_number = ''.join(filter(str.isdigit, last_part))
        if root_number:
            parts[-1] = root_number
            root = '.'.join(parts)
            question_groups.setdefault(root, set()).add(q)

    for root, questions in question_groups.items():
        if root in exam_codes:
            all_questions.append(root)
        else:
            all_questions.extend(sorted(questions, key=parse_question_code))

    all_questions = sorted(all_questions, key=parse_question_code)

elif edition == "6. Sixth Edition - Group 4 2025":
    def is_valid_question(code):
        parts = code.split('.')
        if len(parts) < 2:
            return False
        last_part = parts[-1].lower()
        if last_part.isdigit() or (len(last_part) == 1 and last_part.isalpha()):
            return True
        if len(last_part) > 1:
            if last_part[0].isdigit():
                return last_part.endswith('a') or last_part.endswith('a.i')
            elif last_part[0].isalpha():
                return len(last_part) == 1 or last_part.endswith('.i')
        return False
    all_questions = [q for q in sorted_questions if is_valid_question(q)]

# Remove existing question rows and footer as before
if edition == "5. Fifth Edition - TOPIC":
    for element in soup.select(".module"):
        element.extract()
    for h4 in soup.find_all('h4'):
        h4.decompose()
    for h3 in soup.find_all('h3'):
        h3.decompose()
    for ul in soup.find_all('ul'):
        ul.decompose()
elif edition == "6. Sixth Edition - Group 4 2025":
    for element in soup.select(".row"):
        element.extract()

for element in soup.select(".footer.bottom"):
    element.extract()

all_questions_div = soup.new_tag('div', attrs={'class': 'all-questions'})

if edition == "5. Fifth Edition - TOPIC":
    page_content_container = soup.find('div', class_='page-content container')
    if page_content_container:
        page_content_container.append(all_questions_div)
    else:
        print("Error: 'page-content container' not found!")
elif edition == "6. Sixth Edition - Group 4 2025":
    soup.body.append(all_questions_div)

# Now loop ONLY over all_questions (which were created after filtering)
for question_code in all_questions:
    # skip if no link (safety)
    if question_code not in links_dict:
        print(f"Warning: link for {question_code} not found, skipping.")
        continue

    link_path = links_dict[question_code]
    absolute_path = os.path.join(script_dir, link_path)

    if not os.path.exists(absolute_path):
        print(f"Warning: file not found for {question_code}: {absolute_path}")
        continue

    with open(absolute_path, 'r', encoding='utf-8') as f:
        question_content = f.read()

    question_soup = BeautifulSoup(question_content, "html.parser")

    container_div = soup.new_tag('div', attrs={'class': 'question-container'})
    code_div = soup.new_tag('div', attrs={'class': 'question-code'})
    code_div.string = question_code
    container_div.append(code_div)

    if edition == "5. Fifth Edition - TOPIC":
        start_h2 = question_soup.find('h2', string='Question')
        end_h2 = question_soup.find('h2', string='Syllabus sections')
        if start_h2 and end_h2:
            content_div = BeautifulSoup('<div class="question-content"></div>', 'html.parser').div
            current = start_h2
            while current and current != end_h2:
                next_sibling = current.find_next_sibling()
                if current == start_h2 or not any(parent for parent in current.parents if parent in content_div.descendants):
                    content_div.append(copy.copy(current))
                current = next_sibling if next_sibling else end_h2
            container_div.append(content_div)
    elif edition == "6. Sixth Edition - Group 4 2025":
        question_div = question_soup.find('div', {'class': 'p-3 bg-white rounded'})
        if question_div:
            question_div['class'] = 'question-content'
            container_div.append(question_div)

    if container_div.find('div', {'class': 'question-content'}):
        all_questions_div.append(container_div)

# Add CSS and the math cleanup as you had
style_tag = soup.new_tag('style')
style_tag.string = '''
    .question-container {
        margin-bottom: 2em;
        border: 1px solid #ddd;
        border-radius: 4px;
    }
    .question-code {
        background-color: #f8f9fa;
        padding: 0.5em;
        border-bottom: 1px solid #ddd;
        font-family: monospace;
        font-weight: bold;
    }
    .question-content {
        padding: 1em;
    }
'''
# ensure head exists
if soup.head:
    soup.head.append(style_tag)
else:
    soup.insert(0, BeautifulSoup('<head></head>', 'html.parser'))
    soup.head.append(style_tag)

for math_tag in soup.find_all('math'):
    if 'alttext' in math_tag.attrs:
        math_tag['alttext'] = ''

for tag in soup.find_all(['mtext', 'mo', 'mi']):
    if tag.string:
        tag.string = tag.string.replace("\u2061", "")
        tag.string = tag.string.replace("\u00A0", "&#32;")
        tag.string = tag.string.replace(" ", "&#32;")

html_str = str(soup)
html_str = html_str.replace("&nbsp;", "&#32;")

with open(destination_file, 'w', encoding='utf-8') as f:
    f.write(html_str)

print(f"Wrote filtered output to {destination_file}")
