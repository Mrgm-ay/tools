#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import csv
import sys
from typing import List, Dict, Tuple, Optional
import argparse


class CStructExtractor:
    def __init__(self):
        # 構造体定義の正規表現パターン
        self.struct_pattern = re.compile(
            r'typedef\s+struct\s*(?P<tag_name>\w+)?\s*\{(?P<body>.*?)\}\s*(?P<typedef_name>\w+)\s*;|'
            r'struct\s+(?P<struct_name>\w+)\s*\{(?P<struct_body>.*?)\}\s*;',
            re.DOTALL | re.MULTILINE
        )
        
        # メンバ変数の正規表現パターン
        self.member_pattern = re.compile(
            r'(?P<type>(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:struct\s+)?(?:enum\s+)?\w+(?:\s*\*)*)\s+'
            r'(?P<name>\w+)(?:\[(?P<array_size>[^\]]*)\])?\s*(?::\s*(?P<bit_field>\d+))?\s*;'
        )
        




    def read_file(self, file_path: str) -> str:
        """ファイルを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # UTF-8で読めない場合はShift_JISやCP932を試す
            try:
                with open(file_path, 'r', encoding='shift_jis') as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='cp932') as f:
                    return f.read()

    def extract_struct_members(self, struct_body: str) -> List[Dict[str, str]]:
        """構造体のメンバを抽出"""
        members = []
        
        # 改行やタブを正規化
        struct_body = re.sub(r'\s+', ' ', struct_body.strip())
        
        # メンバ変数を検索
        for match in self.member_pattern.finditer(struct_body):
            member_type = match.group('type').strip()
            member_name = match.group('name').strip()
            array_size = match.group('array_size') if match.group('array_size') else ''
            bit_field = match.group('bit_field') if match.group('bit_field') else ''
            
            # 配列の場合は型に配列情報を追加
            if array_size:
                member_type += f'[{array_size}]'
            
            # ビットフィールドの場合は型に情報を追加
            if bit_field:
                member_type += f' : {bit_field}'
            
            members.append({
                'type': member_type,
                'name': member_name
            })
        
        return members

    def extract_structs_from_file(self, file_path: str) -> List[Dict]:
        """ファイルから構造体を抽出"""
        if not os.path.exists(file_path):
            print(f"ファイルが見つかりません: {file_path}")
            return []
        
        if not file_path.lower().endswith(('.c', '.h')):
            print(f"C言語ファイルではありません: {file_path}")
            return []
        
        try:
            content = self.read_file(file_path)
            
            structs = []
            
            for match in self.struct_pattern.finditer(content):
                # typedef struct の場合
                if match.group('typedef_name'):
                    struct_name = match.group('typedef_name')
                    tag_name = match.group('tag_name') if match.group('tag_name') else ''
                    body = match.group('body')
                # struct の場合
                elif match.group('struct_name'):
                    struct_name = match.group('struct_name')
                    tag_name = struct_name
                    body = match.group('struct_body')
                else:
                    continue
                
                members = self.extract_struct_members(body)
                
                struct_info = {
                    'file_path': file_path,
                    'struct_name': struct_name,
                    'tag_name': tag_name,
                    'members': members
                }
                
                structs.append(struct_info)
            
            return structs
            
        except Exception as e:
            print(f"ファイル処理中にエラーが発生しました: {file_path}, エラー: {e}")
            return []

    def structs_to_csv_data(self, structs: List[Dict]) -> List[List[str]]:
        """構造体データをCSV形式に変換"""
        csv_data = []
        
        # ヘッダー行
        csv_data.append([
            'ファイルパス', '構造体名', 'タグ名', 'メンバ番号', 
            'メンバ型', 'メンバ名'
        ])
        
        for struct in structs:
            file_path = struct['file_path']
            struct_name = struct['struct_name']
            tag_name = struct['tag_name']
            
            if not struct['members']:
                # メンバがない場合も1行出力
                csv_data.append([
                    file_path, struct_name, tag_name, '0', '', ''
                ])
            else:
                for i, member in enumerate(struct['members'], 1):
                    csv_data.append([
                        file_path, struct_name, tag_name, str(i),
                        member['type'], member['name']
                    ])
        
        return csv_data

    def save_to_csv(self, csv_data: List[List[str]], output_path: str):
        """CSVファイルに保存"""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(csv_data)
            print(f"CSVファイルを保存しました: {output_path}")
        except Exception as e:
            print(f"CSVファイル保存中にエラーが発生しました: {e}")

    def process_file(self, file_path: str, output_path: str = None):
        """メイン処理"""
        structs = self.extract_structs_from_file(file_path)
        
        if not structs:
            print("構造体が見つかりませんでした。")
            return
        
        print(f"構造体を {len(structs)} 個発見しました。")
        
        csv_data = self.structs_to_csv_data(structs)
        
        if output_path is None:
            # 出力ファイル名を自動生成
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_path = f"{base_name}_structs.csv"
        
        self.save_to_csv(csv_data, output_path)


def main():
    parser = argparse.ArgumentParser(
        description='C言語ソースファイルから構造体宣言を抽出してCSV化するツール'
    )
    parser.add_argument(
        'input_file', 
        help='入力するC言語ソースファイルのパス (.c または .h)'
    )
    parser.add_argument(
        '-o', '--output', 
        help='出力CSVファイルのパス (省略時は自動生成)'
    )
    
    args = parser.parse_args()
    
    extractor = CStructExtractor()
    extractor.process_file(args.input_file, args.output)


if __name__ == "__main__":
    # コマンドライン引数がない場合の使用例
    if len(sys.argv) == 1:
        print("使用例:")
        print("python struct_extractor.py sample.c")
        print("python struct_extractor.py sample.h -o output.csv")
        print("\n直接実行する場合:")
        
        # テスト用のサンプル
        sample_c_content = '''
        typedef struct {
            int id;
            char name[32];
            float value;
        } Sample;
        
        struct Point {
            double x;
            double y;
        };
        
        typedef struct Node {
            int data;
            struct Node* next;
        } Node;
        '''
        
        # テスト用ファイルを作成
        with open('test_sample.c', 'w', encoding='utf-8') as f:
            f.write(sample_c_content)
        
        extractor = CStructExtractor()
        extractor.process_file('test_sample.c', 'test_output.csv')
        
        # テスト用ファイルを削除
        os.remove('test_sample.c')
        
    else:
        main()