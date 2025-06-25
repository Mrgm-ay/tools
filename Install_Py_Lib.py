import os
import sys
import subprocess
import importlib
from pathlib import Path


class DynamicLibraryManager:
    def __init__(self):
        # 実行ファイルのディレクトリを取得
        self.script_dir = Path(__file__).parent.absolute()
        self.py_lib_dir = self.script_dir / "py_Lib"
    
    def ensure_library(self, package_name, import_name=None, version=None, version_check=True):
        """
        ライブラリの存在確認とインストールを行う
        
        Args:
            package_name (str): pipでインストールするパッケージ名
            import_name (str): インポート時の名前（異なる場合のみ指定）
            version (str): 指定するバージョン（例: "1.2.3", ">=1.0.0", "~=2.1.0"）
            version_check (bool): 既存ライブラリのバージョン確認を行うか
        
        Returns:
            module: インポートされたモジュール
        """
        if import_name is None:
            import_name = package_name
        
        # パッケージ名にバージョン指定を追加
        package_spec = self._build_package_spec(package_name, version)
        
        # 1. まず通常のインポートを試行
        try:
            module = importlib.import_module(import_name)
            
            # バージョンチェックが有効で、バージョンが指定されている場合
            if version_check and version and hasattr(module, '__version__'):
                if not self._check_version_compatibility(module.__version__, version):
                    print(f"⚠ {import_name} のバージョンが要件を満たしません")
                    print(f"  現在: {module.__version__}, 要求: {version}")
                    print("  再インストールを実行します...")
                    raise ImportError("バージョン不適合")
            
            print(f"✓ {import_name} は既にインストールされています")
            if hasattr(module, '__version__'):
                print(f"  バージョン: {module.__version__}")
            return module
            
        except ImportError:
            if version:
                print(f"✗ {import_name} (バージョン: {version}) が見つかりません。インストールを開始します...")
            else:
                print(f"✗ {import_name} が見つかりません。インストールを開始します...")
        
        # 2. py_Libディレクトリを作成
        if not os.path.exists(self.py_lib_dir): # ディレクトリが存在するか確認
            os.makedirs(self.py_lib_dir) # ディレクトリ作成
        # 3. ローカルディレクトリにインストール
        self._install_to_local_dir(package_spec)
        
        # 4. ローカルディレクトリをsys.pathに追加
        self._add_to_path()
        
        # 5. 再度インポートを試行
        try:
            module = importlib.import_module(import_name)
            print(f"✓ {import_name} のインストールとインポートが完了しました")
            if hasattr(module, '__version__'):
                print(f"  インストールされたバージョン: {module.__version__}")
            return module
        except ImportError as e:
            raise ImportError(f"ライブラリ {import_name} のインストールに失敗しました: {e}")
    
    def _build_package_spec(self, package_name, version):
        """
        パッケージ名とバージョンから pip install 用の仕様文字列を構築
        
        Args:
            package_name (str): パッケージ名
            version (str): バージョン指定
        
        Returns:
            str: pip install用のパッケージ仕様
        """
        if version is None:
            return package_name
        
        # バージョン指定の形式チェック
        if any(op in version for op in ['>=', '<=', '==', '!=', '~=', '>']):
            # 既に演算子が含まれている場合はそのまま使用
            return f"{package_name}{version}"
        else:
            # 単純なバージョン番号の場合は == を追加
            return f"{package_name}=={version}"
    
    def _check_version_compatibility(self, current_version, required_version):
        """
        現在のバージョンが要求バージョンを満たすかチェック
        
        Args:
            current_version (str): 現在インストールされているバージョン
            required_version (str): 要求されるバージョン仕様
        
        Returns:
            bool: 互換性があるかどうか
        """
        try:
            from packaging import version
            from packaging.specifiers import SpecifierSet
            
            # バージョン仕様を解析
            spec_set = SpecifierSet(required_version)
            current_ver = version.parse(current_version)
            
            return current_ver in spec_set
            
        except ImportError:
            # packagingライブラリがない場合は簡単な文字列比較
            print("⚠ packaging ライブラリがないため、簡易バージョンチェックを実行")
            if required_version.startswith('=='):
                return current_version == required_version[2:]
            elif required_version.isdigit() or '.' in required_version:
                return current_version == required_version
            else:
                print(f"⚠ バージョン仕様 '{required_version}' を解析できません")
                return True  # 不明な場合は通す
        except Exception as e:
            print(f"⚠ バージョンチェックでエラー: {e}")
            return True  # エラー時は通す
        """py_Libディレクトリを作成"""
        if not self.py_lib_dir.exists():
            self.py_lib_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ ディレクトリを作成しました: {self.py_lib_dir}")
    
    def _install_to_local_dir(self, package_spec):
        """指定されたディレクトリにpipインストールを実行"""
        try:
            cmd = [
                sys.executable, "-m", "pip", "install",
                "--target", str(self.py_lib_dir),
                package_spec
            ]
            
            print(f"インストール実行中: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✓ {package_spec} のインストールが完了しました")
            
            # インストール結果の詳細を表示（オプション）
            if result.stdout:
                print("インストール詳細:")
                print(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"✗ インストールエラー: {e}")
            if e.stderr:
                print(f"エラー詳細: {e.stderr}")
            raise
    
    def _add_to_path(self):
        """py_LibディレクトリをPythonパスに追加"""
        lib_path_str = str(self.py_lib_dir)
        if lib_path_str not in sys.path:
            sys.path.insert(0, lib_path_str)
            print(f"✓ パスに追加しました: {lib_path_str}")
    
    def list_installed_libraries(self):
        """py_Libディレクトリにインストールされたライブラリを一覧表示"""
        if not self.py_lib_dir.exists():
            print("py_Libディレクトリが存在しません")
            return
        
        print(f"\n=== py_Libディレクトリの内容 ({self.py_lib_dir}) ===")
        for item in self.py_lib_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                print(f"📁 {item.name}")
        print("=" * 50)
# より簡単な関数インターフェース
def ensure_library(package_name, import_name=None, version=None, version_check=True):
    """
    グローバルなライブラリマネージャーを使用した簡単なインターフェース
    
    Args:
        package_name (str): pipでインストールするパッケージ名
        import_name (str): インポート時の名前（異なる場合のみ指定）
        version (str): 指定するバージョン（例: "1.2.3", ">=1.0.0", "~=2.1.0"）
        version_check (bool): 既存ライブラリのバージョン確認を行うか
    
    Returns:
        module: インポートされたモジュール
    """
    if not hasattr(ensure_library, '_manager'):
        ensure_library._manager = DynamicLibraryManager()
    
    return ensure_library._manager.ensure_library(package_name, import_name, version, version_check)


if __name__ == "__main__":
    # 使用例の実行DE
    print("\n=== 簡単なインターフェースのテスト ===")
    try:
        # 簡単なインターフェースを使用（バージョン指定あり）
        numpy = ensure_library("pycparser")
        print(f"numpy version: {numpy.__version__}")
        
        # numpyを実際に使用
        #arr = numpy.array([1, 2, 3, 4, 5])
        #print(f"numpy array: {arr}")
        #print(f"sum: {arr.sum()}")
        
        # 別のバージョン指定例
        #matplotlib = ensure_library("matplotlib", version="~=3.5.0")
        #print(f"matplotlib version: {matplotlib.__version__}")
        
    except Exception as e:
        print(f"テストでエラー: {e}")