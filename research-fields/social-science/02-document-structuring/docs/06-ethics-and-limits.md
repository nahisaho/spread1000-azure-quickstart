# 06 — 倫理・限界 (必読)

## 1. 抽出結果は必ず人が検証する

LLM は **もっともらしい JSON** を返しますが、**元文書に無い値を作る (hallucination)** リスクは 0 ではありません。

- Structured Outputs は「型と enum の準拠」を保証するだけで、「値の正確性」は保証しません
- 本シナリオは全レコードに `source_page_range` を付与しますが、その参照先に実際に該当記述があるかは AI 判定です
- **法務・行政利用では必ず、原 PDF と抽出 JSON を人が並べて検証**してください

## 2. 著作権 (日本)

- **著作権法 13 条**: 法令、条約、告示、訓令、通達、及び裁判所の判決・決定・命令等、これらの翻訳物や編集物で国・地方公共団体等が作成するものは、著作権の目的とならない
- ただし、**判例集** (民集、刑集、判時、判タ等) のような **編集著作物** や、コメンタリー付き解説は、編集の創作性に対して著作権が及ぶ場合があります
- 民間出版社が制作した判例データベースの利用規約は個別確認してください

出典: [e-Gov 著作権法](https://laws.e-gov.go.jp/law/345AC0000000048)

## 3. 個人情報保護

判例には氏名、住所、勤務先、家族構成、事件履歴などが含まれることがあります。特に：

- **要配慮個人情報** (個人情報保護法 2 条 3 項): 犯罪歴、病歴、被害の事実 等
- 公開判例でも、複数属性を組み合わせると **再識別** できる場合があります

**推奨**:

- アップロード前に氏名・住所・勤務先を伏字（例: `〇〇太郎`）に置換
- 事件番号は残しても被告名は伏せる (研究目的が事件識別で無い限り)
- 抽出後の JSON にも同じマスキングを維持

出典: [個人情報保護委員会 FAQ](https://www.ppc.go.jp/all_faq_index/faq4-q011/)

## 4. データ主権 (Data Residency)

- **Document Intelligence**: 入力 PDF と分析結果はリソースリージョンで処理され、**分析結果は約 24 時間** サービス側に保持されます
- **Azure OpenAI**:
  - Standard/Regional: リージョン内処理
  - Global Standard: 世界のどこかで処理される可能性
  - DataZone Standard: 地理ゾーン内 (APAC/EU/US)

個人情報を含む文書には **必ず Regional** を選び、`AZURE_OPENAI_DEPLOYMENT_TYPE=Standard` として `.env` に記録してください。

参考:
- [Document Intelligence privacy](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security)
- [Azure OpenAI privacy](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy)

## 5. IRB / 倫理審査

- 実在被験者・原告・被告のデータを扱う場合、必ず所属機関の **IRB (倫理審査委員会)** を通してください
- 本シナリオ同梱の `data/demo-*.pdf` は完全に架空 (CC0) なので IRB 不要

## 6. 公表時の記載事項 (推奨)

論文・レポートで抽出結果を報告する場合：

- Document Intelligence モデル (`prebuilt-layout`) と API バージョン
- Azure OpenAI モデル ID とバージョン (`gpt-5.4-mini-2026-03-17`)
- デプロイタイプ (Regional/Global) とリージョン
- Prompt (全文) と Pydantic スキーマ (`schemas.py` のコミット SHA)
- `reasoning_effort`, `seed` (指定した場合), `system_fingerprint`
- 抽出件数、リフューザル件数、人による検証結果
- 抽出結果と原文の対応関係 (ページ範囲)

## 7. Do / Don't

| ✅ Do | ❌ Don't |
|---|---|
| 架空データや公開告示でパイプライン検証 | 個人情報付き実文書を無マスキングでアップロード |
| 抽出結果を人が原文と照合 | 抽出 JSON をそのまま業務判断に使う |
| `source_page_range` を保存し監査可能に | 抽出根拠を捨てる |
| Regional Standard でデータ主権確保 | Global で個人情報を送る |
| Structured Outputs で型を強制 | JSON モードなしで自由記述させる |

## 8. 追加参考文献

- [『AI 事業者ガイドライン（第1.0版）』総務省・経済産業省 (2024)](https://www.meti.go.jp/press/2024/04/20240419004/20240419004.html)
- [個人情報保護法 (e-Gov)](https://laws.e-gov.go.jp/law/415AC0000000057)
- [著作権法 (e-Gov)](https://laws.e-gov.go.jp/law/345AC0000000048)
