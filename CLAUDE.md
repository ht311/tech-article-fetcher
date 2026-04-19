アーキテクチャ・技術スタック・仕様の詳細は `README.md` を参照。

# 開発スタイル

TDD で開発する（探索 → Red → Green → Refactoring）。
KPI やカバレッジ目標が与えられたら、達成するまで試行する。
不明瞭な指示は質問して明確にする。

# コード設計

- 関心の分離を保つ・状態とロジックを分離する
- コントラクト層（API/型）を厳密に定義し、実装層は再生成可能に保つ
- 静的検査可能なルールはプロンプトではなく linter か ast-grep で記述する

# コマンド

```bash
pip install -e ".[dev]"   # インストール
python -m src.main        # ローカル実行（.env 要設定）
pytest tests/ -v          # テスト
ruff check src/ tests/    # lint
mypy src/                 # 型検査
```
