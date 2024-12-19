import re
import tiktoken
from typing import List, Dict

def clean_text(text: str) -> str:
    """
    清理文本，移除目录和不必要的内容
    
    Args:
        text: 原始文本
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
        
    lines = text.split('\n')
    cleaned_lines = []
    
    # 目录项的正则模式
    toc_patterns = [
        r'^\d+\..*$',  # 匹配 "1. xxx"
        r'^\d+\.\d+.*$',  # 匹配 "1.1 xxx"
        r'^第[一二三四五六七八九十]+[章节].*$',  # 匹配 "第一章 xxx"
        r'^目录$',  # 匹配 "目录"
        r'^Table of Contents$',  # 匹配英文目录
        r'^\s*\d+\s*$',  # 匹配单独的页码
    ]
    
    is_in_toc = False
    for line in lines:
        # 检查是否是目录开始
        if re.match(r'^目录|^Table of Contents', line, re.IGNORECASE):
            is_in_toc = True
            continue
            
        # 检查是否是目录结束（通常是遇到第一章或其他正文标记）
        if is_in_toc and (re.match(r'^第[一二三四五六七八九十]+[章节]|^1\.|^Chapter', line)):
            is_in_toc = False
            
        # 如果在目录区域内，跳过该行
        if is_in_toc:
            continue
            
        # 检查是否匹配任何目录模式
        is_toc_line = any(re.match(pattern, line.strip()) for pattern in toc_patterns)
        
        # 如果不是目录行且不是空行，保留该行
        if not is_toc_line and line.strip():
            # 将连续的点号替换为单个空格，并保留页码
            line = re.sub(r'\s*\.+\s*(?=\d+[-\d]*$)', ' ', line.strip())
            # 移除其他位置的连续点号
            line = re.sub(r'\s*\.+\s*', ' ', line)
            cleaned_lines.append(line)
    
    # 重新组合文本，使用换行符连接
    cleaned_text = '\n'.join(cleaned_lines)
    
    # 移除连续的多个换行符
    cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
    
    return cleaned_text.strip()

def split_text_with_overlap(text: str, chunk_size: int = 1024, 
                          overlap: int = 200, model: str = "gpt-3.5-turbo") -> List[str]:
    """
    将文本分割成指定token大小的块，支持重叠
    
    Args:
        text: 要分割的文本
        chunk_size: 每个块的目标token大小
        overlap: 重叠的token大小
        model: 使用的模型名称，用于选择对应的tokenizer
    Returns:
        List[str]: 文本块列表
    """
    if not text:
        return []
    
    # 初始化tokenizer
    encoding = tiktoken.encoding_for_model(model)
    
    # 将整个文本转换为token
    tokens = encoding.encode(text)
    total_tokens = len(tokens)
    
    chunks = []
    start = 0
    
    while start < total_tokens:
        # 计算当前块的结束位置
        end = start + chunk_size
        
        # 如果不是最后一块，需要确保有重叠
        if end < total_tokens:
            # 确保下一块从重叠位置开始
            next_start = end - overlap
        else:
            # 如果是最后一块，直接取到结尾
            end = total_tokens
            
        # 提取当前块的tokens并解码为文本
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        # 更新开始位置（考虑重叠）
        if end < total_tokens:
            start = next_start
        else:
            break
    
    return chunks

def extract_terms_from_xml(xml_text: str) -> List[Dict[str, str]]:
    """
    从XML文本中提取术语，并进行chunk内去重
    
    Args:
        xml_text: XML格式的文本
    Returns:
        List[Dict[str, str]]: 术语列表
    """
    if not xml_text:
        return []
        
    # 使用集合进行chunk内去重
    terms_set = set()
    
    # 使用正则表达式提取<term>标签中的内容
    term_pattern = r'<term>(.*?)</term>'
    matches = re.findall(term_pattern, xml_text)
    
    for term in matches:
        terms_set.add(term.strip())
    
    # 转换回列表格式
    return [{'term': term} for term in sorted(terms_set)]