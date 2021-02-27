import json
import sys
import re
import os
import select
import hashlib
import zipfile
import urllib.request
from datetime import datetime
from tempfile import TemporaryDirectory

standard_headers = {'User-Agent': 'github-issue-printer/1.0'}

GH_TOKEN = os.environ.get('GITHUB_TOKEN', "").strip()
if GH_TOKEN: standard_headers['Authorization'] = f'Bearer {GH_TOKEN}'


def make_request(url):
    return urllib.request.Request(url, method='GET', headers=standard_headers)


def replace_image(match, tmp_dir):
    """
    Rewrite an re match object that matched an image tag
    Download the image and return a version of the tag rewritten
    to refer to the local version.
    """
    caption = match.group(1)
    url = match.group(2)
    hashed_url = hashlib.md5(url.encode('utf-8')).hexdigest()
    extension = os.path.splitext(url)[1]
    
    if not extension:
        raise Exception("No extension at the end of {0}".format(url))

    image_filename = hashed_url + extension.lower()
    image_path = os.path.join(tmp_dir, image_filename)
    
    if not os.path.exists(image_path):
        req = make_request(url)
        req.add_header('Accept-Encoding', 'gzip, deflate, br')
        
        with urllib.request.urlopen(req) as response:
            with open(image_path, 'wb') as f:
                f.write(response.read())

    return "![{0}]({1})".format(caption, image_filename)


def replace_images(md, tmp_dir):
    """
    Rewrite a Markdown string to replace any images with local versions
    'md' should be a GitHub Markdown string; the return value is a version
    of this where any references to images have been downloaded and replaced
    by a reference to a local copy.
    """
    return re.sub(r'\!\[(.*?)\]\((.*?)\)', lambda match: replace_image(match, tmp_dir), md)


def build_markdown(issue, markdown_file_name, tmp):
    number = issue['number']
    title = issue['title']
    body = issue['body']

    md_content = ""
    md_content += "# #{0} – {1}\n".format(number, title)
    md_content += "**Reported by @{0}**\n".format(issue['user']['login'])
    
    if issue['milestone']:
        md_content += '**Milestone: {0}**\n'.format(issue['milestone']['title'])
    
    md_content += "\n"
    
    # Increase the indent level of any Markdown heading
    body = re.sub(r'^(#+)', r'#\1', body)

    body = replace_images(body, tmp)
    
    md_content += body
    md_content += "\n\n"

    # process comments
    if issue['comments'] > 0:
        md_content += handle_comments(issue, tmp)

    markdown_file_path = os.path.join(tmp, markdown_file_name)
    
    with open(markdown_file_path, 'wb') as markdown_file:
        markdown_file.write(md_content.encode("utf-8"))


def handle_comments(issue, tmp_dir):
    md_content = ""
    req = make_request(issue['comments_url'])
    req.add_header('Accept', 'application/json')
    
    with urllib.request.urlopen(req) as response:
        comments_request = response.read()
    
    for comment in json.loads(comments_request):
        USER = comment['user']['login']
        RAW_DATETIME = comment['created_at']
        DATETIME_OBJ = datetime.strptime(RAW_DATETIME, '%Y-%m-%dT%H:%M:%SZ')
        DATE = DATETIME_OBJ.date()  # 2021-01-09T20:41:02Z
        DATE_WORDS = DATE.strftime('%A %d %B %Y')
        md_content += ("\n### @{0} wrote on {1}".format(USER, DATE_WORDS))
        md_content += '\n\n'
        comment_body = comment['body']
        comment_body = re.sub(r'^(#+)', r'###\1', comment_body)
        comment_body = replace_images(comment_body, tmp_dir)
        md_content += comment_body
        md_content += "\n\n"
    
    return md_content


def main():
    
    # read from standard in (note that select() only works for unix systems)
    stdin = ""
    
    while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        data = sys.stdin.read()
        
        if data:
            stdin += data
        else:
            break
    
    # reading from stdin
    if stdin := stdin.strip():
        if len(sys.argv) > 2:
            print("usage: cat issue.json | python3 run.py <output.zip>")
            exit(1)
        elif len(sys.argv) == 2:
            zip_file_path = sys.argv[1]
        else:
            zip_file_path = os.path.join(os.getcwd(), 'output.zip')
        
        json_data = stdin
        
        if not (json_data := json_data.strip()):
            print("stdin was empty")
            exit(2)
        
    # reading file paths passed as arguments
    else:
        if len(sys.argv) > 3 or len(sys.argv) < 2:
            print("usage: python3 run.py <input.json> (output.zip)")
            exit(3)
        elif len(sys.argv) == 3:
            file_path_1 = sys.argv[1]
            file_path_2 = sys.argv[2]
            
            if file_path_1.lower().endswith(".json"):
                json_file = file_path_1
                zip_file_path = file_path_2
            elif file_path_2.lower().endswith(".json"):
                json_file = file_path_2
                zip_file_path = file_path_1
            else:
                print("usage: python3 run.py <input.json> (output.zip)")
                exit(4)
                
            if not zip_file_path.lower().endswith(".zip"):
                zip_file_path += ".zip"
        else:
            json_file = sys.argv[1]
            json_file_name = os.path.basename(json_file)
            json_file_name = os.path.splitext(json_file_name)[0]
           
            base_path = os.path.dirname(os.path.abspath(json_file))
            zip_file_name = json_file_name + ".zip"
            zip_file_path = os.path.join(base_path, zip_file_name)
        
        if json_file.endswith(".zip"):
            raise Exception("JSON data file is missing, did you mean to send it over stdin?")
        
        with open(json_file, 'r') as json_data:
            json_data = json_data.read()
    
    zip_file_name = os.path.basename(zip_file_path)
    markdown_file_name = os.path.splitext(zip_file_name)[0] + ".md"
    
    # render the JSON to markdown
    json_data = json.loads(json_data)

    with TemporaryDirectory() as tmp:
        build_markdown(json_data, markdown_file_name, tmp)

        # write the markdown content to the correct location
        umask_original = os.umask(0o000)
        
        with zipfile.ZipFile(file=zip_file_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.external_attr = 0o666   #os.O_WRONLY | os.O_CREAT
        
            for file in os.listdir(tmp):
                file_path = os.path.join(tmp, file)
                zip_file.write(file_path, file)
            
        os.umask(umask_original)


if __name__ == '__main__':
    main()