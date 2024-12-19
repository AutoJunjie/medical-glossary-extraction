import boto3
from typing import List
from botocore.config import Config

class BedrockClient:
    def __init__(self, region_name='us-west-2'):
        """
        初始化 Bedrock 客户端
        
        Args:
            region_name: AWS 区域名称
        """
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region_name,
            config=Config(
                retries = dict(
                    max_attempts = 3
                )
            )
        )
    
    def call_claude(self, prompt: str, system_prompt: str = None, 
                   max_tokens: int = 4096, temperature: float = 0,
                   stop_sequences: List[str] = None) -> str:
        """
        调用 Claude 模型的通用方法
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            max_tokens: 最大token数
            temperature: 温度参数
            stop_sequences: 停止序列
        Returns:
            str: 模型响应文本
        """
        system_prompts = [{"text": system_prompt}] if system_prompt else []
        
        message = [
            {
                "role": "user", 
                "content": [{"text": prompt}]
            },
            {
                "role": "assistant", 
                "content": [{"text": "Sure, I'll help. Here's the result: <output>"}]
            }
        ]
        
        try:
            response = self.client.converse(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                messages=message,
                system=system_prompts,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "stopSequences": stop_sequences or ['</output>']
                }
            )
            
            return response['output']['message']['content'][0]['text']
            
        except Exception as e:
            print(f"调用模型时出错: {str(e)}")
            return "" 