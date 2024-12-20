import shutil
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup, Tag
import re
import sys
import copy
import os

if len(sys.argv) < 2:
    print("Usage: python script.py <source_url> [destination_file]")
    sys.exit(1)

source_url = sys.argv[1]
include_subsections = True if len(sys.argv) > 2 and sys.argv[2] == "True" else False
destination_file = sys.argv[3] if len(sys.argv) > 3 else "copy.html"

parsed_url = urlparse(source_url)
file_path = unquote(parsed_url.path).strip()

try:
    shutil.copy(file_path, destination_file)
    print(f"Copied {file_path} to {destination_file}")
except FileNotFoundError:
    print(f"Source file not found: {file_path}")
    sys.exit(1)

# Find base path by locating 'test-builder' in the path
base_path_match = re.search(r'(.*?test-builder)', file_path)
if not base_path_match:
    print("Error: 'test-builder' directory not found in path")
    sys.exit(1)
base_path = base_path_match.group(1)

relative_path = file_path[len(base_path):].lstrip('/')

edition = relative_path.split("/")[0]
subject = relative_path.split("/")[6]

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
    match = re.match(r'(\d+)M\.(\d+)\.(HL|SL)\.TZ(\d+)\.([a-z0-9]+)', code)
    if match:
        year, paper, level, tz, question = match.groups()
        question_sort = ''.join([i.zfill(3) if i.isdigit() else i for i in re.findall(r'\d+|\D+', question)])
        return (int(year), int(paper), level, int(tz), question_sort)
    return (0, 0, '', 0, '')

if edition == "5. Fifth Edition - TOPIC":
    rows = soup.find_all(class_="module")
elif edition == "6. Sixth Edition - Group 4 2025":
    rows = soup.find_all(class_="row")

links_dict = {}
for row in rows:
    header = row.find('h3')
    if (header and not "questions" in header.text) or not header:
        continue
    if header and "Sub sections" in header.text and not include_subsections:
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

def remove_duplicate_questions(question_codes):
    # Function to get the base question number without the part
    def get_base_question(code):
        # Split by dot and get all parts except the last
        parts = code.split('.')
        # Remove the last character if it's a letter
        if parts[-1][-1].isalpha():
            parts[-1] = parts[-1][:-1]
        return '.'.join(parts)

    seen_questions = set()
    unique_codes = []

    for code in question_codes:
        base = get_base_question(code)
        if base not in seen_questions:
            seen_questions.add(base)
            unique_codes.append(code)

    return unique_codes

unique_questions = remove_duplicate_questions(sorted_questions)

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

# Remove footer for both editions
for element in soup.select(".footer.bottom"):
    element.extract()

all_questions_div = soup.new_tag('div', attrs={'class': 'all-questions'})

if edition == "5. Fifth Edition - TOPIC":
    page_content_container = soup.find('div', class_='page-content container')

    # Append all_questions_div to the container
    if page_content_container:
        page_content_container.append(all_questions_div)
    else:
        print("Error: 'page-content container' not found!")
elif edition == "6. Sixth Edition - Group 4 2025":
    soup.body.append(all_questions_div)

for question_code in unique_questions:
    link_path = links_dict[question_code]
    absolute_path = os.path.join(base_path, link_path)

    with open(absolute_path, 'r', encoding='utf-8') as f:
        question_content = f.read()

    question_soup = BeautifulSoup(question_content, "html.parser")

for question_code in unique_questions:
    link_path = links_dict[question_code]
    absolute_path = os.path.join(base_path, link_path)

    with open(absolute_path, 'r', encoding='utf-8') as f:
        question_content = f.read()

    question_soup = BeautifulSoup(question_content, "html.parser")

    if edition == "5. Fifth Edition - TOPIC":
        # Find the starting and ending points
        start_h2 = question_soup.find('h2', string='Question')
        end_h2 = question_soup.find('h2', string='Syllabus sections')

        if start_h2 and end_h2:
            # Create a new div to hold the content
            content_div = BeautifulSoup('<div></div>', 'html.parser').div

            # Get all siblings between Question and Syllabus sections
            current = start_h2
            while current and current != end_h2:
                next_sibling = current.find_next_sibling()
                if current == start_h2 or not any(parent for parent in current.parents if parent in content_div.descendants):
                    content_div.append(copy.copy(current))
                current = next_sibling if next_sibling else end_h2

            question_div = content_div

    elif edition == "6. Sixth Edition - Group 4 2025":
        question_div = question_soup.find('div', {'class': 'p-3 bg-white rounded'})

    if question_div:
        all_questions_div.append(question_div)

with open(destination_file, 'w', encoding='utf-8') as f:
    f.write(str(soup))
