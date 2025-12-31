import os
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EduteraExtractor:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.base_url = "https://www.eduteria.live"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(self.headers)
        
    def login(self):
        """Login to Edutera Live"""
        try:
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('input', {'name': '_token'})

            login_data = {
                'email': self.username,
                'password': self.password,
                '_token': csrf_token['value'] if csrf_token else ''
            }

            login_response = self.session.post(login_url, data=login_data)

            if 'dashboard' in login_response.url.lower():
                logger.info("Successfully logged in to Edutera Live")
                return True
            else:
                logger.error("Login failed")
                return False
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
    
    def get_course_list(self):
        """Get all purchased courses"""
        try:
            dashboard_url = f"{self.base_url}/dashboard"
            response = self.session.get(dashboard_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            courses = []
            course_elements = soup.find_all('div', class_='course-card')

            for course in course_elements:
                title_element = course.find('h3', class_='course-title')
                link_element = course.find('a')

                if title_element and link_element:
                    course_info = {
                        'title': title_element.text.strip(),
                        'url': urljoin(self.base_url, link_element['href']),
                        'id': self.extract_course_id(link_element['href'])
                    }
                    courses.append(course_info)

            return courses
            
        except Exception as e:
            logger.error(f"Error getting course list: {str(e)}")
            return []
    
    def extract_course_id(self, url):
        """Extract course ID from URL"""
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) > 1 and path_parts[0] == 'course':
                return path_parts[1]
            return 'unknown'
        except Exception as e:
            logger.error(f"Error extracting course ID: {str(e)}")
            return 'unknown'
    
    def get_course_details(self, course_url):
        """Get detailed course information"""
        try:
            response = self.session.get(course_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_element = soup.find('h1', class_='course-title')
            course_title = title_element.text.strip() if title_element else "Unknown Course"
            
            content_elements = soup.find_all('div', class_='lesson-item')
            lessons = []

            for element in content_elements:
                title = element.find('span', class_='lesson-title')
                video_link = element.find('a', href=True)
                
                if title and video_link:
                    lessons.append({
                        'title': title.text.strip(),
                        'video_url': urljoin(self.base_url, video_link['href']),
                        'type': 'video'
                    })
            
            pdf_elements = soup.find_all('a', href=True)
            for pdf_element in pdf_elements:
                if pdf_element.get('href', '').endswith('.pdf'):
                    lessons.append({
                        'title': pdf_element.text.strip() or 'PDF Document',
                        'pdf_url': urljoin(self.base_url, pdf_element['href']),
                        'type': 'pdf'
                    })
            
            return {
                'title': course_title,
                'lessons': lessons,
                'total_lessons': len(lessons)
            }
            
        except Exception as e:
            logger.error(f"Error getting course details: {str(e)}")
            return None
    
    def extract_video_links(self, lesson_url):
        """Extract video links from lesson page"""
        try:
            response = self.session.get(lesson_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            video_elements = soup.find_all('video')
            if video_elements:
                video_sources = []
                for video in video_elements:
                    sources = video.find_all('source')
                    for source in sources:
                        if source.get('src'):
                            video_sources.append(urljoin(self.base_url, source['src']))
                return video_sources

            iframe = soup.find('iframe')
            if iframe and iframe.get('src'):
                return [urljoin(self.base_url, iframe['src'])]

            return []
            
        except Exception as e:
            logger.error(f"Error extracting video links: {str(e)}")
            return []

    def extract_all_content(self, course_url):
        """Extract all content from a course"""
        try:
            course_data = self.get_course_details(course_url)
            if not course_data:
                return None

            processed_lessons = []
            for lesson in course_data['lessons']:
                lesson_info = {
                    'title': lesson['title'],
                    'type': lesson['type']
                }

                if lesson['type'] == 'video':
                    video_links = self.extract_video_links(lesson['video_url'])
                    lesson_info['video_urls'] = video_links
                elif lesson['type'] == 'pdf':
                    lesson_info['pdf_url'] = lesson.get('pdf_url', '')

                processed_lessons.append(lesson_info)

            course_data['lessons'] = processed_lessons
            return course_data
            
        except Exception as e:
            logger.error(f"Error extracting course content: {str(e)}")
            return None


def generate_txt_content(course_data):
    """Generate TXT format content"""
    txt_content = f"Course: {course_data.get('title', 'Unknown Course')}\n"
    txt_content += "=" * 50 + "\n"
    txt_content += f"Total Lessons: {course_data.get('total_lessons', 0)}\n\n"

    for i, lesson in enumerate(course_data.get('lessons', []), 1):
        txt_content += f"Lesson {i}: {lesson.get('title', 'Unknown')}\n"

        if lesson.get('type') == 'video':
            txt_content += "  Video URLs:\n"
            for video_url in lesson.get('video_urls', []):
                txt_content += f"    - {video_url}\n"
        elif lesson.get('type') == 'pdf':
            txt_content += f"  PDF URL: {lesson.get('pdf_url', '')}\n"

        txt_content += "\n"

    return txt_content


class EduteraBot:
    def __init__(self, token):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.extractor = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        welcome_text = (
            "🤖 Edutera Live Course Extractor\n\n"
            "Send your Edutera Live login credentials in this format:\n"
            "username@email.com\npassword\n\n"
            "Or use /courses to see your available courses."
        )
        await update.message.reply_text(welcome_text)

    async def login_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle login credentials"""
        text = update.message.text
        lines = text.strip().split('\n')

        if len(lines) >= 2:
            username = lines[0].strip()
            password = lines[1].strip()

            # Create extractor instance
            self.extractor = EduteraExtractor(username, password)

            if self.extractor.login():
                await update.message.reply_text(
                    "✅ Successfully logged in!\n\n"
                    "Use /courses to see your available courses."
                )
            else:
                await update.message.reply_text(
                    "❌ Login failed. Please check your credentials."
                )
        else:
            await update.message.reply_text(
                "❌ Please provide both username and password in separate lines.\n"
                "Format:\nusername@email.com\npassword"
            )

    async def courses_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List available courses"""
        if not self.extractor:
            await update.message.reply_text("⚠️ Please login first using /start")
            return

        try:
            courses = self.extractor.get_course_list()
            if not courses:
                await update.message.reply_text("No courses found.")
                return

            keyboard = []
            for course in courses:
                keyboard.append([InlineKeyboardButton(
                    course['title'],
                    callback_data=f"course_{course['id']}"
                )])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Select a course to extract content:", reply_markup=reply_markup
            )

        except Exception as e:
            await update.message.reply_text(f"Error fetching courses: {str(e)}")

    async def extract_course(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Extract course content"""
        query = update.callback_query
        await query.answer()

        course_id = query.data.split('_')[1]
        logger.info(f"Extracting course ID: {course_id}")

        try:
            course_url = f"{self.extractor.base_url}/course/{course_id}"
            course_data = self.extractor.extract_all_content(course_url)

            if course_data:
                txt_content = generate_txt_content(course_data)
                filename = f"course_{course_id}_extracted.txt"

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(txt_content)

                # Send file
                with open(filename, 'rb') as f:
                    await query.message.reply_document(
                        document=f,
                        filename=filename,
                        caption=f"✅ Course extracted successfully!\n\n"
                               f"Course: {course_data.get('title', 'Unknown')}\n"
                               f"Lessons: {course_data.get('total_lessons', 0)}"
                    )

                os.remove(filename)  # Clean up

            else:
                await query.message.reply_text("❌ Failed to extract course content.")
        except Exception as e:
            await query.message.reply_text(f"Error extracting course: {str(e)}")

    def setup_handlers(self):
        """Setup all bot handlers"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("courses", self.courses_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.login_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.login_handler))
        self.app.add_handler(MessageHandler(filters.COMMAND, self.start))

async def main():
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    bot = EduteraBot(BOT_TOKEN)
    bot.setup_handlers()
    await bot.app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
