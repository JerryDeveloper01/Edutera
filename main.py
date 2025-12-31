import requests
from bs4 import BeautifulSoup
import json
import re
import time
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EduteriaExtractor:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.base_url = "https://www.eduteria.live/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(self.headers)
    
    def login(self):
        """Login to Eduteria Live"""
        try:
            login_url = f"{self.base_url}login"
            response = self.session.get(login_url)
            
            # Get CSRF token
            soup = BeautifulSoup(response.content, 'html.parser')
            csrf_token = soup.find('input', {'name': '_token'})
            
            if csrf_token:
                csrf_value = csrf_token.get('value')
            else:
                csrf_value = ''
            
            # Login data
            login_data = {
                'email': self.username,
                'password': self.password,
                'remember': 'on'
            }
            
            # Add CSRF token if available
            if csrf_value:
                login_data['_token'] = csrf_value
            
            # Perform login
            login_response = self.session.post(login_url, data=login_data)
            
            # Check if login was successful
            if 'dashboard' in login_response.url or 'profile' in login_response.url:
                logger.info("Login successful")
                return True
            else:
                logger.error("Login failed")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
    
    def get_courses(self):
        """Get list of purchased courses"""
        try:
            courses_url = f"{self.base_url}dashboard"
            response = self.session.get(courses_url)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find course elements
            courses = []
            course_elements = soup.find_all('div', class_='course-card')
            
            for element in course_elements:
                title_element = element.find('h3', class_='course-title')
                link_element = element.find('a')
                
                if title_element and link_element:
                    course = {
                        'title': title_element.text.strip(),
                        'url': link_element.get('href'),
                        'id': self.extract_course_id(link_element.get('href'))
                    }
                    courses.append(course)
            
            logger.info(f"Found {len(courses)} courses")
            return courses
            
        except Exception as e:
            logger.error(f"Error getting courses: {str(e)}")
            return []
    
    def extract_course_id(self, url):
        """Extract course ID from URL"""
        match = re.search(r'/course/(\d+)', url)
        return match.group(1) if match else None
    
    def get_course_content(self, course_url):
        """Get course content including videos and PDFs"""
        try:
            response = self.session.get(course_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find video and PDF links
            content = {
                'videos': [],
                'pdfs': [],
                'title': '',
                'description': ''
            }
            
            # Get course title
            title_element = soup.find('h1', class_='course-title')
            if title_element:
                content['title'] = title_element.text.strip()
            
            # Get description
            desc_element = soup.find('div', class_='course-description')
            if desc_element:
                content['description'] = desc_element.text.strip()
            
            # Look for video elements
            video_elements = soup.find_all('video')
            for video in video_elements:
                src = video.get('src')
                if src:
                    content['videos'].append({
                        'title': 'Video',
                        'url': src
                    })
            
            # Look for PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$'))
            for link in pdf_links:
                href = link.get('href')
                if href and href.endswith('.pdf'):
                    content['pdfs'].append({
                        'title': link.text.strip(),
                        'url': href
                    })
            
            # Look for other video links (iframe or data attributes)
            video_links = soup.find_all('a', href=re.compile(r'(youtube|vimeo)'))
            for link in video_links:
                href = link.get('href')
                if href:
                    content['videos'].append({
                        'title': link.text.strip(),
                        'url': href
                    })
            
            return content
            
        except Exception as e:
            logger.error(f"Error extracting course content: {str(e)}")
            return None
    
    def extract_all_content(self):
        """Extract content from all courses"""
        courses = self.get_courses()
        all_content = []
        
        for course in courses:
            logger.info(f"Processing course: {course['title']}")
            content = self.get_course_content(course['url'])
            
            if content:
                content['course_title'] = course['title']
                all_content.append(content)
                
                # Add delay to avoid rate limiting
                time.sleep(2)
        
        return all_content

class TelegramBot:
    def __init__(self, token):
        self.bot = Bot(token=token)
        self.session = asyncio.Session()
    
    async def send_message(self, chat_id, text):
        """Send message to Telegram chat"""
        try:
            await self.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
    
    async def send_file(self, chat_id, file_path, caption):
        """Send file to Telegram chat"""
        try:
            with open(file_path, 'rb') as file:
                await self.bot.send_document(chat_id=chat_id, document=file, caption=caption)
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")

def generate_txt_content(content_list):
    """Generate TXT content from extracted data"""
    txt_content = []
    
    txt_content.append("EDUTERIA LIVE COURSE EXTRACTOR")
    txt_content.append("=" * 40)
    txt_content.append(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    txt_content.append("")
    
    for course in content_list:
        txt_content.append(f"Course: {course['course_title']}")
        txt_content.append("-" * 50)
        
        # Videos
        if course.get('videos'):
            txt_content.append("VIDEOS:")
            for video in course['videos']:
                txt_content.append(f"  Title: {video['title']}")
                txt_content.append(f"  URL: {video['url']}")
                txt_content.append("")
        
        # PDFs
        if course.get('pdfs'):
            txt_content.append("PDF FILES:")
            for pdf in course['pdfs']:
                txt_content.append(f"  Title: {pdf['title']}")
                txt_content.append(f"  URL: {pdf['url']}")
                txt_content.append("")
        
        txt_content.append("")
    
    return "\n".join(txt_content)

def save_txt_file(content, filename):
    """Save content to TXT file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Content saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        return False

def main():
    # Configuration
    EDUTERIA_USERNAME = "your_email@example.com"  # Replace with your Eduteria email
    EDUTERIA_PASSWORD = "your_password"           # Replace with your Eduteria password
    TELEGRAM_BOT_TOKEN = "7951229858:AAEcDzEYxxlf6pfD_JlsonyXzgzuOpTyKA8" # Replace with your Telegram bot token
    TELEGRAM_CHAT_ID = "8517203930"             # Replace with your Telegram chat ID
    
    try:
        # Create extractor
        extractor = EduteriaExtractor(EDUTERIA_USERNAME, EDUTERIA_PASSWORD)
        
        # Login
        if not extractor.login():
            logger.error("Login failed")
            return
        
        logger.info("Starting course extraction...")
        
        # Extract all content
        content_list = extractor.extract_all_content()
        
        if not content_list:
            logger.error("No content extracted")
            return
        
        # Generate TXT content
        txt_content = generate_txt_content(content_list)
        
        # Save to file
        filename = f"eduteria_extracted_content_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        save_txt_file(txt_content, filename)
        
        logger.info(f"Content extracted successfully. File saved as {filename}")
        
        # Send via Telegram bot (optional)
        try:
            # Create Telegram bot
            bot = TelegramBot(TELEGRAM_BOT_TOKEN)
            
            # Send TXT file via Telegram
            with open(filename, 'rb') as file:
                # You can send the file content as text message
                message = f"Extracted content from Eduteria Live\n\n{txt_content[:2000]}..."  # First 2000 chars
                logger.info(f"Sending message to Telegram chat {TELEGRAM_CHAT_ID}")
                # Note: For large files, you might want to send as document
                # This is a simplified version
                
        except Exception as e:
            logger.warning(f"Telegram sending failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"Main execution error: {str(e)}")

if __name__ == "main.py":
    main()
