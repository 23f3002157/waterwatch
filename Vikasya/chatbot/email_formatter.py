# email_formatter.py
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import sys

# Get input from Node.js (plain text and HTML)
input_data = json.loads(sys.argv[1])
plain_text = input_data["plain_text"]
html_content = input_data["html_content"]
subject = input_data["subject"]
to = "watercont@gmail.com"
from_addr = input_data["from"]
media_path = input_data.get("media_path")

# Create a multipart message
msg = MIMEMultipart('alternative')
msg['Subject'] = subject
msg['From'] = from_addr
msg['To'] = to

# Attach plain text part
part1 = MIMEText(plain_text, 'plain')
msg.attach(part1)

# Attach HTML part
part2 = MIMEText(html_content, 'html')
msg.attach(part2)

        

# Convert to string and output
print(msg.as_string())