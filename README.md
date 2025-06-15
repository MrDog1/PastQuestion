# 専門医試験問題データベース - 疾患名正規化プロジェクト

## 🎯 最終成果物

最終成果物は `final_output/` ディレクトリにあります：

| ファイル | 説明 |
|---------|------|
| **専門医試験比較表_normalized_v2.xlsx** | 正規化済みExcelファイル（D列の疾患名を正規化） |
| **normalize_diseases_v3.py** | 疾患名正規化スクリプト（最新版） |
| **disease_dictionary_v3.jsonl** | 疾患名辞書（812エントリ、網羅率95.56%） |

## 📊 成果

- **網羅率95.56%達成**: 辞書を784→812エントリに拡充
- **14.1%の重複削減**: 913個のユニーク疾患名を784個に削減
- **遺伝子名の適切な処理**: C3, MLH1, ETV6::NTRK3などを保持
- **表記ゆれの統合**: 
  - 「2）腺癌」「腺癌（類内膜癌）」→「腺癌」（18件に統合）
  - 「小細胞癌（CD56,Chromogranin A）」→「小細胞癌」（12件に統合）

## 🚀 使い方

```bash
# 1. 必要なライブラリをインストール
pip install pandas openpyxl python-docx striprtf

# 2. 正規化を実行
cd final_output
python normalize_diseases_v3.py

# 3. 網羅率を確認
python ../tools/coverage_analyzer.py

# 4. 辞書をメンテナンス
python ../tools/dictionary_maintenance_tool.py stats
```

## 📁 ディレクトリ構成

```
過去問DB/
├── final_output/          # 📌 最終成果物
│   ├── 専門医試験比較表_normalized_v2.xlsx
│   ├── normalize_diseases_v3.py
│   └── disease_dictionary_v3.jsonl
├── tools/                # 🛠️ メンテナンスツール
│   ├── coverage_analyzer.py
│   ├── update_dictionary.py
│   └── dictionary_maintenance_tool.py
├── reports/             # 📊 レポート類
│   └── FINAL_REPORT.md
├── archive/             # 📦 アーカイブ
├── 専門医試験比較表.xlsx   # 元データ
├── 専門医試験DB How to.docx # 仕様書
└── README.md            # このファイル
```

## 📝 処理内容

1. **Unicode正規化（NFKC）**
2. **行頭の番号・記号除去**（例: "1)", "a:"）
3. **検体状態の除去**（陰性、陽性、検体適正など）
4. **表記統一**（がん→癌、全角半角統一）
5. **遺伝子名の保持**（大文字、::記号を含む）

## 更新履歴
- 2024-06-15: プロジェクト完成、正規化処理実装