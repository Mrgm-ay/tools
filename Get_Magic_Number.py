import re
import os
import csv
import sys
from pathlib import Path

def extract_magic_numbers(file_path):
    """
    C言語ソースファイルからマジックナンバーを抽出する
    
    Args:
        file_path (str): C言語ソースファイルのパス
    
    Returns:
        list: マジックナンバーの情報を含む辞書のリスト
    """
    magic_numbers = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        # UTF-8で読めない場合はShift_JISを試す
        try:
            with open(file_path, 'r', encoding='shift_jis') as file:
                lines = file.readlines()
        except UnicodeDecodeError:
            # それでも読めない場合はエラーを出力して空のリストを返す
            print(f"Warning: Could not read file {file_path} with UTF-8 or Shift_JIS encoding")
            return []
    
    # 数値パターンの正規表現
    # 整数: 10進数、16進数(0x, 0X)、8進数(0で始まる)、2進数(0b, 0B)
    # 浮動小数点数: 1.23, .5, 1., 1e10, 1.23e-4 など
    # サフィックス: L, LL, U, UL, ULL, f, F, l, L など
    number_patterns = [
        # 16進数 (0x, 0X)
        r'\b0[xX][0-9a-fA-F]+[uUlL]*\b',
        # 2進数 (0b, 0B) - C23またはGCC拡張
        r'\b0[bB][01]+[uUlL]*\b',
        # 8進数 (0で始まる)
        r'\b0[0-7]+[uUlL]*\b',
        # 浮動小数点数（指数表記あり）
        r'\b\d+\.?\d*[eE][+-]?\d+[fFlL]?\b',
        r'\b\.\d+[eE][+-]?\d+[fFlL]?\b',
        # 浮動小数点数（指数表記なし）
        r'\b\d+\.\d+[fFlL]?\b',
        r'\b\d+\.[fFlL]?\b',
        r'\b\.\d+[fFlL]?\b',
        # 10進数（整数）
        r'\b[1-9]\d*[uUlL]*\b',
        # 0単体
        r'\b0[uUlL]*\b'
    ]
    
    # コメントと文字列リテラル内の数値は除外するためのパターン
    comment_string_pattern = re.compile(
        r'//.*?$|'           # 行コメント
        r'/\*.*?\*/|'        # ブロックコメント
        r'"(?:[^"\\]|\\.)*"|'  # 文字列リテラル
        r"'(?:[^'\\]|\\.)*'",  # 文字リテラル
        re.MULTILINE | re.DOTALL
    )
    
    for line_num, line in enumerate(lines, 1):
        # コメントと文字列を除外したラインを作成
        clean_line = line
        for match in comment_string_pattern.finditer(line):
            # マッチした部分を同じ長さの空白で置換（行位置を保持）
            clean_line = clean_line[:match.start()] + ' ' * (match.end() - match.start()) + clean_line[match.end():]
        
        # 各数値パターンをチェック
        for pattern in number_patterns:
            for match in re.finditer(pattern, clean_line):
                number = match.group()
                column = match.start() + 1  # 1から始まる列番号
                
                # 前後の文字をチェックして識別子の一部でないことを確認
                start_pos = match.start()
                end_pos = match.end()
                
                # 前の文字が英数字またはアンダースコアでないことを確認
                if start_pos > 0 and clean_line[start_pos - 1].isalnum() or (start_pos > 0 and clean_line[start_pos - 1] == '_'):
                    continue
                
                # 後の文字が英数字またはアンダースコアでないことを確認
                if end_pos < len(clean_line) and (clean_line[end_pos].isalnum() or clean_line[end_pos] == '_'):
                    continue
                
                magic_numbers.append({
                    'line': line_num,
                    'column': column,
                    'number': number,
                    'context': line.strip()
                })
    
    return magic_numbers

def create_output_directory(relative_path):
    """
    出力ディレクトリを作成する
    
    Args:
        relative_path (str): 入力ファイルの相対パス
    
    Returns:
        str: 出力ディレクトリのパス
    """
    # スクリプトと同じディレクトリにresult_magic_numberフォルダを作成
    script_dir = Path(__file__).parent
    result_dir = script_dir / "result_magic_number"
    
    # 入力ファイルの相対パスからディレクトリ部分を取得
    input_path = Path(relative_path)
    if input_path.parent != Path('.'):
        # 相対パスにディレクトリが含まれている場合
        output_dir = result_dir / input_path.parent
    else:
        # ファイルがカレントディレクトリにある場合
        output_dir = result_dir
    
    # ディレクトリを作成
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return output_dir

def save_to_csv(magic_numbers, output_path):
    """
    マジックナンバーをCSVファイルに保存する
    
    Args:
        magic_numbers (list): マジックナンバーのリスト
        output_path (str): 出力ファイルのパス
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['line', 'column', 'number', 'context']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for item in magic_numbers:
            writer.writerow(item)

def main():
    """
    メイン関数
    """
    if len(sys.argv) != 2:
        print("Usage: python magic_number_extractor.py <relative_path_to_c_file>")
        sys.exit(1)
    
    relative_path = sys.argv[1]
    
    # ファイルの存在確認
    if not os.path.exists(relative_path):
        print(f"Error: File '{relative_path}' does not exist.")
        sys.exit(1)
    
    # C言語ファイルかどうかの確認
    if not relative_path.lower().endswith(('.c', '.h', '.cpp', '.hpp', '.cc', '.cxx')):
        print(f"Warning: '{relative_path}' may not be a C/C++ source file.")
    
    print(f"Analyzing file: {relative_path}")
    
    # マジックナンバーを抽出
    magic_numbers = extract_magic_numbers(relative_path)
    
    if not magic_numbers:
        print("No magic numbers found.")
        return
    
    # 出力ディレクトリを作成
    output_dir = create_output_directory(relative_path)
    
    # 出力ファイル名を生成
    input_filename = Path(relative_path).stem  # 拡張子を除いたファイル名
    output_filename = f"{input_filename}_magic_number.csv"
    output_path = output_dir / output_filename
    
    # CSVファイルに保存
    save_to_csv(magic_numbers, output_path)
    
    print(f"Found {len(magic_numbers)} magic numbers.")
    print(f"Results saved to: {output_path}")
    
    # 結果の一部を表示
    print("\nFirst 5 magic numbers found:")
    for i, item in enumerate(magic_numbers[:5]):
        print(f"  Line {item['line']}, Column {item['column']}: {item['number']}")
        print(f"    Context: {item['context']}")

if __name__ == "__main__":
    main()