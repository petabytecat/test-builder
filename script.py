import shutil
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
import re
import sys

if len(sys.argv) < 2:
    print("Usage: python script.py <source_url> [destination_file]")
    sys.exit(1)

source_url = sys.argv[1]
destination_file = sys.argv[2] if len(sys.argv) > 2 else "copy.html"

parsed_url = urlparse(source_url)
file_path = unquote(parsed_url.path).strip()

try:
    shutil.copy(file_path, destination_file)
    print(f"Copied {file_path} to {destination_file}")
except FileNotFoundError:
    print(f"Source file not found: {file_path}")
    sys.exit(1)

try:
    edition = file_path.split('/')[6]
    subject = file_path.split('/')[12]
    print(f"Edition: {edition}")
    print(f"Subject: {subject}")
except IndexError:
    print("Error parsing edition or subject from file path.")
    sys.exit(1)

with open(destination_file, 'r', encoding='utf-8') as f:
    content = f.read()

soup = BeautifulSoup(content, "html.parser")

for tag in soup.find_all(['link', 'script', 'img', 'a']):
    for attr in ['href', 'src']:
        if tag.has_attr(attr):
            if tag[attr].startswith('../../../../../../'):
                tag[attr] = tag[attr].replace('../../../../../../', '6. Sixth Edition - Group 4 2025/questionbank/')

def parse_question_code(code):
    match = re.match(r'(\d+)M\.(\d+)\.(HL|SL)\.TZ(\d+)\.([a-z0-9]+)', code)
    if match:
        year, paper, level, tz, question = match.groups()
        question_sort = ''.join([i.zfill(3) if i.isdigit() else i for i in re.findall(r'\d+|\D+', question)])
        return (int(year), int(paper), level, int(tz), question_sort)
    return (0, 0, '', 0, '')

links_dict = {}
for li in soup.find_all("li"):
    question_code = li.text.split(":")[0].strip()
    link_tag = li.find("a")
    if link_tag and "href" in link_tag.attrs:
        original_link = link_tag["href"]

        if re.search(r"\.\./question_node_trees/\d+\.html", original_link):
            correct_path = f'6. Sixth Edition - Group 4 2025/questionbank/en/teachers/ibdocs2/questionbanks/{subject}/question_node_trees/{original_link.split("/")[-1]}'
            links_dict[question_code] = correct_path

sorted_questions = sorted(links_dict.keys(), key=parse_question_code)

unwanted_elements = soup.find_all("div", {"class": "container-fluid"}) + soup.find_all("div", {"class": "footer bottom"})
for element in unwanted_elements:
    element.decompose()

all_questions_div = soup.new_tag('div', attrs={'class': 'all-questions'})
soup.body.append(all_questions_div)

for question_code in sorted_questions:
    try:
        link_path = links_dict[question_code]
        absolute_path = f'/Users/dewei.zhang/Documents/GitHub/test-builder/{link_path}'

        with open(absolute_path, 'r', encoding='utf-8') as f:
            question_content = f.read()

        question_soup = BeautifulSoup(question_content, "html.parser")
        question_div = question_soup.find('div', {'class': 'p-3 bg-white rounded'})

        if question_div:
            all_questions_div.append(question_div)

    except Exception as e:
        print(f"Error processing {question_code}: {str(e)}")

with open(destination_file, 'w', encoding='utf-8') as f:
    f.write(str(soup))
