import os
import re

def format_srt_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在每个序号行前添加空行
    formatted_content = re.sub(r'(\n\d+\n)', r'\n\1', content)
    
    # 确保文件末尾有一个空行
    if not formatted_content.endswith('\n\n'):
        formatted_content += '\n'
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(formatted_content)

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.srt'):
                file_path = os.path.join(root, file)
                format_srt_file(file_path)
                print(f"已处理文件: {file_path}")

if __name__ == '__main__':
    # 直接使用当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    process_directory(current_dir)
    print("所有SRT文件处理完成！")