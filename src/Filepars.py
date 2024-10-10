import logging
import io
import aiohttp
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from docx2python import docx2python
from bs4 import BeautifulSoup

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Parser:
    """Считывает всё, что находится в файле, в виде текста"""
    
    def __init__(self, file_content: bytes, file_type: str):
        self.file_content = file_content
        self.file_type = file_type.lower()

    def read_from_txt(self) -> str:
        """Читает текст из .txt файла"""
        try:
            text = self.file_content.decode('utf-8')
            logger.info("Успешно прочитан .txt файл.")
            return text
        except Exception as e:
            logger.error(f"Ошибка при чтении .txt файла: {e}")
            raise

    def read_from_pdf(self) -> str:
        """Читает текст из .pdf файла"""
        resource_manager = PDFResourceManager()
        output = io.StringIO()
        laparams = LAParams()
        device = TextConverter(resource_manager, output, laparams=laparams)
        interpreter = PDFPageInterpreter(resource_manager, device)

        try:
            with io.BytesIO(self.file_content) as file:
                for page in PDFPage.get_pages(file):
                    interpreter.process_page(page)
            text = output.getvalue()
            logger.info("Успешно прочитан .pdf файл.")
            return text
        except Exception as e:
            logger.error(f"Ошибка при чтении .pdf файла: {e}")
            raise
        finally:
            device.close()
            output.close()

    def read_from_docx(self) -> str:
        """Читает текст из .docx файла"""
        try:
            docx_data = docx2python(io.BytesIO(self.file_content))
            # Используем list comprehension для простоты
            text = "\n".join("".join(para) for para in docx_data.text)
            logger.info("Успешно прочитан .docx файл.")
            return text
        except Exception as e:
            logger.error(f"Ошибка при чтении .docx файла: {e}")
            raise

    async def read_from_html(self, url: str) -> str:
        """Читает текст из HTML-страницы по указанному URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        soup = BeautifulSoup(html_content, 'html.parser')
                        text = soup.get_text(separator='\n')
                        logger.info(f"Успешно прочитана HTML-страница: {url}")
                        return text
                    else:
                        logger.error(f"Ошибка при получении HTML-страницы: статус {response.status}, URL: {url}")
                        raise Exception(f"Ошибка при получении HTML-страницы: статус {response.status}, URL: {url}")
        except Exception as e:
            logger.error(f"Ошибка при чтении HTML: {e}, URL: {url}")
            raise
