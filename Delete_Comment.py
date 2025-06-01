import re
from pathlib import Path

def remove_comments_from_file(file_path):
    """
    指定されたパスのC/Hファイルからコメントを除去し、result_commentフォルダ内に出力
    
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
    output_base_dir = script_dir / "result_comment"
    
    # 相対パスの構造を保持した出力パスを作成
    output_path = output_base_dir / input_path
    
    # 出力ディレクトリを作成（存在しない場合）
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # ファイルを読み込み
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # コメントを除去
        cleaned_content = remove_c_comments(content)
        
        # 結果を出力ファイルに書き込み
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"処理完了: {input_path} -> {output_path}")
        
    except UnicodeDecodeError:
        # UTF-8で読み込めない場合はcp932で試行
        try:
            with open(input_path, 'r', encoding='cp932') as f:
                content = f.read()
            
            cleaned_content = remove_c_comments(content)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            print(f"処理完了 (cp932): {input_path} -> {output_path}")
            
        except Exception as e:
            print(f"エラー: ファイルの読み込みに失敗しました - {input_path}: {e}")
    
    except Exception as e:
        print(f"エラー: ファイルの処理に失敗しました - {input_path}: {e}")

def remove_c_comments(code):
    """
    C/C++のコメントを除去する関数
    
    Args:
        code: C/C++のソースコード文字列
    
    Returns:
        コメントが除去されたソースコード文字列
    """
    # 文字列リテラルとコメントを正しく処理するための正規表現
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
        # 文字列リテラルの場合はそのまま返す
        if match.group(1):
            return match.group(1)
        # コメントの場合
        else:
            comment = match.group(2)
            # ブロックコメントの場合、改行を保持
            if comment.startswith('/*'):
                return '\n' * comment.count('\n')
            # 行コメントの場合は空文字に置換
            else:
                return ''
    
    # 正規表現を使ってコメントを除去
    result = re.sub(pattern, replace_comment, code, flags=re.MULTILINE | re.DOTALL | re.VERBOSE)
    
    # 連続する空行を1行にまとめる
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
    
    return result

# 使用例とテスト用のコード
if __name__ == "__main__":
    # 前回の関数も含めてテスト
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
    
    # 各ファイルのコメントを除去
    print("\n=== コメント除去処理 ===")
    for file_path in c_h_files:
        remove_comments_from_file(file_path)
    
    # 単一ファイルのテスト例
    # remove_comments_from_file("example.c")