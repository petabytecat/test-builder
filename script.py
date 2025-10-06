import shutil
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup, Tag
import re
import sys
import copy
import os

if len(sys.argv) < 2:
    print("Usage: python script.py <source_url> [include_subsection] [destination_file]")
    sys.exit(1)

source_url = sys.argv[1]
include_subsection = True if len(sys.argv) > 2 and sys.argv[2] == "True" else False
destination_file = sys.argv[3] if len(sys.argv) > 3 else "copy.html"

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
subject = relative_path.split(os.sep)[6]

with open(destination_file, 'r', encoding='utf-8') as f:
    content = f.read()
soup = BeautifulSoup(content, "html.parser")


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

sorted_questions = sorted(links_dict.keys(), key=parse_question_code)

def is_valid_question_format(code):
    parts = code.split('.')
    if len(parts) < 5:
        return False
    question_part = parts[4]
    if '_' in question_part:
        underscore_parts = question_part.split('_')
        question_number = underscore_parts[1] if len(underscore_parts) > 1 else question_part
    else:
        question_number = question_part
    return len(question_number) > 0 and question_number[0].isdigit()

sorted_questions = [q for q in sorted_questions if is_valid_question_format(q)]
all_questions = []


if edition == "5. Fifth Edition - TOPIC":
    def get_base_question(code):
        parts = code.split('.')
        if len(parts) < 5:
            return code
        question_part_index = 4
        question_part = parts[question_part_index]
        if '_' in question_part:
            prefix, suffix = question_part.split('_', 1)
            base_number = ''.join([c for c in suffix if c.isdigit()])
            if base_number:
                new_parts = parts[:question_part_index] + [f"{prefix}_{base_number}"]
                return '.'.join(new_parts)
        else:
            base_number = ''.join([c for c in question_part if c.isdigit()])
            if base_number:
                new_parts = parts[:question_part_index] + [base_number]
                return '.'.join(new_parts)
        return code

    question_groups = {}
    for code in sorted_questions:
        base = get_base_question(code)
        if base not in question_groups:
            question_groups[base] = []
        question_groups[base].append(code)

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

    html_roots = set()
    for q in sorted_questions:
        parts = q.split('.')
        if len(parts) >= 5:
            base_num = ''.join([c for c in parts[-1] if c.isdigit()])
            if base_num:
                parts[-1] = base_num
                html_roots.add('.'.join(parts))

    question_groups = {}
    for q in exam_codes:
        parts = q.split('.')
        root_number = ''.join(filter(str.isdigit, parts[-1]))
        if root_number:
            parts[-1] = root_number
            root = '.'.join(parts)
            if root not in question_groups:
                question_groups[root] = set()
            question_groups[root].add(q)

    filtered_exam_codes = set()
    for root, questions in question_groups.items():
        if root in html_roots:
            filtered_exam_codes.update(questions)

    for root, questions in question_groups.items():
        if root in html_roots:
            if root in filtered_exam_codes:
                all_questions.append(root)
            else:
                all_questions.extend(sorted(questions, key=parse_question_code))
    all_questions = sorted(set(all_questions), key=parse_question_code)


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


# Create a clean new soup (keep CSS/head but clear body)
clean_soup = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
if soup.head:
    clean_soup.head.extend(copy.copy(tag) for tag in soup.head.contents if isinstance(tag, Tag))

all_questions_div = clean_soup.new_tag('div', attrs={'class': 'all-questions'})
clean_soup.body.append(all_questions_div)

for question_code in all_questions:
    link_path = links_dict[question_code]
    absolute_path = os.path.join(script_dir, link_path)
    with open(absolute_path, 'r', encoding='utf-8') as f:
        question_content = f.read()
    question_soup = BeautifulSoup(question_content, "html.parser")

    # Wrap question code
    container_div = clean_soup.new_tag('div', attrs={'class': 'question-container'})
    code_div = clean_soup.new_tag('div', attrs={'class': 'question-code'})
    code_div.string = question_code
    container_div.append(code_div)

    # Extract only the question content
    if edition == "5. Fifth Edition - TOPIC":
        start_h2 = question_soup.find('h2', string='Question')
        end_h2 = question_soup.find('h2', string='Syllabus sections')
        if start_h2 and end_h2:
            content_div = clean_soup.new_tag('div', attrs={'class': 'question-content'})
            current = start_h2.find_next_sibling()
            while current and current != end_h2:
                next_sibling = current.find_next_sibling()
                content_div.append(copy.copy(current))
                current = next_sibling
            container_div.append(content_div)

    elif edition == "6. Sixth Edition - Group 4 2025":
        question_div = question_soup.find('div', {'class': 'p-3 bg-white rounded'})
        if question_div:
            content_div = clean_soup.new_tag('div', attrs={'class': 'question-content'})
            for child in question_div.contents:
                content_div.append(copy.copy(child))
            container_div.append(content_div)

    all_questions_div.append(container_div)


style_tag = clean_soup.new_tag('style')
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

clean_soup.head.append(style_tag)

for tag in clean_soup.find_all(['link', 'script', 'img', 'a']):
    for attr in ['href', 'src']:
        if tag.has_attr(attr):
            if tag[attr].startswith('../../../../../../'):
                if edition == "5. Fifth Edition - TOPIC":
                    tag[attr] = tag[attr].replace('../../../../../../', f'{edition}/questionbank.ibo.org/')
                elif edition == "6. Sixth Edition - Group 4 2025":
                    tag[attr] = tag[attr].replace('../../../../../../', f'{edition}/questionbank/')


# Clean math tags
for math_tag in clean_soup.find_all('math'):
    if 'alttext' in math_tag.attrs:
        math_tag['alttext'] = ''
for tag in clean_soup.find_all(['mtext', 'mo', 'mi']):
    if tag.string:
        tag.string = tag.string.replace("\u2061", "").replace(" ", "").replace("\u00A0", "")

# Save output
with open(destination_file, 'w', encoding='utf-8') as f:
    f.write(str(clean_soup))
