import re
from pathlib import Path

def extract_tables_from_file(file_path):
    """
    指定されたパスのC/Hファイルからテーブル宣言を抽出し、result_tableフォルダに出力
    
    Args:
        file_path: 処理対象ファイルの相対パス (Path オブジェクトまたは文字列)
    """
    # Pathオブジェクトに変換
    input_path = Path(file_path) if isinstance(file_path, str) else file_path
    
    # 入力ファイルが存在しない場合はエラー
    if not input_path.exists():
        print(f"エラー: ファイルが存在しません - {input_path}")
        return
    
    # 出力先ディレクトリを作成
    script_dir = Path(__file__).parent
    table_output_dir = script_dir / "result_table"
    
    # 相対パスの構造を保持した出力パスを作成
    table_output_path = table_output_dir / input_path
    
    # 出力ディレクトリを作成（存在しない場合）
    table_output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # ファイルを読み込み
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # テーブル宣言を抽出
        table_declarations = extract_tables(content)
        
        # テーブル宣言を出力
        with open(table_output_path, 'w', encoding='utf-8') as f:
            f.write(f"// Table declarations extracted from {input_path}\n")
            f.write("// " + "="*60 + "\n\n")
            if table_declarations:
                for i, table in enumerate(table_declarations, 1):
                    f.write(f"// Table {i}\n")
                    f.write(table + "\n\n")
            else:
                f.write("// No table declarations found\n")
        
        print(f"処理完了: {input_path}")
        print(f"  テーブル宣言: {len(table_declarations)}個 -> {table_output_path}")
        
    except UnicodeDecodeError:
        # UTF-8で読み込めない場合はcp932で試行
        try:
            with open(input_path, 'r', encoding='cp932') as f:
                content = f.read()
            
            table_declarations = extract_tables(content)
            
            with open(table_output_path, 'w', encoding='utf-8') as f:
                f.write(f"// Table declarations extracted from {input_path}\n")
                f.write("// " + "="*60 + "\n\n")
                if table_declarations:
                    for i, table in enumerate(table_declarations, 1):
                        f.write(f"// Table {i}\n")
                        f.write(table + "\n\n")
                else:
                    f.write("// No table declarations found\n")
            
            print(f"処理完了 (cp932): {input_path}")
            print(f"  テーブル宣言: {len(table_declarations)}個 -> {table_output_path}")
            
        except Exception as e:
            print(f"エラー: ファイルの読み込みに失敗しました - {input_path}: {e}")
    
    except Exception as e:
        print(f"エラー: ファイルの処理に失敗しました - {input_path}: {e}")

def extract_tables(code):
    """
    C/C++のソースコードからテーブル宣言を抽出する
    
    Args:
        code: C/C++のソースコード文字列
    
    Returns:
        list: テーブル宣言のリスト
    """
    # コメントを除去（文字列リテラルは保護）
    code_without_comments = remove_c_comments_for_parsing(code)
    
    # テーブル宣言のパターンを検索
    table_declarations = []
    
    # 1. 配列の初期化を伴う宣言を検索
    # 例: int table[] = {1, 2, 3};
    #     const char* names[] = {"apple", "banana"};
    array_patterns = [
        # 基本的な配列宣言
        r'(?:(?:static|const|extern)\s+)*(?:unsigned\s+)?(?:char|short|int|long|float|double|void\s*\*|\w+_t|\w+)\s*\*?\s+\w+\s*\[\s*(?:\d+)?\s*\]\s*=\s*\{[^}]*\}\s*;',
        # 構造体配列
        r'(?:(?:static|const|extern)\s+)*(?:struct\s+\w+|\w+)\s+\w+\s*\[\s*(?:\d+)?\s*\]\s*=\s*\{[^}]*\}\s*;',
        # 多次元配列
        r'(?:(?:static|const|extern)\s+)*(?:unsigned\s+)?(?:char|short|int|long|float|double|\w+_t|\w+)\s+\w+\s*\[\s*\d*\s*\]\s*\[\s*\d*\s*\]\s*=\s*\{[^}]*\}\s*;',
        # ポインタ配列
        r'(?:(?:static|const|extern)\s+)*(?:char|void|\w+)\s*\*\s*\w+\s*\[\s*(?:\d+)?\s*\]\s*=\s*\{[^}]*\}\s*;'
    ]
    
    # より確実な方法：ブレース対応を考慮した抽出
    tables = find_table_declarations(code_without_comments)
    
    return tables

def find_table_declarations(code):
    """
    ブレースのネストを考慮してテーブル宣言を抽出
    """
    tables = []
    lines = code.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 配列宣言の開始を検出
        if is_table_declaration_start(line):
            # 宣言の開始位置を記録
            table_start = i
            table_lines = [lines[i]]
            
            # ブレースが開いているかチェック
            if '{' in line:
                brace_count = line.count('{') - line.count('}')
                i += 1
                
                # ブレースが閉じるまで行を収集
                while i < len(lines) and brace_count > 0:
                    current_line = lines[i]
                    table_lines.append(current_line)
                    brace_count += current_line.count('{') - current_line.count('}')
                    i += 1
                
                # セミコロンまで収集（ブレースが閉じた後）
                if i < len(lines) and brace_count == 0:
                    last_line = table_lines[-1].strip()
                    if not last_line.endswith(';'):
                        while i < len(lines):
                            current_line = lines[i].strip()
                            table_lines.append(lines[i])
                            if current_line.endswith(';'):
                                i += 1
                                break
                            i += 1
                
                # テーブル宣言として追加
                table_declaration = '\n'.join(table_lines)
                if is_valid_table_declaration(table_declaration):
                    tables.append(table_declaration.strip())
            else:
                # 単一行の配列宣言
                if ';' in line and is_valid_table_declaration(line):
                    tables.append(line)
        
        i += 1
    
    return tables

