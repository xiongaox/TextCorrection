# 用途
# 替换文本中的错别字；去除多余符号；删除空行
# 支持格式: LRC, TXT, SRT, ASS 等文本文件

import os
import re
import logging
import json
from datetime import datetime

# 配置日志
def setup_logger():
    # 创建logs目录（如果不存在）
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 设置日志文件名（使用当前时间）
    log_filename = f"logs/lrc_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 配置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger()

def load_replacements():
    """从外部JSON文件加载替换字典"""
    json_file = 'replacements.json'
    
    if not os.path.exists(json_file):
        print(f"错误: 找不到配置文件 {json_file}")
        print("请确保 replacements.json 文件存在于程序目录中")
        return None
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 合并所有分类的替换规则
        replacements = {}
        for key, value in data.items():
            if key.startswith('_'):  # 跳过注释字段
                continue
            if isinstance(value, dict):  # 如果是分组格式
                replacements.update(value)
            else:  # 如果是旧的平铺格式，直接添加
                replacements[key] = value
        
        print(f"成功加载 {len(replacements)} 个替换规则")
        
        # 按分类显示加载的规则数量
        for category, rules in data.items():
            if not category.startswith('_') and isinstance(rules, dict):
                print(f"  - {category}: {len(rules)} 个规则")
        
        return replacements
    except json.JSONDecodeError as e:
        print(f"JSON文件格式错误: {e}")
        return None
    except Exception as e:
        print(f"加载JSON文件失败: {e}")
        return None

# 支持的文件格式配置
SUPPORTED_EXTENSIONS = {
    '.lrc': 'LRC歌词文件',
    '.txt': '纯文本文件', 
    '.srt': 'SRT字幕文件',
    '.ass': 'ASS字幕文件',
    '.ssa': 'SSA字幕文件',
    '.vtt': 'WebVTT字幕文件'
}

# 时间戳的正则表达式模式
TIMESTAMP_PATTERNS = {
    'lrc': re.compile(r'^(\[\d{2}:\d{2}(.\d{2})?\])(.*)$'),
    'srt': re.compile(r'^(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})$'),
    'vtt': re.compile(r'^(\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3})$'),
    'ass': re.compile(r'^(Dialogue: .+?,)(.*)$')
}

def detect_file_type(file_path):
    """检测文件类型"""
    _, ext = os.path.splitext(file_path.lower())
    return ext

def process_lrc_content(line, replacements, replacement_counts, empty_line_count):
    """处理LRC格式内容"""
    original_line = line.strip()
    if not original_line:
        return None, False
    
    # 提取时间戳和歌词内容
    timestamp_match = TIMESTAMP_PATTERNS['lrc'].match(original_line)
    
    if timestamp_match:
        timestamp = timestamp_match.group(1)
        lyrics = timestamp_match.group(3).strip()
        
        # 应用替换规则
        modified = False
        for old_text, new_text in replacements.items():
            if old_text in lyrics:
                count = lyrics.count(old_text)
                replacement_counts[old_text] = replacement_counts.get(old_text, 0) + count
                lyrics = lyrics.replace(old_text, new_text)
                modified = True
        
        # 如果替换后歌词为空，则跳过这一行
        if not lyrics:
            empty_line_count[0] += 1
            return None, True
        
        return f"{timestamp}{lyrics}\n", modified
    else:
        # 保留不包含时间戳的行（如歌曲信息行）
        return original_line + '\n', False

def process_srt_content(lines, replacements, replacement_counts, empty_line_count):
    """处理SRT格式内容"""
    processed_lines = []
    modified = False
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            i += 1
            continue
        
        # 字幕序号
        if line.isdigit():
            processed_lines.append(line + '\n')
            i += 1
            continue
        
        # 时间戳行
        if TIMESTAMP_PATTERNS['srt'].match(line):
            processed_lines.append(line + '\n')
            i += 1
            continue
        
        # 字幕内容行
        subtitle_text = line
        for old_text, new_text in replacements.items():
            if old_text in subtitle_text:
                count = subtitle_text.count(old_text)
                replacement_counts[old_text] = replacement_counts.get(old_text, 0) + count
                subtitle_text = subtitle_text.replace(old_text, new_text)
                modified = True
        
        if subtitle_text.strip():
            processed_lines.append(subtitle_text + '\n')
        else:
            empty_line_count[0] += 1
            modified = True
        
        i += 1
    
    return processed_lines, modified

def process_ass_content(lines, replacements, replacement_counts, empty_line_count):
    """处理ASS/SSA格式内容"""
    processed_lines = []
    modified = False
    
    for line in lines:
        original_line = line.strip()
        
        if not original_line:
            continue
        
        # 检查是否是对话行
        dialogue_match = TIMESTAMP_PATTERNS['ass'].match(original_line)
        
        if dialogue_match:
            dialogue_prefix = dialogue_match.group(1)
            dialogue_text = dialogue_match.group(2)
            
            # 应用替换规则到对话内容
            for old_text, new_text in replacements.items():
                if old_text in dialogue_text:
                    count = dialogue_text.count(old_text)
                    replacement_counts[old_text] = replacement_counts.get(old_text, 0) + count
                    dialogue_text = dialogue_text.replace(old_text, new_text)
                    modified = True
            
            if dialogue_text.strip():
                processed_lines.append(f"{dialogue_prefix}{dialogue_text}\n")
            else:
                empty_line_count[0] += 1
                modified = True
        else:
            # 保留非对话行（样式定义等）
            processed_lines.append(original_line + '\n')
    
    return processed_lines, modified

