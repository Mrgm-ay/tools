#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import csv
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
from itertools import product

class CompileSwitchAnalyzer:
    def __init__(self, source_path: str):
        self.source_path = Path(source_path)
        self.switches = set()
        self.switch_lines = []
        self.cases = []
        
    def extract_compile_switches(self) -> List[Dict]:
        """ソースファイルからコンパイルスイッチを抽出"""
        switch_patterns = [
            r'#ifdef\s+(\w+)',
            r'#ifndef\s+(\w+)', 
            r'#if\s+defined\s*\(\s*(\w+)\s*\)',
            r'#if\s+!defined\s*\(\s*(\w+)\s*\)',
            r'#elif\s+defined\s*\(\s*(\w+)\s*\)',
            r'#elif\s+!defined\s*\(\s*(\w+)\s*\)'
        ]
        
        with open(self.source_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            for pattern in switch_patterns:
                match = re.search(pattern, line)
                if match:
                    switch_name = match.group(1)
                    self.switches.add(switch_name)
                    
                    # スイッチタイプを判定
                    if '#ifndef' in line or '!defined' in line:
                        switch_type = 'ifndef'
                    else:
                        switch_type = 'ifdef'
                    
                    self.switch_lines.append({
                        'line_number': line_num,
                        'line_content': line,
                        'switch_name': switch_name,
                        'switch_type': switch_type
                    })
        
        return self.switch_lines
    
    def generate_switch_cases(self) -> List[Dict]:
        """スイッチの組み合わせケースを生成"""
        if not self.switches:
            return []
        
        switches_list = sorted(list(self.switches))
        # 各スイッチに対してTrue/Falseの組み合わせを生成
        combinations = list(product([True, False], repeat=len(switches_list)))
        
        for i, combination in enumerate(combinations, 1):
            case_dict = {
                'case_no': i,
                'case_name': f"Case_{i:02d}"
            }
            
            for switch, enabled in zip(switches_list, combination):
                case_dict[switch] = enabled
            
            self.cases.append(case_dict)
        
        return self.cases
    
    def save_switch_lines_csv(self, output_dir: Path):
        """スイッチが使われている行をCSVで保存"""
        csv_path = output_dir / f"{self.source_path.stem}_switch_lines.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if self.switch_lines:
                fieldnames = ['line_number', 'line_content', 'switch_name', 'switch_type']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.switch_lines)
        
        print(f"スイッチ行情報を保存: {csv_path}")
    
    def save_cases_csv(self, output_dir: Path):
        """ケース情報をCSVで保存"""
        csv_path = output_dir / f"{self.source_path.stem}_cases.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if self.cases:
                fieldnames = ['case_no', 'case_name'] + sorted(list(self.switches))
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.cases)
        
        print(f"ケース情報を保存: {csv_path}")
    
    def preprocess_code(self, code_lines: List[str], case: Dict) -> List[str]:
        """指定されたケースに基づいてコードを前処理"""
        result = []
        stack = []  # (condition_met, original_condition) のスタック
        skip_depth = 0
        
        for line in code_lines:
            stripped = line.strip()
            
            # #ifdefや#ifndefの処理
            ifdef_match = re.match(r'#ifdef\s+(\w+)', stripped)
            ifndef_match = re.match(r'#ifndef\s+(\w+)', stripped)
            if_defined_match = re.match(r'#if\s+defined\s*\(\s*(\w+)\s*\)', stripped)
            if_not_defined_match = re.match(r'#if\s+!defined\s*\(\s*(\w+)\s*\)', stripped)
            
            if ifdef_match or if_defined_match:
                switch_name = ifdef_match.group(1) if ifdef_match else if_defined_match.group(1)
                condition_met = case.get(switch_name, False)
                stack.append((condition_met, stripped))
                if not condition_met:
                    skip_depth += 1
                continue
            
            elif ifndef_match or if_not_defined_match:
                switch_name = ifndef_match.group(1) if ifndef_match else if_not_defined_match.group(1)
                condition_met = not case.get(switch_name, False)
                stack.append((condition_met, stripped))
                if not condition_met:
                    skip_depth += 1
                continue
            
            elif stripped.startswith('#else'):
                if stack:
                    prev_condition, _ = stack[-1]
                    new_condition = not prev_condition
                    stack[-1] = (new_condition, stack[-1][1])
                    if prev_condition and not new_condition:
                        skip_depth += 1
                    elif not prev_condition and new_condition:
                        skip_depth -= 1
                continue
            
            elif stripped.startswith('#elif'):
                # 簡単な#elif defined処理
                elif_defined_match = re.match(r'#elif\s+defined\s*\(\s*(\w+)\s*\)', stripped)
                elif_not_defined_match = re.match(r'#elif\s+!defined\s*\(\s*(\w+)\s*\)', stripped)
                
                if stack:
                    prev_condition, _ = stack[-1]
                    if prev_condition:
                        # 前の条件が真だった場合、elifは評価されない
                        new_condition = False
                        if not new_condition:
                            skip_depth += 1
                    else:
                        # 前の条件が偽だった場合、elifを評価
                        if elif_defined_match:
                            switch_name = elif_defined_match.group(1)
                            new_condition = case.get(switch_name, False)
                        elif elif_not_defined_match:
                            switch_name = elif_not_defined_match.group(1)
                            new_condition = not case.get(switch_name, False)
                        else:
                            new_condition = False
                        
                        if not new_condition:
                            skip_depth += 1
                        else:
                            skip_depth -= 1
                    
                    stack[-1] = (new_condition, stripped)
                continue
            
            elif stripped.startswith('#endif'):
                if stack:
                    prev_condition, _ = stack.pop()
                    if not prev_condition and skip_depth > 0:
                        skip_depth -= 1
                continue
            
            # 通常の行の処理
            if skip_depth == 0:
                result.append(line)
        
        return result
    
    def extract_case_code(self, case: Dict, output_dir: Path):
        """指定されたケースで有効なコードを抽出して保存"""
        with open(self.source_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        processed_lines = self.preprocess_code(lines, case)
        
        # 出力ファイル名を生成
        case_no = case['case_no']
        file_extension = self.source_path.suffix
        output_filename = f"sw_case_{case_no:02d}_{self.source_path.stem}{file_extension}"
        output_path = output_dir / output_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(processed_lines)
        
        print(f"ケース {case_no} のコードを保存: {output_path}")
    
    def analyze(self, output_dir: str = None):
        """メイン解析処理"""
        if output_dir is None:
            output_dir = self.source_path.parent / "switch_analysis"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        print(f"解析対象ファイル: {self.source_path}")
        print(f"出力ディレクトリ: {output_dir}")
        
        # スイッチを抽出
        switch_lines = self.extract_compile_switches()
        print(f"検出されたスイッチ: {sorted(list(self.switches))}")
        print(f"スイッチ行数: {len(switch_lines)}")
        
        if not self.switches:
            print("コンパイルスイッチが見つかりませんでした。")
            return
        
        # ケースを生成
        cases = self.generate_switch_cases()
        print(f"生成されたケース数: {len(cases)}")
        
        # CSV保存
        self.save_switch_lines_csv(output_dir)
        self.save_cases_csv(output_dir)
        
        # 各ケースのコードを抽出
        print("\nケース別コード抽出中...")
        for case in cases:
            self.extract_case_code(case, output_dir)
        
        print(f"\n解析完了! 出力ディレクトリ: {output_dir}")

def main():
    if len(sys.argv) != 2:
        print("使用方法: python script.py <C言語ソースファイルのパス>")
        sys.exit(1)
    
    source_path = sys.argv[1]
    
    if not os.path.exists(source_path):
        print(f"ファイルが見つかりません: {source_path}")
        sys.exit(1)
    
    analyzer = CompileSwitchAnalyzer(source_path)
    analyzer.analyze()

if __name__ == "__main__":
    main()