def is_table_declaration_start(line):
    """
    行がテーブル宣言の開始かどうかを判定
    """
    # 基本的な配列宣言パターン
    patterns = [
        r'^\s*(?:static\s+|const\s+|extern\s+)*(?:unsigned\s+)?(?:char|short|int|long|float|double|void\s*\*|\w+_t|\w+)\s*\*?\s+\w+\s*\[',
        r'^\s*(?:static\s+|const\s+|extern\s+)*struct\s+\w+\s+\w+\s*\[',
        r'^\s*(?:static\s+|const\s+|extern\s+)*\w+\s+\w+\s*\[.*\]\s*=',
    ]
    
    for pattern in patterns:
        if re.search(pattern, line):
            # 関数宣言ではないことを確認
            if not re.search(r'\w+\s*\([^)]*\)\s*(?:\{|;)', line):
                return True
    
    return False

def is_valid_table_declaration(declaration):
    """
    有効なテーブル宣言かどうかをチェック
    """
    # 基本的なチェック
    if not declaration.strip():
        return False
    
    # 配列ブラケットと初期化ブレースがあるかチェック
    has_array_bracket = '[' in declaration and ']' in declaration
    has_initialization = '=' in declaration and ('{' in declaration or '"' in declaration or "'" in declaration)
    
    # 関数宣言ではないことを確認
    is_function = re.search(r'\w+\s*\([^)]*\)\s*\{', declaration)
    
    # typedef宣言ではないことを確認
    is_typedef = declaration.strip().startswith('typedef')
    
    return has_array_bracket and has_initialization and not is_function and not is_typedef

def remove_c_comments_for_parsing(code):
    """
    パース用のコメント除去（簡易版）
    """
    # 文字列リテラルとコメントを処理
    pattern = r'''
        (                           # グループ1: 文字列リテラル
            "(?:[^"\\]|\\.)*"       # ダブルクォート文字列
            |                       # または
            '(?:[^'\\]|\\.)*'       # シングルクォート文字列
        )
        |                           # または
        (                           # グループ2: コメント
            //.*?$                  # 行コメント
            |                       # または
            /\*.*?\*/               # ブロックコメント
        )
    '''
    
    def replace_comment(match):
        if match.group(1):
            return match.group(1)
        else:
            comment = match.group(2)
            if comment.startswith('/*'):
                return '\n' * comment.count('\n')
            else:
                return ''
    
    return re.sub(pattern, replace_comment, code, flags=re.MULTILINE | re.DOTALL | re.VERBOSE)

# 使用例とテスト用のコード
if __name__ == "__main__":
    from pathlib import Path
    
    def get_all_files():
        """実行ファイルのフォルダ配下にある全てのファイルの相対パスを取得"""
        script_dir = Path(__file__).parent
        return [file.relative_to(script_dir) for file in script_dir.rglob('*') if file.is_file()]
    
    def filter_c_h_files(file_paths):
        """パスのリストから.cと.hファイルのみを抽出"""
        return [file_path for file_path in file_paths 
                if Path(file_path).suffix.lower() in ['.c', '.h']]
    
    # 全ファイルを取得
    all_files = get_all_files()
    
    # .cと.hファイルのみを抽出
    c_h_files = filter_c_h_files(all_files)
    
    print("=== C/Hファイル一覧 ===")
    for file_path in c_h_files:
        print(file_path)
    
    # 各ファイルからテーブル宣言を抽出
    print("\n=== テーブル抽出処理 ===")
    for file_path in c_h_files:
        extract_tables_from_file(file_path)
    
    # テスト用のサンプルコード
    sample_code = '''
    // Sample C file with table declarations
    
    // Simple integer array
    int numbers[] = {1, 2, 3, 4, 5};
    
    // Constant string array
    const char* fruits[] = {
        "apple",
        "banana", 
        "orange"
    };
    
    // Static character array
    static char buffer[256] = {0};
    
    // Structure array
    struct Point {
        int x, y;
    };
    
    struct Point points[] = {
        {0, 0},
        {10, 20},
        {30, 40}
    };
    
    // Multi-dimensional array
    int matrix[3][3] = {
        {1, 2, 3},
        {4, 5, 6},
        {7, 8, 9}
    };
    
    // Function pointer array
    int (*operations[])(int, int) = {
        add_func,
        sub_func,
        mul_func
    };
    
    // Not a table - function declaration
    int process_data(int data[], int size);
    
    // Not a table - variable declaration
    int single_var = 10;
    '''
    
    print("\n=== サンプルコードのテスト ===")
    tables = extract_tables(sample_code)
    
    print(f"テーブル宣言 ({len(tables)}個):")
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {repr(table)}")
        print(f"     {table}")
        print()