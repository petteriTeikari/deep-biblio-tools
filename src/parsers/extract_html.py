import sys

from bs4 import BeautifulSoup

filename = sys.argv[1]
with open(filename, encoding="utf-8") as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, "html.parser")

# Remove script and style elements
for script in soup(["script", "style"]):
    script.decompose()

# Get text
text = soup.get_text()

# Clean up whitespace
lines = (line.strip() for line in text.splitlines())
chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
text = "\n".join(chunk for chunk in chunks if chunk)

print(text)
