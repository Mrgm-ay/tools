#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import csv
import sys
from typing import List, Dict, Tuple, Optional
import argparse
from collections import defaultdict


class StructConfigAnalyzer:
    def __init__(self):
        # 構造体変数宣言の正規表現パターン
        self.struct_var_pattern = re.compile(
            r'(?P<struct_name>\w+)\s+(?P<var_name>\w+)(?P<array_def>\[(?P<array_size>[^\]]*)\])?\s*=\s*(?P<init_value>\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*;',
            re.DOTALL | re.MULTILINE
        )
        
        # 構造体配列宣言の正規表現パターン
        self.struct_array_pattern = re.compile(
            r'(?P<struct_name>\w+)\s+(?P<var_name>\w+)\[(?P<array_size>[^\]]*)\]\s*=\s*(?P<init_value>\{.*?\})\s*;',
            re.DOTALL | re.MULTILINE
        )
        
        # 単純な構造体変数宣言（初期化なし）
        self.simple_struct_var_pattern = re.compile(
            r'(?P<struct_name>\w+)\s+(?P<var_name>\w+)(?P<array_def>\[(?P<array_size>[^\]]*)\])?\s*;'
        )

    def read_csv_structs(self, csv_path: str) -> Dict[str, List[Dict]]:
        """CSVファイルから構造体情報を読み込み"""
        structs = defaultdict(list)
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    struct_name = row['構造体名']
                    if row['メンバ名']:  # メンバ名が空でない場合のみ追加
                        structs[struct_name].append({
                            'member_name': row['メンバ名'],
                            'member_type': row['メンバ型'],
                            'member_number': int(row['メンバ番号']) if row['メンバ番号'].isdigit() else 0
                        })
        except Exception as e:
            print(f"CSVファイル読み込みエラー: {e}")
            return {}
        
        return dict(structs)

    def read_file(self, file_path: str) -> str:
        """ファイルを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='shift_jis') as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='cp932') as f:
                    return f.read()

    def parse_init_values(self, init_str: str, members: List[Dict]) -> Dict[str, str]:
        """初期化値を解析してメンバごとの値を抽出"""
        member_values = {}
        
        # 初期化文字列から { } を除去し、内容を取得
        init_str = init_str.strip()
        if init_str.startswith('{') and init_str.endswith('}'):
            init_str = init_str[1:-1].strip()
        
        # カンマで分割（ネストした構造体は考慮しない簡易版）
        values = []
        bracket_count = 0
        current_value = ""
        
        for char in init_str:
            if char == '{':
                bracket_count += 1
            elif char == '}':
                bracket_count -= 1
            elif char == ',' and bracket_count == 0:
                values.append(current_value.strip())
                current_value = ""
                continue
            current_value += char
        
        if current_value.strip():
            values.append(current_value.strip())
        
        # メンバ名と値を対応付け
        for i, member in enumerate(members):
            if i < len(values):
                member_values[member['member_name']] = values[i]
            else:
                member_values[member['member_name']] = ""
        
        return member_values

    def parse_array_init_values(self, init_str: str, members: List[Dict]) -> List[Dict[str, str]]:
        """配列の初期化値を解析"""
        array_elements = []
        
        # 初期化文字列から外側の { } を除去
        init_str = init_str.strip()
        if init_str.startswith('{') and init_str.endswith('}'):
            init_str = init_str[1:-1].strip()
        
        # 各要素（構造体）を抽出
        bracket_count = 0
        current_element = ""
        
        for char in init_str:
            if char == '{':
                bracket_count += 1
            elif char == '}':
                bracket_count -= 1
                current_element += char
                if bracket_count == 0:
                    # 一つの構造体要素が完成
                    element_values = self.parse_init_values(current_element, members)
                    array_elements.append(element_values)
                    current_element = ""
                    continue
            elif char == ',' and bracket_count == 0:
                continue
            
            if bracket_count > 0:
                current_element += char
        
        return array_elements

    def extract_struct_declarations(self, content: str, structs_info: Dict[str, List[Dict]]) -> List[Dict]:
        """構造体変数宣言を抽出"""
        declarations = []
        declaration_counter = defaultdict(int)
        
        # 初期化ありの構造体変数を検索
        for match in self.struct_var_pattern.finditer(content):
            struct_name = match.group('struct_name')
            var_name = match.group('var_name')
            array_size = match.group('array_size') if match.group('array_size') else None
            init_value = match.group('init_value')
            
            if struct_name not in structs_info:
                continue
            
            declaration_counter[f"{struct_name}_{var_name}"] += 1
            declaration_id = declaration_counter[f"{struct_name}_{var_name}"]
            
            members = structs_info[struct_name]
            
            if array_size:
                # 配列の場合
                var_name_with_array = f"{var_name}[]"
                array_elements = self.parse_array_init_values(init_value, members)
                
                for element_index, element_values in enumerate(array_elements):
                    for member in members:
                        member_name = member['member_name']
                        member_value = element_values.get(member_name, "")
                        
                        declarations.append({
                            'struct_name': struct_name,
                            'var_name': var_name_with_array,
                            'member_name': member_name,
                            'init_value': member_value,
                            'array_size': array_size,
                            'declaration_id': declaration_id,
                            'element_index': element_index
                        })
            else:
                # 単一構造体の場合
                member_values = self.parse_init_values(init_value, members)
                
                for member in members:
                    member_name = member['member_name']
                    member_value = member_values.get(member_name, "")
                    
                    declarations.append({
                        'struct_name': struct_name,
                        'var_name': var_name,
                        'member_name': member_name,
                        'init_value': member_value,
                        'array_size': "",
                        'declaration_id': declaration_id,
                        'element_index': None
                    })
        
        # 初期化なしの構造体変数も検索
        for match in self.simple_struct_var_pattern.finditer(content):
            struct_name = match.group('struct_name')
            var_name = match.group('var_name')
            array_size = match.group('array_size') if match.group('array_size') else None
            
            if struct_name not in structs_info:
                continue
            
            # 既に初期化ありで見つかっているものは除外
            full_match_found = False
            for decl in declarations:
                if (decl['struct_name'] == struct_name and 
                    decl['var_name'].replace('[]', '') == var_name):
                    full_match_found = True
                    break
            
            if full_match_found:
                continue
            
            declaration_counter[f"{struct_name}_{var_name}"] += 1
            declaration_id = declaration_counter[f"{struct_name}_{var_name}"]
            
            members = structs_info[struct_name]
            var_display_name = f"{var_name}[]" if array_size else var_name
            
            for member in members:
                declarations.append({
                    'struct_name': struct_name,
                    'var_name': var_display_name,
                    'member_name': member['member_name'],
                    'init_value': "",
                    'array_size': array_size if array_size else "",
                    'declaration_id': declaration_id,
                    'element_index': None
                })
        
        return declarations

    def create_result_csv(self, declarations: List[Dict], target_file_path: str):
        """結果CSVを作成"""
        # 出力フォルダを作成
        output_dir = "result_struct_config"
        os.makedirs(output_dir, exist_ok=True)
        
        # ファイル名を生成
        base_name = os.path.basename(target_file_path)
        output_filename = f"struct_config_{base_name}.csv"
        output_path = os.path.join(output_dir, output_filename)
        
        # CSVデータを準備
        csv_data = []
        csv_data.append([
            '構造体名', '変数名', 'メンバ名', '初期値', '配列要素数'
        ])
        
        for decl in declarations:
            csv_data.append([
                decl['struct_name'],
                decl['var_name'],
                decl['member_name'],
                decl['init_value'],
                decl['array_size']
            ])
        
        # CSVファイルに保存
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(csv_data)
            print(f"結果CSVファイルを保存しました: {output_path}")
            print(f"抽出された宣言数: {len(declarations)}")
        except Exception as e:
            print(f"CSVファイル保存中にエラーが発生しました: {e}")

    def analyze(self, csv_path: str, target_file_path: str):
        """メイン解析処理"""
        print(f"構造体情報CSV: {csv_path}")
        print(f"調査対象ファイル: {target_file_path}")
        
        # 構造体情報を読み込み
        structs_info = self.read_csv_structs(csv_path)
        if not structs_info:
            print("構造体情報の読み込みに失敗しました。")
            return
        
        print(f"読み込まれた構造体数: {len(structs_info)}")
        
        # 調査対象ファイルを読み込み
        try:
            content = self.read_file(target_file_path)
        except Exception as e:
            print(f"調査対象ファイル読み込みエラー: {e}")
            return
        
        # 構造体宣言を抽出
        declarations = self.extract_struct_declarations(content, structs_info)
        
        if not declarations:
            print("構造体変数の宣言が見つかりませんでした。")
            return
        
        # 結果CSVを作成
        self.create_result_csv(declarations, target_file_path)


def main():
    parser = argparse.ArgumentParser(
        description='構造体CSVと調査対象ファイルから構造体変数設定を抽出'
    )
    parser.add_argument('csv_path', help='構造体情報CSVファイルのパス')
    parser.add_argument('target_file', help='調査対象ファイルのパス')
    
    args = parser.parse_args()
    
    analyzer = StructConfigAnalyzer()
    analyzer.analyze(args.csv_path, args.target_file)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("使用例:")
        print("python struct_config_analyzer.py structs.csv target.c")
        print("\n直接実行する場合のテスト:")
        
        # テスト用のサンプルファイル作成
        sample_csv_content = '''ファイルパス,構造体名,タグ名,メンバ番号,メンバ型,メンバ名
test.h,Config,Config,1,int,id
test.h,Config,Config,2,char[32],name
test.h,Config,Config,3,float,value
test.h,Point,Point,1,double,x
test.h,Point,Point,2,double,y'''
        
        sample_c_content = '''
        Config settings = {1, "test", 3.14};
        Config configs[2] = {{1, "first", 1.0}, {2, "second", 2.0}};
        Point origin = {0.0, 0.0};
        Point points[3] = {{1.0, 2.0}, {3.0, 4.0}, {5.0, 6.0}};
        '''
        
        # テスト用ファイル作成
        with open('test_structs.csv', 'w', encoding='utf-8-sig') as f:
            f.write(sample_csv_content)
        
        with open('test_target.c', 'w', encoding='utf-8') as f:
            f.write(sample_c_content)
        
        # テスト実行
        analyzer = StructConfigAnalyzer()
        analyzer.analyze('test_structs.csv', 'test_target.c')
        
        # テスト用ファイル削除
        os.remove('test_structs.csv')
        os.remove('test_target.c')
        
    else:
        main()