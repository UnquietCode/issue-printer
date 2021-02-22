import json
import base64
import sys
import re
import os
import select
import urllib.request
from datetime import datetime


def replace_image(match):
    """
    Rewrite an re match object that matched an image tag
    Download the image and return a version of the tag rewritten
    to refer to the local version.
    """
    caption = match.group(1)
    url = match.group(2)
    extension = os.path.splitext(url)[1]

    if not extension:
        raise Exception("No extension at the end of {0}".format(url))

    prefix = f'data:image/{extension.lower()};base64,'
    with urllib.request.urlopen(url) as response:
        data_url = prefix + base64.b64encode(response.read())
        
    return "![{0}]({1})".format(caption, data_url)


def replace_images(md):
    """
    Rewrite a Markdown string to replace any images with local versions
    'md' should be a GitHub Markdown string; the return value is a version
    of this where any references to images have been downloaded and replaced
    by a reference to a local copy.
    """
    return re.sub(r'\!\[(.*?)\]\((.*?)\)', replace_image, md)


def build_markdown(issue):
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
    body = replace_images(body)
    
    md_content += body
    md_content += "\n\n"

    # handle comments
    if issue['comments'] > 0:
        with urllib.request.urlopen(issue['comments_url']) as response:
            comments_request = response.read()
        
        for comment in comments_request.json():
            USER = comment['user']['login']
            RAW_DATETIME = comment['created_at']
            DATETIME_OBJ = datetime.strptime(RAW_DATETIME, '%Y-%m-%dT%H:%M:%SZ')
            DATE = DATETIME_OBJ.date() #2021-01-09T20:41:02Z
            DATE_WORDS = DATE.strftime('%A %d %B %Y')
            md_content += ("\n### @{0} wrote on {1}".format(USER, DATE_WORDS))
            md_content += '\n\n'
            comment_body = comment['body']
            comment_body = re.sub(r'^(#+)', r'###\1', comment_body)
            comment_body = replace_images(comment_body)
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
            print("usage: cat issue.json | python3 run.py <output.md>")
            exit(1)
        elif len(sys.argv) == 2:
            markdown_file_path = sys.argv[1]
        else:
            markdown_file_path = os.path.join(os.getcwd(), 'output.md')
        
        json_data = stdin
    
    # reading file paths passed as arguments
    else:
        if len(sys.argv) > 3 or len(sys.argv) < 2:
            print("usage: python3 run.py <input.json> (output.md)")
            exit(1)
        elif len(sys.argv) == 3:
            file_path_1 = sys.argv[1]
            file_path_2 = sys.argv[2]
            
            if file_path_1.lower().endswith(".json"):
                json_file = file_path_1
                markdown_file_path = file_path_2
            elif file_path_2.lower().endswith(".json"):
                json_file = file_path_2
                markdown_file_path = file_path_1
            
            if not markdown_file_path.lower().endswith(".md"):
                markdown_file_path += ".md"
        else:
            json_file = sys.argv[1]
            path_parts = os.path.split(json_file)
            file_name = path_parts[-1]
            base_dir = json_file[0:-1*(len(file_name))]
            markdown_file_name = file_name[0:file_name.rindex('.')] + ".md"
            markdown_file_path = os.path.join(base_dir, markdown_file_name)
        
        if json_file.endswith(".md"):
            raise Exception("JSON data file is missing, did you mean to send it over stdin?")
        
        with open(json_file, 'r') as markdown_file:
            json_data = markdown_file.read()
    
    # render the JSON to markdown
    json_data = json.loads(json_data)
    rendered = build_markdown(json_data)

    # write the markdown content to the correct location
    umask_original = os.umask(0o000)

    with os.fdopen(os.open(markdown_file_path, os.O_WRONLY | os.O_CREAT, 0o666), 'wb') as markdown_file:
        markdown_file.write(rendered)

    os.umask(umask_original)


if __name__ == '__main__':
    main()