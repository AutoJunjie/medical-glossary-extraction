from markitdown import MarkItDown
from typing import Optional
import os

class DocumentParser:
    """文档解析器，用于处理不同格式的文档"""
    
    def __init__(self):
        self.markitdown = MarkItDown()
    
    def parse_pdf(self, file_path: str) -> Optional[str]:
        """
        解析PDF文档
        
        Args:
            file_path: PDF文件路径
        Returns:
            str: 提取的文本内容，如果解析失败则返回None
        """
        try:
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                return None
                
            result = self.markitdown.convert(file_path)
            if not result or not result.text_content:
                print(f"无法从文件中提取文本: {file_path}")
                return None
                
            return result.text_content
            
        except Exception as e:
            print(f"解析文档时出错: {str(e)}")
            return None 