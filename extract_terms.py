import csv
from datetime import datetime
import concurrent.futures
from typing import List, Dict, Tuple
from utils.bedrock import BedrockClient
from utils.splitter import clean_text, split_text_with_overlap, extract_terms_from_xml
from utils.parser import DocumentParser
import pandas as pd
import os
import argparse

class TermExtractor:
    def __init__(self, bedrock_client: BedrockClient = None, max_workers: int = 5,
                 input_dir: str = "./input", output_dir: str = "./output"):
        """
        初始化术语提取器
        
        Args:
            bedrock_client: Bedrock客户端实例，如果为None则创建新实例
            max_workers: 并行处理的最大工作线程数
            input_dir: 输入文件目录
            output_dir: 输出文件目录
        """
        self.bedrock_client = bedrock_client or BedrockClient()
        self.max_workers = max_workers
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.doc_parser = DocumentParser()
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_terms_with_claude(self, text: str, lang: str) -> str:
        """使用 Claude 3 Sonnet 模型提取专业术语"""
        prompt = f"""Please extract only the medical-related {lang} terms from the text and format it in XML structure following this example:
<terminology>
  <term>患者通气</term>
  <term>呼吸机</term>
  <term>潮气量</term>
  <term>吸气</term>
  <term>呼气</term>
  <term>气道压力</term>
</terminology>

<terminology>
    <term>FIO2 sensor missing</term>
    <term>FiO2 sensor</term>
    <term>Low FIO2</term>
    <term>HMEs</term>
    <term>Oxygen inlet</term>
</terminology>

Extract terms that match these criteria:

Important extraction rules:

Extract ONLY {lang} medical terms
Extract complete medical terms
List each term only once
Include compound medical terms

Exclude:

Technical/mechanical terms
Non-medical terms
General descriptive terms

Please start the extraction with <output>:
{text}
        """
        
        system_prompt = "You are an app that creates playlists for a radio station that plays rock and pop music."
        
        try:
            response_text = self.bedrock_client.call_claude(
                prompt=prompt,
                system_prompt=system_prompt
            )
            print(response_text)
            return response_text
            
        except Exception as e:
            print(f"调用模型时出错: {str(e)}")
            return []

    def save_terms_to_csv(self, terms: List[Dict[str, str]], chunk_index: int, filename: str):
        """将提取的术语保存到CSV文件"""
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for term in terms:
                writer.writerow([chunk_index + 1, term['term']])

    def process_chunk(self, args: Tuple[str, int, str]) -> Tuple[int, List[Dict[str, str]]]:
        """
        处理单个文本块
        
        Args:
            args: (chunk, chunk_index, lang) 的元组
        Returns:
            tuple: (chunk_index, terms列表)
        """
        chunk, chunk_index, lang = args
        try:
            print(f"开始处理 Chunk {chunk_index + 1}...")
            xml_response = self.extract_terms_with_claude(chunk, lang)
            terms = extract_terms_from_xml(xml_response)
            print(f"Chunk {chunk_index + 1} 处理完成")
            return chunk_index, terms
        except Exception as e:
            print(f"处理 Chunk {chunk_index + 1} 时出错: {str(e)}")
            return chunk_index, []

    def process_chunks_parallel(self, chunks: List[str], csv_filename: str, lang: str):
        """
        并行处理多个文本块，并对所有chunks的结果进行去重
        
        Args:
            chunks: 文本块列表
            csv_filename: CSV文件名
            lang: 文档语言 ('zh' 或 'en')
        """
        # 准备任务列表
        tasks = [(chunk, i, lang) for i, chunk in enumerate(chunks)]
        
        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_chunk = {
                executor.submit(self.process_chunk, task): task[1]
                for task in tasks
            }
            
            # 收集结果
            all_terms = set()  # 用于全局去重
            chunk_term_map = {}  # 记录每个chunk的术语
            
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_index, terms = future.result()
                # 记录这个chunk的所有术语
                chunk_terms = set()
                for term in terms:
                    term_text = term['term']
                    if term_text not in all_terms:  # 只添加全局未出现的术语
                        all_terms.add(term_text)
                        chunk_terms.add(term_text)
                
                if chunk_terms:  # 如果这个chunk有新的术语
                    chunk_term_map[chunk_index] = chunk_terms
            
            # 按chunk顺序写入CSV
            with open(csv_filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for chunk_index in range(len(chunks)):
                    if chunk_index in chunk_term_map:
                        for term in sorted(chunk_term_map[chunk_index]):
                            writer.writerow([chunk_index + 1, term])

    def process_document(self, pdf_path: str, output_csv: str = None, lang: str = "zh"):
        """
        处理单个PDF文档并提取术语
        
        Args:
            pdf_path: PDF文件路径
            output_csv: 输出CSV文件路径，如果为None则自动生成
            lang: 文档语言 ('zh' 或 'en')
        Returns:
            str: 输出CSV文件路径
        """
        if output_csv is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_csv = os.path.join(self.output_dir, f'technical_terms_{timestamp}.csv')

        # 创建CSV文件并写入表头
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Chunk ID', 'Term'])

        # 读取和处理文档
        full_input_path = os.path.join(self.input_dir, pdf_path)
        text_content = self.doc_parser.parse_pdf(full_input_path)
        
        if text_content is None:
            print(f"无法处理文档: {pdf_path}")
            return None
        
        # 使用工具类的函数
        cleaned_text = clean_text(text_content)
        text_chunks = split_text_with_overlap(cleaned_text)

        # 并行处理文本块，传递语言数
        self.process_chunks_parallel(text_chunks, output_csv, lang)
        
        print(f"\n处理完成！结果已保存到 {output_csv}")
        return output_csv

    def load_terms(self, zh_csv: str, en_csv: str) -> Tuple[List[str], List[str]]:
        """
        加载中英文CSV文件中的术语
        
        Args:
            zh_csv: 中文术语CSV文件路径
            en_csv: 英文术语CSV文件路径
        Returns:
            Tuple[List[str], List[str]]: 中文术语列表和英文术语列表
        """
        zh_df = pd.read_csv(zh_csv)
        en_df = pd.read_csv(en_csv)
        
        # 提取术语并去重
        zh_terms = sorted(list(set(zh_df['Term'].tolist())))
        en_terms = sorted(list(set(en_df['Term'].tolist())))
        
        return zh_terms, en_terms

    def align_terms(self, zh_terms: List[str], en_terms: List[str], 
                   batch_size: int = 50) -> List[Dict[str, str]]:
        """
        使用Claude模型对齐中英文术语
        
        Args:
            zh_terms: 中文术语列表
            en_terms: 英文术语列表
            batch_size: 每批处理的术语数量
        Returns:
            List[Dict[str, str]]: 对齐后的术语字典列表
        """
        aligned_pairs = []
        
        # 将术语分批处理
        for i in range(0, len(zh_terms), batch_size):
            zh_batch = zh_terms[i:i + batch_size]
            
            prompt = f"""Please align the Chinese medical terms with their English equivalents from the provided lists. 
Return the results in XML format like this:

<alignments>
  <pair>
    <zh>呼吸机</zh>
    <en>Ventilator</en>
  </pair>
</alignments>

Only create pairs when you are highly confident about the alignment.
Skip terms that don't have a clear match.
Maintain medical accuracy in the alignments.

Chinese terms:
{', '.join(zh_batch)}

English terms:
{', '.join(en_terms)}

Start your response with <output>:"""

            system_prompt = "You are a medical terminology expert specializing in medical terminology."
            
            try:
                response_text = self.bedrock_client.call_claude(
                    prompt=prompt,
                    system_prompt=system_prompt
                )
                
                # 解析XML响应
                import re
                zh_pattern = r'<zh>(.*?)</zh>'
                en_pattern = r'<en>(.*?)</en>'
                
                zh_matches = re.findall(zh_pattern, response_text)
                en_matches = re.findall(en_pattern, response_text)
                
                # 将匹配的对添加到结果中
                for zh, en in zip(zh_matches, en_matches):
                    aligned_pairs.append({
                        'zh': zh.strip(),
                        'en': en.strip()
                    })
                
                print(f"已处理 {len(zh_batch)} 个术语")
                
            except Exception as e:
                print(f"处理批次时出错: {str(e)}")
                continue
        
        return aligned_pairs

    def process_and_align_documents(self, zh_doc: str, en_doc: str, 
                                  output_file: str = None) -> str:
        """
        处理两个文档并生成对齐的术语表
        
        Args:
            zh_doc: 中文文档路径
            en_doc: 英文文档路径
            output_file: 输出文件路径，如果为None则自动生成
        Returns:
            str: 输出文件路径
        """
        # 处理中文文档
        print("开始处理中文文档...")
        zh_csv = self.process_document(zh_doc, lang="zh")
        
        # 处理英文文档
        print("\n开始处理英文文档...")
        en_csv = self.process_document(en_doc, lang="en")
        
        # 加载术语
        print("\n开始对齐术语...")
        zh_terms, en_terms = self.load_terms(zh_csv, en_csv)
        print(f"加载了 {len(zh_terms)} 个中文术语和 {len(en_terms)} 个英文术语")
        
        # 对齐术语
        aligned_pairs = self.align_terms(zh_terms, en_terms)
        print(f"成功对齐了 {len(aligned_pairs)} 对术语")
        
        # 生成输出文件名
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.output_dir, f'aligned_glossary_{timestamp}.csv')
        
        # 保存结果
        df = pd.DataFrame(aligned_pairs)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"结果已保存到 {output_file}")
        
        return output_file

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='提取并对齐中英文术语')
    parser.add_argument('zh_doc', help='中文文档路径')
    parser.add_argument('en_doc', help='英文文档路径')
    parser.add_argument('--input-dir', default='./input', help='输入文件目录 (默认: ./input)')
    parser.add_argument('--output-dir', default='./output', help='输出文件目录 (默认: ./output)')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 创建术语提取器实例
    extractor = TermExtractor(input_dir=args.input_dir, output_dir=args.output_dir)
    
    # 处理文档并生成对齐词汇表
    extractor.process_and_align_documents(args.zh_doc, args.en_doc)

if __name__ == "__main__":
    main()

