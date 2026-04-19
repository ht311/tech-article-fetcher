# TODO

## 型定義の自動生成導入 (plan-7 A2=b)

現状 `src/core/models.py` (Pydantic) と `dashboard/functions/api/_types.ts` は手書きミラー。
`tests/test_contract.py` でフィールド整合性を検証しているが、自動生成に移行することで
ミラー管理コストをゼロにできる。

**候補ツール**:
- `datamodel-code-generator` (pydantic → TypeScript)
- `pydantic2ts`
- OpenAPI (FastAPI 等で `/openapi.json` を出力し `openapi-typescript` で生成)

**作業内容**:
1. 自動生成ツールを選定・導入
2. `src/core/models.py` から TS 型を生成するスクリプトを `scripts/gen_types.py` に作成
3. 生成された型を `dashboard/functions/api/_types.ts` に出力する
4. `Makefile` または `package.json` の `prebuild` に組み込む
5. CI でドリフト検出 (`git diff --exit-code dashboard/functions/api/_types.ts`)
6. `tests/test_contract.py` の regex パース方式は自動生成後に削除可
