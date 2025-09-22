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

    # Extract question number/part
    question = parts[-1]
    # Normalize question numbers for sorting
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
    if len(parts) < 5:  # Must have at least 5 parts
        return False

    question_part = parts[4]  # Fifth element
    
    # Handle both underscore and period formats
    # Examples: "11a", "H_11a", "S_7a"
    if '_' in question_part:
        # For underscore format like "H_11a", extract the part after underscore
        underscore_parts = question_part.split('_')
        if len(underscore_parts) > 1:
            question_number = underscore_parts[1]  # Get "11a" from "H_11a"
        else:
            question_number = question_part
    else:
        # For period format like "11a"
        question_number = question_part
    
    # Check if it starts with a digit
    return len(question_number) > 0 and question_number[0].isdigit()

sorted_questions = [q for q in sorted_questions if is_valid_question_format(q)]

all_questions = []
if edition == "5. Fifth Edition - TOPIC":
    def get_base_question(code):
        """
        Extract the base question code by removing all sub-question parts.
        Examples:
        21M.1.AHL.TZ2.11a -> 21M.1.AHL.TZ2.11
        21M.1.AHL.TZ2.11b.ii -> 21M.1.AHL.TZ2.11
        20N.2.AHL.TZ0.H_11a -> 20N.2.AHL.TZ0.H_11
        20N.2.AHL.TZ0.H_11b -> 20N.2.AHL.TZ0.H_11
        """
        parts = code.split('.')
        if len(parts) < 5:
            return code
            
        question_part_index = 4
        if question_part_index >= len(parts):
            return code
            
        question_part = parts[question_part_index]
        
        # Handle underscore format (e.g., "H_11a")
        if '_' in question_part:
            prefix, suffix = question_part.split('_', 1)
            # Extract only the leading digits from the suffix
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
            # Handle period format (e.g., "11a")
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

    # Group questions by their base question
    question_groups = {}
    for code in sorted_questions:
        base = get_base_question(code)
        if base not in question_groups:
            question_groups[base] = []
        question_groups[base].append(code)
    
    # For each group, pick the best representative
    for base, codes in question_groups.items():
        # First preference: use the base question if it exists
        if base in links_dict:
            all_questions.append(base)
        # Second preference: use the first sub-question (usually 'a')
        else:
            # Sort the codes to get the first sub-question
            sorted_codes = sorted(codes, key=lambda x: x.split('.')[-1])
            all_questions.append(sorted_codes[0])
            # Make sure we have a link for this question
            if sorted_codes[0] not in links_dict and codes:
                # Use any available link from the group
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
                    # Add the file path to links_dict if not already present
                    if code not in links_dict:
                        links_dict[code] = f'{edition}/questionbank/en/teachers/ibdocs2/questionbanks/{subject}/question_node_trees/{filename}'

    # Group questions by their root number
    question_groups = {}
    for q in exam_codes:
        parts = q.split('.')
        last_part = parts[-1]
        # Get the root number (remove any letters)
        root_number = ''.join(filter(str.isdigit, last_part))
        if root_number:
            parts[-1] = root_number
            root = '.'.join(parts)
            if root not in question_groups:
                question_groups[root] = set()
            question_groups[root].add(q)

    # Process each group and add to all_questions
    for root, questions in question_groups.items():
        # If the root exists as a question, use only that
        if root in exam_codes:
            all_questions.append(root)
        else:
            # If root doesn't exist, add all sub-questions
            all_questions.extend(sorted(questions, key=parse_question_code))

    all_questions = sorted(all_questions, key=parse_question_code)
    #all_questions = sorted(all_questions, key=parse_question_code)
elif edition == "6. Sixth Edition - Group 4 2025":
    def is_valid_question(code):
        # Split the code into parts
        parts = code.split('.')
        if len(parts) < 2:
            return False

        # Get the last part (question number/letter)
        last_part = parts[-1].lower()

        # Match standalone numbers (e.g., "4") or letters (e.g., "a")
        if last_part.isdigit() or (len(last_part) == 1 and last_part.isalpha()):
            return True

        # Match first parts of questions (e.g., "4a", "4a.i", "b.i")
        # But reject parts like "4b.ii", "3c.i", "9a.ii"
        if len(last_part) > 1:
            # If it starts with a number, should only be followed by 'a' or 'a.i'
            if last_part[0].isdigit():
                return last_part.endswith('a') or last_part.endswith('a.i')
            # If it starts with a letter, should only be followed by '.i' or nothing
            elif last_part[0].isalpha():
                return len(last_part) == 1 or last_part.endswith('.i')

        return False

    # Filter the sorted questions
    all_questions = [q for q in sorted_questions if is_valid_question(q)]

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

for question_code in all_questions:
    link_path = links_dict[question_code]
    absolute_path = os.path.join(script_dir, link_path)

    with open(absolute_path, 'r', encoding='utf-8') as f:
        question_content = f.read()

    question_soup = BeautifulSoup(question_content, "html.parser")

    # Create a container div for both code and question
    container_div = soup.new_tag('div', attrs={'class': 'question-container'})

    # Create and add the code div
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

# Add some CSS to style the question code
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
soup.head.append(style_tag)

# 1. Remove alttext in all <math> tags
for math_tag in soup.find_all('math'):
    if 'alttext' in math_tag.attrs:
        math_tag['alttext'] = ''

# 2. Clean <mtext> and <mo> content
for tag in soup.find_all(['mtext', 'mo']):
    if tag.string:
        # Remove weird function symbol (U+2061)
        tag.string = tag.string.replace("\u2061", "")
        # Replace NBSP with numeric space
        tag.string = tag.string.replace("\u00A0", "&#32;")
        # Replace literal spaces with numeric space
        tag.string = tag.string.replace(" ", "&#32;")

# 3. Optional: replace &nbsp; in the raw HTML as extra safeguard
html_str = str(soup)
html_str = html_str.replace("&nbsp;", "&#32;")

with open(destination_file, 'w', encoding='utf-8') as f:
    f.write(str(soup))
