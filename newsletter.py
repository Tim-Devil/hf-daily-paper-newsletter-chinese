import os
import json
from datetime import datetime
import markdown
from jinja2 import Template
from utils import get_logger
import re
import argparse

logger = get_logger()

class NewsletterGenerator:
    def __init__(self):
        self.template = """
# <img src="https://huggingface.co/datasets/huggingface/brand-assets/resolve/main/hf-logo.png" width="30"/> Hugging Face {{ date }} 论文日报

## 📊 今日论文统计
- 总论文数：{{ total_papers }}
- 热门领域：{{ hot_topics }}

## 📝 论文详情

{% for paper in papers %}
### {{ loop.index }}. {{ paper.title }}

**原文标题：** {{ paper.original_title }}

**摘要：**
{{ paper.summary }}

**论文链接：** [HuggingFace]({{ paper.paper_url }}) | [arXiv]({{ paper.arxiv_url }})

{% if paper.code_url %}
**代码链接：** [GitHub]({{ paper.code_url }})
{% endif %}

---
{% endfor %}

## 🔍 关键词云图
![关键词云图](../images/keywords_wordcloud.png)

## 📈 近期论文趋势
![论文趋势](../images/daily_papers.png)

## 🎙️ 语音播报
- [收听今日论文解读](../{{ audio_path }})

## 📱 订阅渠道
- GitHub: [hf-daily-paper-newsletter-chinese](https://github.com/2404589803/hf-daily-paper-newsletter-chinese)
"""
        
        # HTML模板,包含响应式CSS样式
        self.html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hugging Face 论文日报 - {{ date }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
            font-size: 28px;
        }
        
        h1 img {
            vertical-align: middle;
            margin-right: 10px;
        }
        
        h2 {
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 24px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        
        h3 {
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 20px;
        }
        
        p {
            margin-bottom: 15px;
            text-align: justify;
        }
        
        ul {
            margin-left: 20px;
            margin-bottom: 20px;
        }
        
        li {
            margin-bottom: 8px;
        }
        
        a {
            color: #3498db;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        strong {
            color: #2c3e50;
            font-weight: 600;
        }
        
        hr {
            border: none;
            border-top: 1px solid #e0e0e0;
            margin: 30px 0;
        }
        
        /* 关键修复:限制图片宽度 */
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* 确保图片容器也有宽度限制 */
        p img {
            max-width: 100%;
        }
        
        /* 论文详情区域样式 */
        .paper-section {
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        
        /* 统计信息样式 */
        .stats {
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            
            h1 {
                font-size: 24px;
            }
            
            h2 {
                font-size: 20px;
            }
            
            h3 {
                font-size: 18px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        {{ content }}
    </div>
</body>
</html>
"""

    def extract_paper_info(self, paper_data):
        """从论文数据中提取关键信息"""
        translation = paper_data.get('translation', '')
        
        # 使用更严格的正则表达式提取标题和摘要
        title_match = re.search(r"标题[:：]\s*([^\n]+)(?=\s*\n\s*摘要[:：]|\Z)", translation, re.DOTALL)
        summary_match = re.search(r"摘要[:：]\s*([^\n].+?)(?=\s*(?:\n\s*[^：\n]+[:：]|\Z))", translation, re.DOTALL)
        
        # 如果匹配失败,尝试使用备用模式
        if not title_match:
            title_match = re.search(r"^([^\n]+)\n\s*摘要[:：]", translation, re.MULTILINE)
        
        title = (title_match.group(1) if title_match else paper_data.get('title', '')).strip()
        summary = (summary_match.group(1) if summary_match else '').strip()
        
        # 如果摘要为空,尝试获取剩余的所有文本作为摘要
        if not summary and '摘要：' in translation:
            summary = translation.split('摘要：', 1)[1].strip()
        
        return {
            'title': title,
            'original_title': paper_data.get('title', ''),
            'summary': summary,
            'paper_url': paper_data.get('url', ''),
            'arxiv_url': paper_data.get('arxiv_url', ''),
            'code_url': paper_data.get('paper', {}).get('code', '')
        }

    def get_hot_topics(self, papers):
        """分析热门研究领域"""
        topics = []
        keywords = ['LLM', 'Vision', 'Audio', 'MultiModal', 'NLP', 'RL', 
                   'Transformer', 'GPT', 'AIGC', 'Diffusion']
        for paper in papers:
            title = paper.get('title', '').lower()
            summary = paper.get('summary', '').lower()
            content = title + ' ' + summary
            for keyword in keywords:
                if keyword.lower() in content and keyword not in topics:
                    topics.append(keyword)
        return ', '.join(topics) if topics else '综合领域'

    def generate_html(self, markdown_content, date_str):
        """将Markdown转换为带样式的HTML"""
        # 先将markdown转换为HTML
        html_content = markdown.markdown(markdown_content)
        
        # 使用HTML模板包装内容
        template = Template(self.html_template)
        full_html = template.render(content=html_content, date=date_str)
        
        return full_html

    def generate_newsletter(self, date_str=None):
        """生成每日论文简报"""
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
            
        try:
            # 读取论文数据
            json_file = os.path.join('HF-day-paper-deepseek', f"{date_str}_HF_deepseek_clean.json")
            if not os.path.exists(json_file):
                logger.error(f"未找到{date_str}的论文数据文件")
                return False
                
            with open(json_file, 'r', encoding='utf-8') as f:
                papers_data = json.load(f)
                
            # 检查是否有有效数据
            if not isinstance(papers_data, list) or len(papers_data) == 0:
                logger.info(f"{date_str} 没有论文数据,跳过生成日报")
                return False
                
            # 处理论文信息
            papers = [self.extract_paper_info(paper) for paper in papers_data]
            if not papers:
                logger.warning("没有提取到有效的论文信息")
                return False
                
            # 检查是否存在统计数据
            stats_file = os.path.join('stats', 'stats_report.json')
            if not os.path.exists(stats_file):
                logger.warning("未找到统计数据文件,将使用简化版模板")
                template_data = {
                    'date': date_str,
                    'total_papers': len(papers),
                    'hot_topics': self.get_hot_topics(papers),
                    'papers': papers,
                    'wordcloud_path': None,
                    'trend_path': None,
                    'audio_path': f'audio/{date_str}_daily_papers.mp3'
                }
            else:
                # 准备模板数据
                template_data = {
                    'date': date_str,
                    'total_papers': len(papers),
                    'hot_topics': self.get_hot_topics(papers),
                    'papers': papers,
                    'wordcloud_path': f'images/keywords_wordcloud.png',
                    'trend_path': f'images/daily_papers.png',
                    'audio_path': f'audio/{date_str}_daily_papers.mp3'
                }
            
            # 渲染模板
            template = Template(self.template)
            newsletter_md = template.render(**template_data)
            
            # 转换为HTML并添加样式
            newsletter_html = self.generate_html(newsletter_md, date_str)
            
            # 保存文件
            output_dir = 'newsletters'  # 日报保存在 newsletters 目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存Markdown版本
            md_path = os.path.join(output_dir, f"{date_str}_daily_paper.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(newsletter_md)
                
            # 保存HTML版本
            html_path = os.path.join(output_dir, f"{date_str}_daily_paper.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(newsletter_html)
                
            logger.info(f"日报已生成：{md_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成日报时出错：{str(e)}")
            return False

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='生成HuggingFace每日论文简报')
    parser.add_argument('--date', type=str, help='指定要生成的日期 (YYYY-MM-DD格式)')
    args = parser.parse_args()

    # 使用指定的日期或默认使用当前日期
    generator = NewsletterGenerator()
    success = generator.generate_newsletter(args.date)
    if not success:
        exit(1)
    exit(0)
