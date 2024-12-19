 # 医学术语提取与对齐工具

这个工具用于从中英文医学文档中提取专业术语，并自动对齐中英文术语对。

## 功能特点

- 支持PDF文档处理
- 自动提取医学专业术语
- 中英文术语智能对齐
- 并行处理提高效率
- 支持自定义输入输出目录

## 安装

1. 克隆仓库：
   ```
   git clone [repository URL]
   ```
2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```
3. 设置AWS凭证以访问Bedrock服务

## 使用方法

基本用法：
```bash
python extract_terms.py <zh_doc> <en_doc>
```

例如：
```bash
python extract_terms.py manual-zh.pdf manual-en.pdf
```

### 命令行参数

必需参数：
- `zh_doc`: 中文文档路径
- `en_doc`: 英文文档路径

可选参数：
- `--input-dir`: 输入文件目录（默认: ./input）
- `--output-dir`: 输出文件目录（默认: ./output）

完整示例：
```bash
python extract_terms.py manual-zh.pdf manual-en.pdf \
    --input-dir /path/to/input \
    --output-dir /path/to/output
```

## 输出文件

程序会在输出目录中生成以下文件：
1. `technical_terms_<timestamp>.csv`: 从各文档中提取的术语
2. `aligned_glossary_<timestamp>.csv`: 对齐后的中英文术语对

## 项目结构

```
.
├── input/                  # 输入文件目录
├── output/                 # 输出文件目录
├── utils/                  # 工具模块
│   ├── bedrock.py         # AWS Bedrock 客户端
│   ├── parser.py          # 文档解析工具
│   └── splitter.py        # 文本分割工具
├── requirements.txt        # 项目依赖
└── extract_terms.py        # 主程序
```

## 注意事项

- 确保输入文件放在正确的输入目录中
- 需要有效的AWS凭证配置
- 建议使用虚拟环境运行程序