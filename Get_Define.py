import re
from pathlib import Path

def extract_defines_from_file(file_path):
    """
    指定されたパスのC/Hファイルからdefine定義とdefineマクロを抽出し、それぞれ別のフォルダに出力
    
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
    define_output_dir = script_dir / "result_define"
    macro_output_dir = script_dir / "result_define_macro"
    
    # 相対パスの構造を保持した出力パスを作成
    define_output_path = define_output_dir / input_path
    macro_output_path = macro_output_dir / input_path
    
    # 出力ディレクトリを作成（存在しない場合）
    define_output_path.parent.mkdir(parents=True, exist_ok=True)
    macro_output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # ファイルを読み込み
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # define定義とマクロを抽出
        define_definitions, define_macros = extract_defines(content)
        
        # define定義を出力
        with open(define_output_path, 'w', encoding='utf-8') as f:
            f.write(f"// Define definitions extracted from {input_path}\n")
            f.write("// " + "="*60 + "\n\n")
            if define_definitions:
                for define in define_definitions:
                    f.write(define + "\n")
            else:
                f.write("// No define definitions found\n")
        
        # defineマクロを出力
        with open(macro_output_path, 'w', encoding='utf-8') as f:
            f.write(f"// Define macros extracted from {input_path}\n")
            f.write("// " + "="*60 + "\n\n")
            if define_macros:
                for macro in define_macros:
                    f.write(macro + "\n")
            else:
                f.write("// No define macros found\n")
        
        print(f"処理完了: {input_path}")
        print(f"  Define定義: {len(define_definitions)}個 -> {define_output_path}")
        print(f"  Defineマクロ: {len(define_macros)}個 -> {macro_output_path}")
        
    except UnicodeDecodeError:
        # UTF-8で読み込めない場合はcp932で試行
        try:
            with open(input_path, 'r', encoding='cp932') as f:
                content = f.read()
            
            define_definitions, define_macros = extract_defines(content)
            
            # 出力処理（上記と同じ）
            with open(define_output_path, 'w', encoding='utf-8') as f:
                f.write(f"// Define definitions extracted from {input_path}\n")
                f.write("// " + "="*60 + "\n\n")
                if define_definitions:
                    for define in define_definitions:
                        f.write(define + "\n")
                else:
                    f.write("// No define definitions found\n")
            
            with open(macro_output_path, 'w', encoding='utf-8') as f:
                f.write(f"// Define macros extracted from {input_path}\n")
                f.write("// " + "="*60 + "\n\n")
                if define_macros:
                    for macro in define_macros:
                        f.write(macro + "\n")
                else:
                    f.write("// No define macros found\n")
            
            print(f"処理完了 (cp932): {input_path}")
            print(f"  Define定義: {len(define_definitions)}個 -> {define_output_path}")
            print(f"  Defineマクロ: {len(define_macros)}個 -> {macro_output_path}")
            
        except Exception as e:
            print(f"エラー: ファイルの読み込みに失敗しました - {input_path}: {e}")
    
    except Exception as e:
        print(f"エラー: ファイルの処理に失敗しました - {input_path}: {e}")

def extract_defines(code):
    """
    C/C++のソースコードからdefine定義とdefineマクロを抽出する
    
    Args:
        code: C/C++のソースコード文字列
    
    Returns:
        tuple: (define_definitions, define_macros) のタプル
            - define_definitions: 単純な定数定義のリスト
            - define_macros: 引数を持つマクロ定義のリスト
    """
    # まずコメントを除去（文字列リテラルは保護）
    code_without_comments = remove_c_comments_for_parsing(code)
    
    # #defineを含む行を抽出（複数行対応・改良版）
    # 行継続文字(\)を考慮した正規表現
    define_pattern = r'^\s*#define\s+[A-Za-z_][A-Za-z0-9_]*(?:\([^)]*\))?\s*(?:\\(?:\r?\n|$)|[^\r\n\\])*(?:\\(?:\r?\n[^\r\n]*)*[^\r\n\\]*)?'
    
    # より確実な方法：行単位で処理
    lines = code_without_comments.split('\n')
    defines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # #defineで始まる行を検出
        if re.match(r'^\s*#define\s+', line):
            define_block = lines[i]
            
            # 継続行がある場合の処理
            while line.rstrip().endswith('\\') and i + 1 < len(lines):
                i += 1
                define_block += '\n' + lines[i]
                line = lines[i].strip()
            
            defines.append(define_block)
        
        i += 1
    
    define_definitions = []
    define_macros = []
    
    for define in defines:
        # 改行と継続文字を正規化
        normalized_define = normalize_define(define)
        
        # マクロかどうかを判定（括弧があるかどうか）
        # #define NAME(params) の形式かチェック
        macro_pattern = r'^\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
        if re.match(macro_pattern, normalized_define):
            define_macros.append(normalized_define)
        else:
            define_definitions.append(normalized_define)
    
    return define_definitions, define_macros

def normalize_define(define_text):
    """
    #defineの継続行を正規化する
    
    Args:
        define_text: #define文字列
    
    Returns:
        正規化された#define文字列
    """
    # 行継続文字（\）とその後の改行を処理
    lines = define_text.split('\n')
    normalized_lines = []
    
    for line in lines:
        # 各行の末尾の空白を削除
        line = line.rstrip()
        
        if line.endswith('\\'):
            # 継続文字を除去して、次の行と結合する準備
            normalized_lines.append(line[:-1].rstrip())
        else:
            normalized_lines.append(line)
    
    # 複数行の場合は適切にフォーマット
    if len(normalized_lines) > 1:
        # 最初の行（#define部分）
        result = normalized_lines[0]
        
        # 継続行がある場合
        if len(normalized_lines) > 1:
            result += ' \\\n'
            for i in range(1, len(normalized_lines)):
                line = normalized_lines[i].strip()
                if i == len(normalized_lines) - 1:
                    # 最後の行には継続文字を付けない
                    result += '    ' + line
                else:
                    # 中間行には継続文字を付ける
                    result += '    ' + line + ' \\\n'
        
        return result
    else:
        return normalized_lines[0] if normalized_lines else define_text

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
    
    # 各ファイルからdefine定義とマクロを抽出
    print("\n=== Define抽出処理 ===")
    for file_path in c_h_files:
        extract_defines_from_file(file_path)
    
    # 単一ファイルのテスト例
    # extract_defines_from_file("example.h")
    
    # テスト用のサンプルコード
    sample_code = '''
    // Sample C header file
    #define MAX_SIZE 100
    #define PI 3.14159
    #define VERSION "1.0.0"
    
    // Simple macro
    #define SQUARE(x) ((x) * (x))
    
    // Multi-line macro
    #define COMPLEX_MACRO(a, b) \\
        do { \\
            printf("a = %d\\n", a); \\
            printf("b = %d\\n", b); \\
        } while(0)
    
    // Another definition
    #define DEBUG 1
    '''
    
    print("\n=== サンプルコードのテスト ===")
    definitions, macros = extract_defines(sample_code)
    
    print(f"Define定義 ({len(definitions)}個):")
    for i, d in enumerate(definitions, 1):
        print(f"  {i}. {repr(d)}")
        print(f"     {d}")
        print()
    
    print(f"Defineマクロ ({len(macros)}個):")
    for i, m in enumerate(macros, 1):
        print(f"  {i}. {repr(m)}")
        print(f"     {m}")
        print()