def process_txt_content(lines, replacements, replacement_counts, empty_line_count):
    """处理纯文本内容"""
    processed_lines = []
    modified = False
    
    for line in lines:
        original_line = line.rstrip('\n\r')
        
        if not original_line.strip():
            continue
        
        # 应用替换规则
        processed_text = original_line
        for old_text, new_text in replacements.items():
            if old_text in processed_text:
                count = processed_text.count(old_text)
                replacement_counts[old_text] = replacement_counts.get(old_text, 0) + count
                processed_text = processed_text.replace(old_text, new_text)
                modified = True
        
        if processed_text.strip():
            processed_lines.append(processed_text + '\n')
        else:
            empty_line_count[0] += 1
            modified = True
    
    return processed_lines, modified

def process_text_file(file_path, replacements, replacement_counts, empty_line_count):
    """
    处理单个文本文件
    
    参数:
    file_path: 文件路径
    replacements: 替换字典
    replacement_counts: 记录每个替换词被使用的次数
    empty_line_count: 记录删除的空行数

    返回:
    bool: 文件是否被修改
    """
    try:
        # 检测文件类型
        file_type = detect_file_type(file_path)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        processed_lines = []
        modified = False
        
        # 根据文件类型选择处理方法
        if file_type == '.lrc':
            for line in lines:
                processed_line, line_modified = process_lrc_content(line, replacements, replacement_counts, empty_line_count)
                if processed_line is not None:
                    processed_lines.append(processed_line)
                if line_modified:
                    modified = True
                    
        elif file_type == '.srt':
            processed_lines, modified = process_srt_content(lines, replacements, replacement_counts, empty_line_count)
            
        elif file_type in ['.ass', '.ssa']:
            processed_lines, modified = process_ass_content(lines, replacements, replacement_counts, empty_line_count)
            
        elif file_type in ['.txt', '.vtt']:
            processed_lines, modified = process_txt_content(lines, replacements, replacement_counts, empty_line_count)
            
        else:
            # 对于其他格式，按纯文本处理
            processed_lines, modified = process_txt_content(lines, replacements, replacement_counts, empty_line_count)
        
        # 如果文件被修改，则写回文件
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(processed_lines)
            return True
        return False
            
    except Exception as e:
        return False

def process_directory(directory_path, logger):
    """处理指定目录下的所有支持格式的文本文件（包括子目录）"""
    
    # 加载替换字典
    replacements = load_replacements()
    if replacements is None:
        logger.error("无法加载替换字典，程序退出")
        return
    
    logger.info(f"加载了 {len(replacements)} 个替换规则")
    
    # 统计计数器
    stats = {
        'total_files': 0,
        'modified_files': 0,
        'error_files': 0,
        'file_types': {}
    }
    
    # 替换词计数器
    replacement_counts = {}
    
    # 空行计数器 (使用列表以便能在函数间修改)
    empty_line_count = [0]
    
    logger.info(f"开始处理目录: {directory_path}")
    logger.info(f"支持的文件格式: {', '.join(SUPPORTED_EXTENSIONS.keys())}")
    
    # 遍历目录及其子目录
    for root, _, files in os.walk(directory_path):
        for file in files:
            file_ext = os.path.splitext(file.lower())[1]
            
            # 检查是否为支持的文件格式
            if file_ext in SUPPORTED_EXTENSIONS:
                stats['total_files'] += 1
                stats['file_types'][file_ext] = stats['file_types'].get(file_ext, 0) + 1
                
                file_path = os.path.join(root, file)
                
                try:
                    if process_text_file(file_path, replacements, replacement_counts, empty_line_count):
                        stats['modified_files'] += 1
                        logger.info(f"已处理: {file_path}")
                except Exception as e:
                    stats['error_files'] += 1
                    logger.error(f"处理文件出错 {file_path}: {str(e)}")
    
    # 输出文件类型统计
    logger.info("文件类型统计:")
    for file_ext, count in stats['file_types'].items():
        logger.info(f"  {file_ext} ({SUPPORTED_EXTENSIONS[file_ext]}): {count} 个文件")
    
    # 输出替换词统计信息
    if replacement_counts:
        logger.info("替换词使用统计:")
        for word, count in sorted(replacement_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                logger.info(f"  '{word}' 被替换了 {count} 次")
    
    # 只有在有空行被删除时才输出
    if empty_line_count[0] > 0:
        logger.info(f"共删除 {empty_line_count[0]} 行空内容行")
    
    # 输出文件处理统计信息
    logger.info(f"处理完成! 总计: {stats['total_files']} 文件, "
                f"修改: {stats['modified_files']} 文件, "
                f"处理出错: {stats['error_files']} 文件")

def main():
    # 设置日志
    logger = setup_logger()
    logger.info("多格式文本处理程序启动")
    
    # 直接使用当前工作目录
    directory = os.getcwd()
    logger.info(f"将处理当前目录: {directory}")
    
    # 显示支持的文件格式
    logger.info("支持的文件格式:")
    for ext, desc in SUPPORTED_EXTENSIONS.items():
        logger.info(f"  {ext} - {desc}")
    
    # 处理目录
    process_directory(directory, logger)
    
    # 处理完成后暂停，让用户查看结果
    input("处理完成，按Enter键退出...")

if __name__ == "__main__":
    main()