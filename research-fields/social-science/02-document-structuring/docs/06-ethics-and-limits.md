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

## 8. Azure OpenAI 濫用モニタリング (Abuse Monitoring)

Azure OpenAI サービスは既定で **30 日間のサービス側コンテンツログ** を保持します。

- **自動システム + 一部の Microsoft 担当者** が限定的な状況下でログを閲覧する場合があります
- これは Azure の利用規約に基づく濫用対策であり、デフォルトで有効です
- 詳細: [Azure OpenAI Data Privacy](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy)

### 修正済み濫用モニタリングの申請

個人情報・PHI (Protected Health Information) を含む文書を処理する場合は、可能であれば次の方法で対応してください：

1. **修正済み濫用モニタリングを申請**: <https://aka.ms/oai/modifiedaccess>  
   承認後はサービス側ログが無効化または制限されます
2. **または、アップロード前に匿名化・仮名化** を徹底する (`docs/03-prepare-documents.md` の不可逆的マスキング手順を参照)

### モニタリング状態の確認

```bash
az cognitiveservices account show \
  -g "$DOC_RG" \
  -n "$AOAI_ACCOUNT_NAME" \
  --query "properties.abuseMonitoring"
```

## 9. APPI・インフォームドコンセント チェックリスト

実在人物のデータ (判例の当事者、アンケート回答等) を処理する際は、以下をすべて確認してください：

- [ ] **同意または法的例外**: 個人情報保護法の利用目的に沿った同意取得済み、または同法 16 条の例外 (学術研究目的等) に該当
- [ ] **目的適合性**: 当初の収集目的の範囲内での利用であること
- [ ] **クラウド・AI 利用の開示**: 同意書または参加者への説明文書に「クラウドサービス (Azure) および AI モデル (Azure OpenAI) で処理する」旨を明記
- [ ] **保管期間と削除**: 保管期限を定め、`.env` / `data/output/` の削除スケジュールを研究計画に記載
- [ ] **撤回対応**: 参加者が同意を撤回した場合の削除手順を研究計画に記載
- [ ] **機関 DPA (Data Processing Agreement)**: 所属機関と Microsoft の間の DPA が締結済みか確認
- [ ] **倫理委員会承認**: 機関の倫理委員会 (IRB 相当) の承認を取得  
  ※ IRB 承認はインフォームドコンセントの代替にはなりません



- [『AI 事業者ガイドライン（第1.2版）』経済産業省 (2026-03-31)](https://www.meti.go.jp/shingikai/mono_info_service/ai_shakai_jisso/index.html)
- [個人情報保護法 (e-Gov)](https://laws.e-gov.go.jp/law/415AC0000000057)
- [著作権法 (e-Gov)](https://laws.e-gov.go.jp/law/345AC0000000048)
