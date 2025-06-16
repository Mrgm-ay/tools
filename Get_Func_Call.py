import re
import csv
import os

def extract_function_calls(file_path, output_csv_path="function_calls.csv"):
    """
    C言語ファイルから関数の呼び出し関係を抽出してCSVに出力する
    
    Args:
        file_path (str): C言語ソースファイルのパス
        output_csv_path (str): 出力CSVファイルのパス
    """
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        # UTF-8で読めない場合はShift-JISを試す
        try:
            with open(file_path, 'r', encoding='shift-jis') as file:
                content = file.read()
        except UnicodeDecodeError:
            print(f"エラー: ファイル {file_path} の文字エンコーディングを読み取れません")
            return
    except FileNotFoundError:
        print(f"エラー: ファイル {file_path} が見つかりません")
        return
    
    # コメントと文字列リテラルを除去
    content = remove_comments_and_strings(content)
    
    # 関数定義を抽出
    function_definitions = extract_function_definitions(content)
    
    # 各関数内の関数呼び出しを抽出
    function_calls = []
    
    for func_name, func_body in function_definitions.items():
        called_functions = extract_called_functions(func_body)
        for called_func in called_functions:
            # 自分自身の呼び出しも含める（再帰呼び出し）
            function_calls.append([func_name, called_func])
    
    # CSVファイルに出力
    try:
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['呼び出し元', '呼び出し先'])  # ヘッダー
            writer.writerows(function_calls)
        
        print(f"関数呼び出し関係を {output_csv_path} に出力しました")
        print(f"抽出された関数呼び出し数: {len(function_calls)}")
        
        # 結果の概要を表示
        if function_calls:
            print("\n抽出された関数呼び出し関係（最初の10件）:")
            for i, (caller, callee) in enumerate(function_calls[:10]):
                print(f"{i+1}. {caller} -> {callee}")
            if len(function_calls) > 10:
                print(f"... (他 {len(function_calls) - 10} 件)")
        
    except Exception as e:
        print(f"CSVファイルの書き込みエラー: {e}")

def remove_comments_and_strings(content):
    """
    C言語コードからコメントと文字列リテラルを除去
    """
    # 文字列リテラルとコメントを除去するための正規表現
    pattern = r'("(?:[^"\\]|\\.)*")|(/\*.*?\*/)|(//.*)|(\'(?:[^\'\\]|\\.)*\')'
    
    def replace_func(match):
        if match.group(2) or match.group(3):  # コメント
            return ' '
        elif match.group(1) or match.group(4):  # 文字列リテラル
            return ' '
        return match.group(0)
    
    return re.sub(pattern, replace_func, content, flags=re.DOTALL)

def extract_function_definitions(content):
    """
    C言語コードから関数定義を抽出
    戻り値: {関数名: 関数本体} の辞書
    """
    function_definitions = {}
    
    # 関数定義の正規表現パターン
    # 戻り値の型、関数名、引数、関数本体を抽出
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*\s+)*([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{'
    
    matches = list(re.finditer(pattern, content))
    
    for match in matches:
        func_name = match.group(2)
        start_pos = match.end() - 1  # '{' の位置
        
        # 対応する '}' を見つける
        brace_count = 1
        pos = start_pos + 1
        
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        
        if brace_count == 0:
            func_body = content[start_pos:pos]
            function_definitions[func_name] = func_body
    
    return function_definitions

def extract_called_functions(func_body):
    """
    関数本体から呼び出されている関数を抽出
    """
    called_functions = set()
    
    # 関数呼び出しの正規表現パターン
    # 関数名(引数) の形式
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    
    matches = re.finditer(pattern, func_body)
    
    for match in matches:
        func_name = match.group(1)
        
        # C言語のキーワードや制御構文を除外
        keywords = {
            'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
            'return', 'break', 'continue', 'goto', 'sizeof', 'typeof',
            'static_assert', '_Static_assert'
        }
        
        if func_name not in keywords:
            called_functions.add(func_name)
    
    return called_functions

def main():
    """
    メイン関数 - ここでファイルパスを指定してください
    """
    # ============================================
    # ここにC言語ソースファイルのパスを指定してください
    # ============================================
    c_file_path = "sample.c"  # 対象のC言語ファイルパス
    output_csv_path = "function_calls.csv"  # 出力CSVファイルパス
    
    print(f"C言語ファイルを解析中: {c_file_path}")
    
    if not os.path.exists(c_file_path):
        print(f"ファイルが存在しません: {c_file_path}")
        print("c_file_path変数を正しいファイルパスに変更してください")
        return
    
    extract_function_calls(c_file_path, output_csv_path)

if __name__ == "__main__":
    main()