# SPReAD-1000 Azure クイックスタート — プレゼンシナリオ

- 講演時間: 20 分（Q&A 別枠）
- 対象: SPReAD-1000（第 1 回公募・令和 8 年度）採択研究代表者。**AI for Science 未経験・Azure 未経験・外注構築予算がない**研究者本人。
- ゴール: 「明日から準備を始めれば、来週には自分の分野のクイックスタートが動く」状態にする。
- スライド枚数: **20 枚 (本編) + 5 枚 (Q&A 予備)**
- **デザインシステム**:
  - **アスペクト比**: 16:9 (1920×1080)
  - **背景**: 白 `#FFFFFF`
  - **基調色**: Microsoft コーポレートカラー
    - Red `#F25022` / Green `#7FBA00` / Blue `#00A4EF` / Yellow `#FFB900`
    - テキスト `#323130` / セカンダリ `#605E5C` / カード背景 `#F3F2F1`
    - Fluent 主色 `#0078D4` (データ・強調)
  - **フォント**: Segoe UI (欧文) / Noto Sans JP (和文) / Cascadia Code (等幅)
  - **スタイル**: インフォグラフィックス優先。各スライドは図・チャート・タイムライン・アイコンセット等で主メッセージを表現
  - **クローム**: **ヘッダー・フッター・ページ番号・ウォーターマーク全て無し** (完全にクリーンな上下)
  - **アクセント色ローテーション**: スライドごとに Microsoft 4色 + Fluent 主色を巡回 (各スライドの説明に明記)

---

## Slide 1 — タイトル

**タイトル**: 外注構築費 ￥0 で、明日から動く AI for Science

**サブタイトル**: SPReAD-1000 採択研究者のための Azure クイックスタート 35 本

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 中央フォーカス (アイコン列 + タイトル + サブタイトル)
- **アクセント色**: #00A4EF (Microsoft Blue)
- **ヘッダー**: 右上に「令和 8 年度」の Blue 枠バッジ (角丸 4px, #00A4EF border 1px, 白背景, 12pt #00A4EF テキスト)
- **メインビジュアル**:
  - Y=200px から水平アイコンストリップ (幅 1200px 中央寄せ):
    - DNA ヘリックス (Red #F25022 outline, 2px stroke, Fluent System Icons)
    - 分子模型 (Green #7FBA00 outline)
    - 波形アイコン (Blue #00A4EF outline)
    - ニューラルネット (Yellow #FFB900 outline)
    - 4アイコン間を 2px #F3F2F1 線でチェーン。各アイコン 80×80px、#F3F2F1 背景円 (直径 104px)
  - Y=380px タイトル (48pt Segoe UI Semibold #323130, 中央寄せ): 「外注構築費 **￥0** で、明日から動く AI for Science」— 「￥0」のみ 60pt #0078D4
  - Y=460px サブタイトル (26pt Noto Sans JP Medium #605E5C, 中央寄せ): 「SPReAD-1000 採択研究者のための Azure クイックスタート 35 本」
  - Y=560px アクセントバー (幅 400px, 高さ 4px, 中央寄せ, #00A4EF 塗り)
- **サブ要素**:
  - Y=720px 発表者情報 (16pt Noto Sans JP #323130, 中央 3 段): 発表者名・所属・日付
  - Y=900px リポジトリ URL (12pt Cascadia Code #0078D4, 中央寄せ): `github.com/nahisaho/spread1000-azure-quickstart`
  - Y=960px アジェンダ予告バナー (幅 1200px 中央, 高さ 40px, #F3F2F1 塗り): 「予告: 明日から準備を始めれば、来週には GPU 学習を回せる」(14pt #605E5C, Yellow #FFB900 左 accent stripe 4px)
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「￥0」のみ 60pt #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「皆さん、本日はよろしくお願いします。（自己紹介）SPReAD-1000 に採択された皆さん、おめでとうございます。今日 20 分でお話しするのは、**外注構築費 ￥0 で、AI の環境を自分の手で立ち上げる方法** です。SI ベンダーに数千万円払わなくても、皆さんの研究計画書に書いた AI 環境は Azure で動きます。Azure の従量課金だけを研究費で払い、外注構築費は 1 円もかけない。ただし "明日 10 分で全部完了" というわけではありません。**明日から準備を始めれば、来週には GPU 学習を回せる**——その具体的なロードマップを、今日は **35 本のクイックスタート** とともに持ち帰っていただきます。」

---

## Slide 2 — 全部、ここに置いてあります

**タイトル**: 全部、ここに置いてあります

**サブタイトル**: `github.com/nahisaho/spread1000-azure-quickstart`（MIT ライセンス・公開中）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 中央フォーカス (リポジトリカード + QRコード + 免責ボックス)
- **アクセント色**: #7FBA00 (Microsoft Green)
- **ヘッダー**: 右上に「MIT License」Green 枠バッジ (角丸 4px, #7FBA00 border 1px, 白背景, 12pt #7FBA00)
- **メインビジュアル**:
  - Y=140px 中央リポジトリカード (幅 1100px, 高さ 220px, 白背景, #605E5C 1px border, 角丸 8px, 影 0 2px 12px rgba(0,0,0,0.08)):
    - 左上 GitHub Octocat アイコン (36×36px, #323130 塗り) + テキスト「nahisaho / spread1000-azure-quickstart」(22pt Segoe UI Semibold #323130)
    - 下部説明 (16pt Noto Sans JP #605E5C): 「SPReAD-1000 採択研究者のための Azure クイックスタート集（10 分野 × 3〜6 シナリオ = 35 本）」
    - 右端 Green バー (幅 8px, 全高, #7FBA00 塗り)
  - Y=400px 中央 QR コード (幅 320px × 高さ 320px, 白背景, #323130 モジュール, コーナースクエアを 4 色 Microsoft カラーで装飾): URL `https://github.com/nahisaho/spread1000-azure-quickstart`
  - Y=740px QR キャプション (14pt Cascadia Code #0078D4, 中央): `github.com/nahisaho/spread1000-azure-quickstart`
- **サブ要素**:
  - Y=820px 免責ボックス (幅 1584px, 高さ 148px, #FFF4F1 塗り, #F25022 2px border, 角丸 8px):
    - 左端 ⚠️ アイコン (40px, #F25022) + 太字テキスト (16pt Noto Sans JP Semibold #323130):
      「本リポジトリはコミュニティ提供の非公式サンプルです。Microsoft 公式のサポート対象ではありません。MIT ライセンスは本リポジトリの Bicep / Python コードにのみ適用。モデル・データセットは個別ライセンス。」
    - 2行目 (14pt #605E5C): 「個別のトラブル対応・SLA・本番運用サポートが必要な場合は、Microsoft Unified サポート契約、または Microsoft パートナー（MSP／SI）とのサポート契約をご検討ください。」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「全部」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「本題に入る前に、まずここだけ覚えて帰ってください。**`github.com/nahisaho/spread1000-azure-quickstart`**。今日この 20 分でお見せするコード・Bicep・ドキュメント、すべてこの GitHub リポジトリに MIT ライセンスで公開しています。登録も申込もいりません。スマホでこの QR コードを撮っていただければ、皆さんの手元にすぐ届きます。1 点だけ大事な注意です。**この リポジトリはコミュニティ提供の非公式サンプルで、Microsoft の公式サポート対象ではありません**。また MIT ライセンスはこのリポジトリの Bicep / Python コードに適用されるもので、モデルやデータセットはそれぞれ個別のライセンスが適用されます。」

---

## Slide 3 — なぜ「今」この話をするのか

**タイトル**: 採択された。でも、AI 環境は誰が作る？

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部数字バナー + 下部 3 ペインアイコンカード
- **アクセント色**: #F25022 (Microsoft Red)
- **ヘッダー**: 右上に「課題」Red 枠バッジ (角丸 4px, #F25022 border 1px, 白背景, 12pt #F25022)
- **メインビジュアル**:
  - Y=130px 上部バナー (幅 1584px, 高さ 160px, #F3F2F1 塗り, #F25022 左端 8px accent stripe):
    - 左ブロック: 「456」(120pt Segoe UI Semibold #0078D4) + 「課題」(36pt #323130) + 「SPReAD-1000 採択」(20pt #605E5C)
    - 右ブロック (デバイダー #605E5C 1px 縦): 「10 分野」(72pt Segoe UI Semibold #F25022)
  - Y=330px 3 ペインアイコンカード (各 464×380px, 白背景, #605E5C 1px border, 角丸 8px, 影 0 2px 8px rgba(0,0,0,0.08)):
    - Card 1 (左端 X=168px): 上部 Red バー 8px、研究者アイコン (Fluent person-outline 64px, #F25022) + 吹き出し (16pt Noto Sans JP #323130): 「**Azure は初めて、Bicep も初めて。でも研究計画に AI 環境と書いた**」
    - Card 2 (中央 X=660px): 上部 Yellow バー 8px、財布 + ✕ アイコン (64px, #FFB900) + 吹き出し: 「外注構築費がない」
    - Card 3 (右端 X=1152px): 上部 Blue バー 8px、時計アイコン (64px, #00A4EF) + 吹き出し: 「令和 8 年度中に成果を出さないと…」
  - Y=770px 中央結論テキスト (24pt Noto Sans JP #605E5C, 中央寄せ): 「本講演はこの 3 つの壁を、20 分で崩します。」
- **サブ要素**: なし (3 ペインカードが主役)
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「AI 環境」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「SPReAD-1000 の採択は 10 分野 456 課題。研究計画には AI を使うと書いた。でも、いざ採択されると、こう気づきます。**Azure は初めて、Bicep も初めて。GPU クォータってどう申請するの？** そして予算配分を見ると、外注構築費はほとんど積んでいない。締切だけは令和 8 年度末に迫っている。今日はこの 3 つの壁を、コピペで越えられる形にお届けします。」

---

## Slide 4 — 始める前に確認すること

**タイトル**: 「動く」を最優先。まず、この前提チェックを。

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 左右 2 カラム (約束カード + チェックリストカード)
- **アクセント色**: #FFB900 (Microsoft Yellow)
- **ヘッダー**: 右上に「✓ Checklist」Yellow 枠バッジ (角丸 4px, #FFB900 border 1px, 白背景, 12pt #FFB900)
- **メインビジュアル**:
  - 左カラム (X=168px〜792px, Y=140px〜920px, 白背景, #7FBA00 1px border, 角丸 8px):
    - 上部 Green バー (高さ 8px, #7FBA00) + 見出し「✓ お約束すること」(24pt Segoe UI Semibold #323130, Y=176px)
    - 5 アイテムリスト (20pt Noto Sans JP, Y=240px, 行間 52px):
      - ✅ Green チェック #7FBA00: 「コピペで動く 35 シナリオ」
      - ✅: 「Track A: Bicep + deploy.sh (約 10 分)」
      - ✅: 「Track B: pip install + python (数分)」
      - ✅: 「cleanup 手順 35/35 整備済み (`docs/06-cleanup.md`)」
      - ✅: 「MIT ライセンス（本リポジトリコードに限る）」
  - 右カラム (X=840px〜1752px, Y=140px〜920px, 白背景, #FFB900 1px border, 角丸 8px):
    - 上部 Yellow バー (高さ 8px, #FFB900) + 見出し「📋 始める前の前提チェックリスト」(24pt Segoe UI Semibold #323130, Y=176px)
    - 5 アイテムリスト (20pt Noto Sans JP, Y=240px, 行間 56px):
      - ✅ (Green #7FBA00): 「Azure サブスクリプション取得 & 課金設定」
      - ✅: 「所属機関の情報セキュリティ / 調達承認」
      - ⏳ (Yellow #FFB900): 「GPU クォータ申請 — 数日〜、今すぐ出す」
      - ⏳: 「AlphaFold 3 等モデル重み申請 — Google DeepMind フォーム」
      - ⏳: 「データ分類 & IRB — 個人情報・医療データを扱う場合」
- **サブ要素**:
  - Y=960px 下部免責 1 行 (14pt Noto Sans JP #605E5C, 中央寄せ, italic): 「本リポジトリは コミュニティ提供の非公式サンプル — Microsoft は本コードに対する保証・SLA・個別サポートを提供しません（MIT ライセンス "AS IS" 条項の通り）。」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「前提チェック」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「今日渡す 35 シナリオは「**まず動かす**」ためのものです。ただし動かすためには前提がいくつかあります。Azure のサブスクリプションと課金設定、所属機関の調達・セキュリティ承認、GPU が必要なシナリオならクォータ申請、AlphaFold 3 を使うなら重み申請、医療データを扱うなら IRB。これらは今日すぐに終わるものではありません。**ただし、今日から準備を始めれば来週には動かせる**。次のスライドで、その 3 段階プランをお見せします。」

---

## Slide 5 — 3 段階プラン

**タイトル**: 「明日から」は準備開始日。3 段階で進む。

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 水平タイムライン 3ステップ + 上下補助要素
- **アクセント色**: #0078D4 (Fluent Blue)
- **ヘッダー**: 右上に「3 ステップ」Blue 枠バッジ (角丸 4px, #0078D4 border 1px, 白背景, 12pt #0078D4)
- **メインビジュアル**:
  - Y=200px 中央タイムライン (水平矢印, 幅 1584px, 高さ 8px, #F3F2F1 塗り):
    - 矢印ヘッド: #0078D4 塗り 三角 24px
    - Step 1 ノード (X=336px, Y=200px): #0078D4 塗り 円 (直径 48px), 白「1」(24pt Segoe UI Semibold)
    - Step 2 ノード (X=960px): #FFB900 塗り 円、白「2」
    - Step 3 ノード (X=1584px): #7FBA00 塗り 円、白「3」
  - Y=280px 3 ステップカード (各 420×360px, 白背景, 角丸 8px, 影 0 2px 8px rgba(0,0,0,0.08)):
    - Card 1 (中央 X=336px): 上部 Blue バー 8px、🗓 カレンダーアイコン (64px, #0078D4)、見出し「今日（Day 0）」(22pt Semibold #0078D4)、本文 (16pt #323130):「サブスク確認 / CPU シナリオスモークテスト / 予算アラート設定 / GPU クォータ申請」
    - Card 2 (中央 X=960px): 上部 Yellow バー 8px、📅 アイコン (64px, #FFB900)、見出し「今週（Day 1-5）」(22pt Semibold #FFB900)、本文:「GPU クォータ承認待ち / モデル重み申請 / データ分類・IRB / 機関セキュリティ承認」
    - Card 3 (中央 X=1584px): 上部 Green バー 8px、✅ アイコン (64px, #7FBA00)、見出し「承認後 1-2 週間（Day 7-14）」(22pt Semibold #7FBA00)、本文:「GPU シナリオ本番実行 / カスタムデータ適用 / 追加シナリオへ横展開」
  - Y=680px 各カード下部に想定日数プログレスバー (幅 300px, 高さ 8px, 角丸 4px, 各ステップ色)
- **サブ要素**:
  - Y=800px 中央注意吹き出し (幅 900px, #FFF4F1 塗り, #FFB900 2px border, 角丸 8px, 中央寄せ):
    - ⚡ アイコン (Yellow) + テキスト (18pt Noto Sans JP Semibold #323130): 「GPU クォータ・モデル重み申請は **今日中に出すと最短**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「3 段階」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「"明日から動く" という表現を使いましたが、正確に言うと **明日は準備の開始日** です。CPU だけで動くシナリオ（Track B）は今日この後すぐに動かせます。GPU が必要なシナリオ（Track A のうち GPU 系）は、クォータ申請の承認待ちがあります。承認は早ければ数分、遅ければ 1 週間かかることもある。だから、**今日、スモークテストをしながら同時にクォータ申請を出す**。1 週間後には GPU 学習が回せる——これが現実的なタイムラインです。」

---

## Slide 6 — SPReAD-1000 と 10 分野

**タイトル**: 10 分野 456 課題を、10 分野 35 シナリオでカバー

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 中央円形放射マップ (10 分野 時計配置) + 左下注意ボックス
- **アクセント色**: #00A4EF (Microsoft Blue)
- **ヘッダー**: 右上に「10 分野 456 課題」Blue 枠バッジ (角丸 4px, #00A4EF border 1px, 白背景, 12pt #00A4EF)
- **メインビジュアル**:
  - 中央 (X=760px, Y=540px): 「35 quickstart」バッジ (直径 200px, #0078D4 塗り 円, 白テキスト 28pt Segoe UI Semibold, 中央寄せ)
  - 中央から放射状に 10 分野ノード (各ノード: #F3F2F1 背景円 直径 110px, アイコン 40px, ラベル 14pt Noto Sans JP #323130, 課題数 16pt Semibold 強調色):
    - 12 時 (X=760px, Y=190px): 🧬 生命科学・薬学 (98) — #F25022
    - 1 時 (X=1040px, Y=260px): 🩺 臨床科学 (70) — #7FBA00
    - 2 時 (X=1200px, Y=400px): ⚗️ 化学 (22) — #00A4EF
    - 3 時 (X=1200px, Y=540px): 👥 社会科学 (55) — #FFB900
    - 4 時 (X=1100px, Y=720px): 🔬 材料・応用医工学 (33) — #0078D4
    - 5 時 (X=940px, Y=850px): 💻 電気工学・情報科学 (68) — #F25022
    - 7 時 (X=580px, Y=850px): ⚙️ 機械・エネルギー (32) — #7FBA00
    - 8 時 (X=320px, Y=720px): 🌏 数学・物理・地球科学 (30) — #00A4EF
    - 9 時 (X=220px, Y=540px): 🌾 農学・環境 (25) — #FFB900
    - 11 時 (X=480px, Y=260px): 🎨 芸術・人文 (23) — #0078D4
  - 各ノードから中央へ 2px #00A4EF 線（放射矢印）
  - 右下小字注記 (12pt #605E5C): 「採択結果 (令和 8 年度 SPReAD-1000)、合計 456」
- **サブ要素**:
  - 左下注意ボックス (X=168px, Y=900px, 幅 700px, 高さ 64px, #FFFDE7 塗り, #FFB900 2px border, 角丸 8px):
    - ⚠️ (Yellow #FFB900) + テキスト (14pt Noto Sans JP #323130): 「**シナリオは公開課題名からの推測。改変前提。詳細は README 参照。**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「35 シナリオ」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「SPReAD-1000 は 10 分野、合計 456 課題です。私たちは、その全 10 分野に **少なくとも 3 本ずつ、合計 35 本のクイックスタート** を用意しました。ただし 1 つ大事な断り書きです。**この 35 シナリオは、文部科学省が公開している採択課題のタイトルから、「この分野ならこういう AI 環境が要るだろう」と推測して組み立てたもの** です。皆さんの実際の研究計画書とは、データもモデルもスケールも一致しないかもしれません。ですので、**「そのまま使うテンプレート」ではなく、「まず動く型」として捉え、皆さんの研究に合わせて改変してください**。生命科学は 6 本、電気・情報は 3 本、芸術・人文にも 4 本（23 課題）、というふうに、採択数のボリュームに応じて重み付けしてあります。また、Azure Machine Learning（Azure ML）というサービスを軸に、GPU 管理・データパイプライン・実験トラッキングを一元化しています。」

---

## Slide 7 — 「動く」の定義

**タイトル**: 2 つのトラック — Azure リソース系とローカル系

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部比較マトリクス + 下部デュアルターミナルカード
- **アクセント色**: #7FBA00 (Microsoft Green)
- **ヘッダー**: 右上に「2 トラック」Green 枠バッジ (角丸 4px, #7FBA00 border 1px, 白背景, 12pt #7FBA00)
- **メインビジュアル**:
  - Y=140px 比較テーブル (幅 1584px, 高さ 200px, 白背景, 角丸 8px, 影 0 2px 8px rgba(0,0,0,0.08)):
    - ヘッダー行 (高さ 52px, #F3F2F1 塗り): 空白 / 「Track A (Azure リソース系)」(#0078D4 塗り) / 「Track B (ローカル / CPU / API のみ)」(#7FBA00 塗り)
    - 行 1: シナリオ数 / 「**22 本**」/ 「**13 本**」
    - 行 2: インフラ / 「Bicep + deploy.sh」/ 「pip install のみ」
    - 行 3: 目安時間 / 「Azure リソース約 10 分」/ 「環境構築のみ数分」
    - 行 4: 例 / 「AML / GPU 学習 / Batch」/ 「病理 CNN (CPU), Speech API」
    - セル交互 #FFFFFF / #F3F2F1 縞模様
  - Y=380px デュアルターミナルカード (各 720×320px, #F3F2F1 塗り, 角丸 8px):
    - 左 (X=168px) Track A ターミナル: 上部タイトルバー (高さ 36px, #0078D4 塗り, 白テキスト「Track A — Bicep Deploy」14pt Cascadia Code), コード本文 (16pt Cascadia Code #323130 on #F3F2F1):
      ```
      ✔ Deployed AML workspace (2m 14s)
      ✔ Assigned AzureML Data Scientist role
      Done. Next: python src/train.py
      ```
    - 右 (X=1032px) Track B ターミナル: 上部タイトルバー (高さ 36px, #7FBA00 塗り, 白テキスト「Track B — pip install」14pt Cascadia Code), コード本文:
      ```
      pip install -r requirements.txt
      python src/train.py --epochs 5
      # GPU も Azure も不要
      ```
  - 右上バッジ: Track A カードの右上に「idempotent（何度打っても安全）」(12pt Segoe UI #0078D4, #EFF6FF 塗り, 角丸 12px, padding 4px 8px)
- **サブ要素**: なし (比較テーブル + ターミナルカードで完結)
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「2 つのトラック」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「私たちの『動く』の定義を明確にします。35 シナリオは **2 つのトラック** に分かれています。**Track A: Azure リソース系（22 本）** は Bicep + deploy.sh で Azure に GPU / AML Workspace などをプロビジョニングします。Azure リソースの準備に約 10 分かかりますが、以降は学習・推論ジョブを Azure 上で実行できます。**Track B: ローカル / CPU / API のみ（13 本）** は pip install と Python だけで動きます。GPU クォータの承認待ちでも今日からすぐ試せます。どちらも `deploy.sh` は idempotent なので、失敗しても打ち直せます。」

---

## Slide 8 — 全シナリオ設計の共通原則

**タイトル**: 「動かす」より難しいのは「止める」

**サブタイトル**: 課金停止を最優先に設計

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部警告バナー + 下部 3 カラム原則カード
- **アクセント色**: #F25022 (Microsoft Red)
- **ヘッダー**: 右上に「⚠️ Cost Safety」Red 枠バッジ (角丸 4px, #F25022 border 1px, 白背景, 12pt #F25022)
- **メインビジュアル**:
  - Y=140px 警告バナー (幅 1584px, 高さ 100px, #FFF4F1 塗り, #F25022 左端 4px accent stripe, 角丸 8px):
    - 左端 ⚠️ アイコン (Fluent warning-outline, 48px, #F25022)、右にテキスト「クラウドは、忘れると請求書が来る」(28pt Segoe UI Semibold #323130)
  - Y=280px 3 カラム原則カード (各 480×420px, 白背景, #605E5C 1px border, 角丸 8px, 影 0 2px 8px rgba(0,0,0,0.08)):
    - Card 1 (X=168px): 上部 Red バー (高さ 8px, #F25022)、❤️ ハートビートアイコン (Fluent heartbeat-outline, 64px, #F25022)、見出し「必ず停まる」(22pt Semibold #F25022)、本文 (16pt Noto Sans JP #323130):「cleanup.sh で全リソース削除、Key Vault は purge、Compute Instance は auto-shutdown、ストレージは soft-delete 明示解除。35/35 シナリオに docs/06-cleanup.md を整備。」
    - Card 2 (X=720px): 上部 Green バー (高さ 8px, #7FBA00)、🔔 ベルアイコン (Fluent bell-outline, 64px, #7FBA00)、見出し「予算アラート」(22pt Semibold #7FBA00)、本文:「毎シナリオに Budget + Cost Alert 設定手順。閾値 50 / 80 / 100%。超過前に通知。」
    - Card 3 (X=1272px): 上部 Blue バー (高さ 8px, #00A4EF)、♻️ リサイクルアイコン (Fluent arrow-rotate-outline, 64px, #00A4EF)、見出し「既定は最小 SKU」(22pt Semibold #00A4EF)、本文:「CPU で動くものは CPU 既定、GPU は T4 (Standard_NC4as_T4_v3)、A100 が必要なものだけ明記。Japan East (japaneast) リージョン想定。」
  - Y=756px 中央ハイライトボックス (幅 1200px, 高さ 72px, 中央寄せ, #F25022 塗り, 角丸 8px):
    - 白テキスト (22pt Noto Sans JP Semibold): 「**帰る前に必ずリソースを削除する。手順は各シナリオの `docs/06-cleanup.md` に統一形式で記載。**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「止める」のみ #F25022)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「クラウドで研究者が一番怖いのは、消し忘れです。VM を立てたまま週末を過ごすと、月曜日に数万円の請求が届きます。だから 35 シナリオすべてに **`docs/06-cleanup.md`** を用意しました。GPU リソースは既定で最小、CPU で動くものは CPU で動かす。予算アラートの張り方も全シナリオに書いてあります。ルールは 1 つだけ、**帰る前に必ず `docs/06-cleanup.md` の手順でリソースを削除する**。これだけ守ってください。」

---

## Slide 9 — 分野例 ①：生命科学・薬学（採択 98 課題）

**タイトル**: タンパク質を折り、分子を生む

**サブタイトル**: AlphaFold 3、ESMFold、TamGen、BioEmu

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 左 6 シナリオリスト + 右ビジュアル (リボン構造図) + 下部代替パス吹き出し
- **アクセント色**: #FFB900 (Microsoft Yellow)
- **ヘッダー**: 右上に「生命科学 98 課題」Yellow 枠バッジ (角丸 4px, #FFB900 border 1px, 白背景, 12pt #FFB900)
- **メインビジュアル**:
  - 左カラム (X=168px〜720px, Y=140px):
    - 見出し「6 シナリオ」(26pt Segoe UI Semibold #323130, アンダーライン Yellow #FFB900 4px)
    - 6 アイテムリスト (20pt Noto Sans JP, 行間 68px, Y=220px):
      1. 🧪 「TamGen 分子生成」— GPU バッジ (T4, #00A4EF 塗り, 白テキスト 12pt, 角丸 12px)
      2. 🧬 「ESMFold 構造予測」— GPU バッジ (A100, #F25022)
      3. 🧬 「AlphaFold 3 マルチマー」— GPU バッジ (A100, #F25022)
      4. 📊 「RNA-Seq nf-core」— バッジ (Azure Batch, #0078D4)
      5. 🔄 「BioEmu アンサンブル」— GPU バッジ (A100, #F25022)
      6. 🔬 「病理画像 CNN」— バッジ (CPU, #7FBA00)
  - 右カラム (X=760px〜1752px, Y=140px):
    - AlphaFold 3 タンパク質リボン図プレースホルダー (幅 820px, 高さ 560px, #F3F2F1 背景, 角丸 8px):
      - カラフルなリボン構造 (α ヘリックス: Red #F25022 らせん, β シート: Blue #00A4EF 矢印, ループ: Green #7FBA00 線) on #F3F2F1 背景
      - キャプション (14pt #605E5C): 「AlphaFold 3 マルチマー予測 — A100 推論」
- **サブ要素**:
  - Y=840px 吹き出しバナー (幅 920px, X=168px, 高さ 60px, #FFFDE7 塗り, #FFB900 1px border, 角丸 8px):
    - 💡 アイコン (Yellow) + テキスト (16pt Noto Sans JP #323130): 「A100 が使えなくても、T4 や CPU で学べる代替パスあり」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「折り」「生む」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「生命科学・薬学 98 課題向けには 6 本用意しました。**AlphaFold 3** はマルチマー・リガンド複合体を A100 で動かせます。予算的に A100 が難しい方は、**ESMFold や TamGen が T4 で動きます**。RNA-Seq は Azure Batch、病理画像は CPU で完結。**構造予測から創薬まで、まず 1 本手を動かせば、Azure の勘所がつかめます**。」

---

## Slide 10 — 分野例 ②：電気工学・情報科学（採択 68 課題）

**タイトル**: LLM ファインチューニングを、T4 1 枚で

**サブタイトル**: QLoRA・時系列 1D-CNN・画像復元

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 左 3 シナリオリスト + 右学習曲線グラフ + 下部強調バナー
- **アクセント色**: #0078D4 (Fluent Blue)
- **ヘッダー**: 右上に「電気・情報 68 課題」Blue 枠バッジ (角丸 4px, #0078D4 border 1px, 白背景, 12pt #0078D4)
- **メインビジュアル**:
  - 左カラム (X=168px〜720px, Y=140px):
    - 見出し「3 シナリオ」(26pt Segoe UI Semibold #323130, アンダーライン Blue #0078D4 4px)
    - 3 アイテムカード (各 480×160px, 白背景, #605E5C 1px border, 角丸 8px, 行間 16px):
      - Card 1: 🤖 「Phi-4-mini QLoRA」— GPU バッジ (T4, #0078D4 塗り, 白テキスト 12pt, 角丸 12px)、サブ (14pt #605E5C):「4bit, LoRA, 日本語 instruction チューニング」
      - Card 2: 📈 「時系列 1D-CNN UCI HAR」— バッジ (CPU, #7FBA00)、サブ:「人体活動認識, PyTorch」
      - Card 3: 🖼 「画像復元 U-Net」— バッジ (CPU, #7FBA00)、サブ:「ノイズ除去, 超解像」
  - 右カラム (X=760px〜1752px, Y=140px):
    - 学習曲線グラフ (幅 840px, 高さ 480px, 白背景, #605E5C 1px border, 角丸 8px):
      - X 軸ラベル「Epoch」(14pt #605E5C)、Y 軸ラベル「Loss」(14pt #605E5C)
      - 訓練 loss 曲線 (2px #0078D4 実線, 下降カーブ)
      - 検証 loss 曲線 (2px #7FBA00 破線, 同様に下降)
      - 凡例: 「Train (#0078D4)」「Val (#7FBA00)」(14pt)
      - グリッド線 (1px #F3F2F1)
- **サブ要素**:
  - Y=840px 強調バナー (幅 900px, X=168px, 高さ 64px, #EFF6FF 塗り, #0078D4 2px border, 角丸 8px):
    - テキスト (18pt Noto Sans JP Semibold #0078D4): 「Phi-4-mini + 4bit + LoRA = **T4 一枚で日本語 instruction 適応**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「T4 1 枚で」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「電気・情報系 68 課題は、生成 AI 応用が中心のはず。ここでは **Phi-4-mini を QLoRA 4bit で日本語 instruction チューニング** します。VRAM 16GB の T4 一枚で回ります。時系列信号分類、画像復元は CPU で動きます。**「うちの研究室に GPU がない」でも、Azure の T4 スポットで数百円から試せます**。」

---

## Slide 11 — 分野例 ③：芸術・人文学（採択 23 課題）

**タイトル**: 音声・古文書・多言語検索・GraphRAG

**サブタイトル**: フルマネージド Azure AI で「モデルを学習しない」選択

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 左 4 シナリオリスト + 右ナレッジグラフビジュアル + 下部情報ボックス
- **アクセント色**: #00A4EF (Microsoft Blue)
- **ヘッダー**: 右上に「芸術・人文 23 課題」Blue 枠バッジ (角丸 4px, #00A4EF border 1px, 白背景, 12pt #00A4EF)
- **メインビジュアル**:
  - 左カラム (X=168px〜720px, Y=140px):
    - 見出し「4 シナリオ」(26pt Segoe UI Semibold #323130, アンダーライン Blue #00A4EF 4px)
    - 4 アイテムカード (各 480×148px, 白背景, #605E5C 1px border, 角丸 8px, 行間 12px):
      - Card 1: 🎙 「Azure Speech 書き起こし」— PaaS バッジ (S0, #00A4EF 塗り, 白テキスト 12pt, 角丸 12px)
      - Card 2: 📜 「Document Intelligence 古文書翻刻」— PaaS バッジ (#00A4EF)
      - Card 3: 🌐 「Azure AI Search 多言語ハイブリッド検索」— PaaS バッジ (#00A4EF)
      - Card 4: 🕸 「Microsoft GraphRAG 史料 QA」— PaaS バッジ (#0078D4)
  - 右カラム (X=760px〜1752px, Y=140px):
    - GraphRAG ナレッジグラフビジュアル (幅 840px, 高さ 560px, #F3F2F1 背景, 角丸 8px):
      - 人物ノード (Yellow #FFB900 塗り 円, 直径 52px, 白テキスト 12pt) × 3
      - 地名ノード (Blue #00A4EF 塗り 円, 直径 48px) × 2
      - 年号ノード (Green #7FBA00 塗り 円, 直径 44px) × 2
      - エッジ: 2px #605E5C 実線, ラベル (12pt #323130): 「登場」「発生地」「年代」
      - キャプション (14pt #605E5C): 「GraphRAG — 史料の人物・地名・年号関係を可視化」
- **サブ要素**:
  - Y=840px 情報ボックス (幅 900px, X=168px, 高さ 64px, #EFF6FF 塗り, #00A4EF 2px border, 角丸 8px):
    - 📘 アイコン + テキスト (16pt Noto Sans JP #323130): 「**PaaS だから「モデル訓練」不要。API 呼び出しだけで研究プロトタイプが立ち上がる**。」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「GraphRAG」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「芸術・人文学 23 課題は、モデルを一から学習するより **既存の Azure AI サービスを呼ぶだけで解ける課題** が多い分野です。音声書き起こし、古文書 OCR、多言語横断検索、そして GraphRAG による史料の Q&A。API を叩けば動きます。**「AI を学習させる」より「AI を使う」に振り切った**、実用重視のシナリオ集です。」

---

## Slide 12 — 共通アーキテクチャパターン

**タイトル**: Track A の骨組み（22 シナリオ）

**サブタイトル**: Bicep + Managed Identity + Cleanup 手順

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 中央階層アーキテクチャ図 + 右フロー矢印 + 左下 Managed Identity バッジ
- **アクセント色**: #7FBA00 (Microsoft Green)
- **ヘッダー**: 右上に「Track A 22 本」Green 枠バッジ (角丸 4px, #7FBA00 border 1px, 白背景, 12pt #7FBA00)
- **メインビジュアル**:
  - 中央アーキテクチャ積層図 (幅 900px, X=168px, Y=140px):
    - 下段: Azure サブスクリプション ボックス (幅 860px, 高さ 64px, #F3F2F1 塗り, #605E5C 1px border, 角丸 4px, アイコン ☁️ + テキスト「Azure サブスクリプション」20pt #323130)
    - ↑ 上向き矢印 (2px #7FBA00, Y=264px)
    - 中段: Resource Group ボックス (幅 820px, 高さ 64px, #EFF6FF 塗り, #0078D4 1px border, アイコン 📦 + テキスト「Resource Group (シナリオごとに 1 個)」20pt #323130)
    - ↑ 上向き矢印 (Y=368px)
    - 上段: 個別リソース横並び (5 ボックス, 各 140×80px, 白背景, #7FBA00 1px border, 角丸 4px):
      - Storage / Key Vault / AML Workspace / Compute / RBAC
      - 各ボックスに Fluent System Icon 28px (Blue #00A4EF) + ラベル (14pt #323130)
  - 右フロー (X=1200px, Y=200px, 縦フロー):
    - Step 1 (Y=200px): 「1」Circle (Blue #0078D4 塗り) + テキスト「`main.bicep` — IaC で宣言」(18pt Noto Sans JP #323130)
    - ↓ (2px #7FBA00 矢印, 高さ 48px)
    - Step 2 (Y=316px): 「2」Circle (#7FBA00 塗り) + テキスト「`deploy.sh` — 冪等スクリプトで適用」
    - ↓ (矢印)
    - Step 3 (Y=432px): 「3」Circle (Red #F25022 塗り) + テキスト「`docs/06-cleanup.md` — リソース削除手順 (35/35 整備)」
- **サブ要素**:
  - 左下バッジ (X=168px, Y=880px, 幅 380px, 高さ 48px, #F3F2F1 塗り, #7FBA00 1px border, 角丸 24px):
    - 🔒 アイコン (Green) + テキスト (16pt Noto Sans JP #7FBA00 Semibold): 「Managed Identity 既定・パスワード不使用」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「骨組み」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「Track A の 22 シナリオはすべて、この骨組みで統一しています。**Bicep で宣言・`deploy.sh` で適用・`docs/06-cleanup.md` で片付ける**。認証は Managed Identity か Entra ID が既定。パスワードやアクセスキーをコードに書きません。1 本目を触れば、Track A の残り 21 本は同じパターンで理解できます。」

---

## Slide 13 — コスト目安：現実的な数字

**タイトル**: 実験 1 セッションで「何円かかるか」を知る

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: コストデータテーブル (上) + 2 行注意ボックス (下)
- **アクセント色**: #F25022 (Microsoft Red)
- **ヘッダー**: 右上に「💴 コスト目安」Red 枠バッジ (角丸 4px, #F25022 border 1px, 白背景, 12pt #F25022)
- **メインビジュアル**:
  - Y=140px コストテーブル (幅 1584px, 白背景, #605E5C 1px border, 角丸 8px):
    - ヘッダー行 (高さ 48px, #323130 塗り, 白テキスト 16pt Semibold): 「シナリオ」「SKU」「時間単価」「1 実験セッション」「追加コスト」
    - 行 1 (#F3F2F1 塗り): 病理画像 CNN / Standard_D4s_v3 (CPU) / 約 ¥80/h / **約 ¥40 / 30 分** (Green #7FBA00 Semibold) / Storage のみ微小
    - 行 2 (白): Phi-4-mini QLoRA / NC4as_T4_v3 スポット / 約 ¥33-100/h / **約 ¥33-100 / 時間** (#0078D4 Semibold) / Storage
    - 行 3 (#F3F2F1): Phi-4-mini QLoRA / NC4as_T4_v3 PAYG / 約 ¥90-150/h / **約 ¥90-150 / 時間** (#0078D4 Semibold) / Storage
    - 行 4 (白, 強調: #FFF4F1 塗り): AlphaFold 3 (推論 1 回) / NC24ads_A100_v4 / 約 ¥900/h / **¥3,000-6,000 / 1 セッション (3-6h)** (Red #F25022 Semibold 20pt) / egress・Storage
    - 行 5 (#F3F2F1): Speech 書き起こし / S0 / — / **約 ¥162 / 音声時間** (Green Semibold) / なし
    - 行 6 (白): GraphRAG / AOAI gpt-5 / — / **¥数千〜¥数万** (Yellow #FFB900 Semibold) / Embeddings・Search
- **サブ要素**:
  - Y=760px 黄背景注意ボックス (幅 1584px, 高さ 100px, #FFFDE7 塗り, #FFB900 2px border, 角丸 8px):
    - ⚠️ (Yellow) + テキスト (16pt Noto Sans JP Semibold #323130): 「**AlphaFold 3 は 1 回のセッションで ¥3,000-6,000 かかります。SPReAD-1000 予算内で十分回りますが、月間の試行回数を計画してください。**」
  - Y=900px 赤字注 (14pt Noto Sans JP #F25022, 右寄せ): 「**為替・スポット可用性で変動。Azure Pricing Calculator + Azure Retail Prices API で必ず確認。参考値は 2026-07 japaneast 概算。**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「何円かかるか」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「気になる金額の話を現実的に話します。CPU シナリオ（病理 CNN）は 30 分で約 40 円、コーヒー 1 杯分です。T4 スポットの QLoRA は 1 時間 33〜100 円で価格変動があります。そして **AlphaFold 3 の A100 は 1 時間約 900 円、1 回のタンパク質推論セッションは 3〜6 時間かかるので ¥3,000-6,000 程度** かかります。SPReAD-1000 の研究費で十分に賄えますが、1 回の実験コストとして計画が必要です。Speech の書き起こしは音声 1 時間あたり約 162 円、GraphRAG はコーパスの規模次第で数千円〜数万円になり得ます。**必ずご自身の契約・リージョン・為替で Azure Pricing Calculator を確認してください**。」

---

## Slide 14 — GPU クォータの壁

**タイトル**: A100 は「申請しないと出てこない」

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 左 GPU SKU テーブル + 右申請フロー図 + 下部 2 行注意ボックス
- **アクセント色**: #FFB900 (Microsoft Yellow)
- **ヘッダー**: 右上に「🖥️ GPU クォータ」Yellow 枠バッジ (角丸 4px, #FFB900 border 1px, 白背景, 12pt #FFB900)
- **メインビジュアル**:
  - 左カラム (X=168px〜720px, Y=140px):
    - 見出し「GPU SKU と既定クォータ」(22pt Segoe UI Semibold #323130, アンダーライン Yellow 4px)
    - SKU テーブル (幅 500px, #605E5C 1px border, 角丸 8px):
      - ヘッダー行 (#323130 塗り, 白テキスト 14pt Semibold): 「用途」「シリーズ (代表 SKU)」「既定クォータ」
      - 行 1 (#F3F2F1): 動作確認 / NCasT4_v3 (NC4as_T4_v3) / **0** (Red #F25022 Semibold 大)
      - 行 2 (白): 中規模 / NCv3 (NC6s_v3) / **0** (Red)
      - 行 3 (#F3F2F1, 強調): 大規模 / NCads_A100_v4 (NC24ads_A100_v4) / **0** (Red)
      - 各「0」セルに #FFF4F1 背景塗り
  - 右カラム (X=760px〜1752px, Y=140px):
    - 申請フロー (4 ステップ縦フロー, 各ステップ 幅 760px, 高さ 88px):
      - Step 1 (Yellow Circle「1」+ #FFFDE7 背景カード): 「Portal → Subscription → Usage + quotas」
      - Step 2 (Circle「2」+ カード): 「Region (japaneast) と SKU Family を選ぶ」
      - Step 3 (Circle「3」+ カード): 「Request increase → 使用目的と SPReAD-1000 課題番号を記入」
      - Step 4 (Green Circle「4」+ #F3F2F1 背景カード): 「承認: 数分〜週単位。拒否の場合は目的を詳記して再申請」
      - ステップ間を 2px #FFB900 矢印で接続
- **サブ要素**:
  - Y=780px 注意ボックス (幅 1584px, 高さ 100px, #FFFDE7 塗り, #FFB900 2px border, 角丸 8px):
    - 1 行目 ⚠️ + テキスト (16pt Noto Sans JP Semibold #323130): 「**Compute (VM) クォータと Azure ML Compute クォータは別体系。両方の申請が必要な場合あり。**」
    - 2 行目 (16pt #323130): 「**capacity 制約で region 移動が必要になる場合あり。japaneast が満杯なら eastus / westus3 を検討。**」
  - Y=920px 太字バナー (幅 1200px, 中央寄せ, 22pt Noto Sans JP Semibold #323130): 「**採択通知直後に申請を出す。承認は早ければ数分、遅ければ週単位。拒否の場合は目的を詳記して再申請。**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「申請」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「Azure の GPU は、契約直後は **クォータがゼロ** です。申請しないと 1 台も作れません。特に A100 は承認まで数分〜週単位かかることもあります——拒否されることもあります。そして注意点が 1 つ: **Compute (VM) のクォータと Azure Machine Learning のクォータは別体系です**。GPU VM が使えても、Azure ML 側のクォータが 0 だとジョブが投げられません。両方申請してください。また japaneast の capacity が逼迫している時期は、region を変更（eastus など）する必要が出ることもあります。だから、**採択通知が来たら今日すぐ申請**。手順は `docs/02-gpu-quota.md` に画面キャプチャ付きであります。」

---

## Slide 15 — AI アシスト内部レビュー

**タイトル**: AI アシスト内部レビュー

**サブタイトル**: 第三者 LLM で相互批評、実行テストとは別

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部プロセスフロー図 + 中央大数字統計 + 下部 3 カテゴリカード
- **アクセント色**: #0078D4 (Fluent Blue)
- **ヘッダー**: 右上に「🤖 AI Review」Blue 枠バッジ (角丸 4px, #0078D4 border 1px, 白背景, 12pt #0078D4)
- **メインビジュアル**:
  - Y=130px プロセスフロー (幅 1400px, 中央寄せ, 水平 5 ノード):
    - ノード 1 (幅 240px, 高さ 48px, #F3F2F1 塗り, 角丸 24px): 「執筆 (Claude)」(16pt #323130)
    - → 矢印 (2px #605E5C)
    - ノード 2 (幅 320px, 高さ 48px, #0078D4 塗り, 角丸 24px, 白テキスト): 「**AI クロスレビュー (GPT-5.6)**」(16pt Semibold)
    - → 矢印
    - ノード 3 (#F3F2F1): 「修正 (Claude)」
    - → 矢印
    - ノード 4 (#0078D4, 白): 「再レビュー」
    - → 矢印
    - ノード 5 (#7FBA00 塗り, 白): 「主要 BLOCKING 解消」(16pt Semibold)
  - Y=230px 統計数値バー (幅 1200px, 中央寄せ, 横並び 3 数値):
    - 「35」(96pt Segoe UI Semibold #0078D4) + 「シナリオ」(26pt #323130)
    - デバイダー (2px #F3F2F1 縦)
    - 「500+」(96pt Segoe UI Semibold #FFB900) + 「指摘」(26pt #323130)
    - デバイダー
    - 「主要 BLOCKING」(48pt Segoe UI Semibold #7FBA00) + 「解消済み」(26pt #323130)
  - Y=400px 3 カテゴリカード (各 480×360px, 白背景, #605E5C 1px border, 角丸 8px, 影):
    - Card 1「静的レビュー (AI)」(上部 Blue バー, #0078D4):
      各チェックアイテム (16pt Noto Sans JP #323130, 左 colored dot):
      🔒 セキュリティ (Managed Identity 未使用, シークレット漏洩)
      💸 コスト事故 (cleanup 抜け, Auto-shutdown 未設定)
      🧪 再現性 (乱数 seed, 依存版ピン止め)
      ⚖️ 倫理・ライセンス (データ由来, APPI/GDPR)
      🐛 実装バグ (NaN/Inf, split leak)
    - Card 2「静的検証 (自動)」(上部 Green バー, #7FBA00):
      コードブロック (14pt Cascadia Code #323130 on #F3F2F1):
      `bash -n` / `python -m py_compile` / `az bicep build` / `yaml.safe_load`
    - Card 3「未実施 (今後の宿題)」(上部 Yellow バー, #FFB900):
      各アイテム (16pt Noto Sans JP, ⬜ 未チェック dot):
      エンドツーエンド実行テスト
      独立外部監査
      ペネトレーションテスト
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「AI アシスト」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「私 1 人で書いたら見落とすので、**別の LLM（GPT-5.6）を並列で走らせて、指摘の総当たり戦をやりました**。500 件以上の指摘、主要な BLOCKING は解消しました。ただし、これは **AI 同士のクロスレビューで最低ライン** です。実際にコードを動かすエンドツーエンドテスト、独立した外部監査、ペネトレーションテストは別途必要です。今日は「最低限の品質チェックはした」という意味で理解してください。」

---

## Slide 16 — 使い方の流れ（実演イメージ）

**タイトル**: 迷ったら README の「5 分で動かす」節へ

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部ステップバー + 左 README モックアップ + 右ターミナルカード + 下部困ったとき案内
- **アクセント色**: #00A4EF (Microsoft Blue)
- **ヘッダー**: 右上に「🚀 Quick Start」Blue 枠バッジ (角丸 4px, #00A4EF border 1px, 白背景, 12pt #00A4EF)
- **メインビジュアル**:
  - Y=130px 上部ステップバー (幅 1584px, 高さ 60px):
    - 6 ステップノード (各 直径 40px 円, 水平等間隔, ラベル 14pt Noto Sans JP, 間を 2px 線):
      - ① clone (#00A4EF 塗り, 白「1」) + 「git clone」
      - ② cd (#7FBA00 塗り) + 「cd シナリオ」
      - ③ login (#FFB900 塗り) + 「az login」
      - ④ deploy (#0078D4 塗り) + 「deploy.sh」
      - ⑤ train (#7FBA00 塗り) + 「python train.py」
      - ⑥ cleanup (#F25022 塗り) + 「cleanup.md」
  - 左カラム (X=168px〜760px, Y=240px):
    - GitHub README モックアップカード (幅 540px, 高さ 480px, #F3F2F1 背景, #605E5C 1px border, 角丸 8px):
      - 上部 Blue タイトルバー (高さ 32px, #00A4EF 塗り): 「README.md」(14pt Cascadia Code 白)
      - 本文: 分野マップ表 + 目次が見える状態 (縮小テキスト, ブラウザ表示風)
      - 「分野マップ」と「35 シナリオ一覧」のセクション見出しが確認できる
  - 右カラム (X=780px〜1752px, Y=240px):
    - Track A ターミナルカード (幅 840px, 高さ 480px, #F3F2F1 背景, 角丸 8px):
      - 上部タイトルバー (高さ 36px, #0078D4 塗り, 白テキスト): 「Terminal — D-3 顕微鏡セグメンテーション」(14pt Cascadia Code)
      - コード本文 (16pt Cascadia Code #323130):
        ```
        git clone https://github.com/nahisaho/spread1000-azure-quickstart
        cd .../materials-medical-engineering/03-microscopy-segmentation
        az login
        bash infra/deploy.sh
        python src/train.py --epochs 5
        # 実行後は docs/06-cleanup.md の手順でリソースを削除
        ```
- **サブ要素**:
  - Y=820px 困った案内バー (幅 1584px, 高さ 52px, #F3F2F1 塗り, 角丸 8px):
    - テキスト (16pt Noto Sans JP #605E5C): 「**困ったら各シナリオの `troubleshooting.md` を見る (29/35 に整備) → GitHub Issues**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「README」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「使い方は本当にこれだけです。**リポジトリを clone、シナリオのフォルダに入る、`az login`、`deploy.sh`、学習を回す、`docs/06-cleanup.md` の手順でリソース削除**。困ったら各シナリオの `troubleshooting.md` を見てください（29/35 に整備済みです）。それでも解決しないときは GitHub Issues にお願いします。研究者コミュニティで潰していきます。」

---

## Slide 17 — 次のフェーズは、専門家と一緒に

**タイトル**: 次のフェーズは、専門家と一緒に

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部ジャッジフロー (3 分岐) + 下部調達フロー + 右上アイコン + 最下段免責
- **アクセント色**: #7FBA00 (Microsoft Green)
- **ヘッダー**: 右上に「📞 サポート先」Green 枠バッジ (角丸 4px, #7FBA00 border 1px, 白背景, 12pt #7FBA00)
- **メインビジュアル**:
  - Y=130px ジャッジフロー (幅 1584px):
    - 中央ノード (幅 360px, 高さ 52px, #F3F2F1 塗り, 角丸 4px): 「どのような状況？」(20pt #323130)
    - 分岐矢印 3 本 (Y=192px から各方向, 2px #605E5C)
    - Branch 1 左 (X=168px, Y=260px, 幅 440px, 高さ 120px, #EFF6FF 塗り, #0078D4 1px border, 角丸 8px):
      「技術的に詰まった（無償ベストエフォート）」(16pt Semibold #0078D4) + ↓ + 「GitHub Issues / Microsoft Learn / Stack Overflow」(14pt #323130)
    - Branch 2 中央 (X=660px, Y=260px, 幅 440px, 高さ 120px, #F0FFF4 塗り, #7FBA00 1px border, 角丸 8px):
      「SI サポート・本番運用設計が必要」(16pt Semibold #7FBA00) + ↓ + 「マイクロソフト パートナー（MSP / SI）」(14pt #323130)
    - Branch 3 右 (X=1152px, Y=260px, 幅 440px, 高さ 120px, #FFFDE7 塗り, #FFB900 1px border, 角丸 8px):
      「Azure 障害・SLA 対応が欲しい」(16pt Semibold #FFB900) + ↓ + 「Microsoft Unified サポート / Azure Support プラン」(14pt #323130)
  - Y=440px 調達フロー (幅 1584px, 高さ 200px, #F3F2F1 塗り, 角丸 8px):
    - 見出し「Azure 調達チャンネル」(18pt Semibold #323130)
    - 2 分岐フロー: 「所属機関に Azure 契約あり → 機関の Azure 管理者に確認」(Green path) | 「契約なし・新規調達 → 機関情報部門・調達 → MCA / EA / パートナー経由 (CSP/SI) から選択」(Blue path)
    - 「SI サポート必要 → パートナー経由」(Yellow path)
  - 右側 URL 情報 (X=1200px, Y=680px):
    - 📞 アイコン (Yellow #FFB900, 40px) + テキスト (14pt Cascadia Code #0078D4): 「partner.microsoft.com」
    - テキスト (14pt Cascadia Code #0078D4): 「azure.microsoft.com/support/plans」
- **サブ要素**:
  - Y=900px 免責ボックス (幅 1584px, 高さ 60px, #FFF4F1 塗り, #F25022 2px border, 角丸 8px):
    - テキスト (14pt Noto Sans JP Semibold #F25022): 「**本リポジトリ (GitHub) は Microsoft 公式サポート対象外。Azure サービスの SLA・障害対応は Azure Support プランまたは Unified サポート契約が必要です。**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「専門家」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「今日お渡しするクイックスタートは「自力で動かす」ためのものです。でも、**SI で本番運用したい、Azure の障害に SLA で対応してほしい**、こうなったら話が別です。**GitHub リポジトリ自体は Microsoft の公式サポート対象外**なので、そこは絶対に混同しないでください。Azure サービスの障害対応が必要なら **Azure Support プラン**、ライセンス調達や SI 構築は **マイクロソフトのパートナー（MSP や SI ベンダー）** にご相談ください。なお、Azure の調達チャンネルについて: **所属機関にすでに Azure 契約がある場合はその管理者に確認**してください。契約がない場合は MCA（Web Direct）、EA、パートナー経由（CSP/SI）など複数のチャンネルがあります。パートナー経由が唯一の手段ではありませんので、機関の調達フローに合わせて選択してください。」

---

## Slide 18 — ライセンス・データ・倫理

**タイトル**: MIT のコード、個別ライセンスのモデル・データ

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部 3 カラムライセンスマトリクス + 下部 4 ゲートプリフライトボックス
- **アクセント色**: #F25022 (Microsoft Red)
- **ヘッダー**: 右上に「⚖️ License & Ethics」Red 枠バッジ (角丸 4px, #F25022 border 1px, 白背景, 12pt #F25022)
- **メインビジュアル**:
  - Y=130px 3 カラムライセンスマトリクス (幅 1584px, 各カラム 484px, 白背景, #605E5C 1px border, 角丸 8px):
    - カラム 1「コード（本リポジトリ）」(上部 Green バー #7FBA00 8px):
      - MIT License バッジ (#7FBA00 塗り, 白テキスト, 角丸 12px)
      - 「商用利用可・研究成果への組み込み可」(16pt #323130)
      - ⚠️ 注記 (14pt #F25022): 「本リポジトリの Bicep / Python コードにのみ適用」
    - カラム 2「モデル」(上部 Yellow バー #FFB900 8px):
      各モデル行 (16pt Noto Sans JP #323130, バッジ付き):
      - MACE-MP-0: MIT バッジ (Green)
      - Phi-4-mini: MIT バッジ (Green)
      - AlphaFold 3 コード (main): Apache 2.0 バッジ (Blue)
      - AlphaFold 3 コード (v3.0.2): CC BY-NC-SA 4.0 バッジ (Yellow)
      - AlphaFold 3 重み/推論: ⛔ non-commercial バッジ (Red #F25022): 「Google DeepMind Terms of Use」
    - カラム 3「データセット」(上部 Blue バー #00A4EF 8px):
      - PlantVillage CC BY-SA 3.0 / LibriSpeech CC BY 4.0 / Materials Project CC BY 4.0 (各 14pt, バッジ)
      - 注記 (14pt #F25022): 「各データセットの個別ライセンスを確認すること」
  - Y=560px 情報ボックス (幅 1584px, 高さ 60px, #EFF6FF 塗り, #0078D4 2px border, 角丸 8px):
    - 📘 + テキスト (16pt Semibold #323130): 「**要配慮個人情報を含むデータは、APPI / GDPR / 所属機関の IRB を必ず確認**。医療・音声・古文書は特に注意。」
  - Y=660px 4 ゲートプリフライト (幅 1584px, 高さ 220px, #FFF4F1 塗り, #FFB900 2px border, 角丸 8px):
    - タイトル「4 ゲートプリフライトチェック」(20pt Semibold #323130)
    - 4 アイテム横並び (各 幅 360px, 高さ 140px, 白背景, 角丸 8px, 影):
      - Gate 1: 🗂 「データ分類」(Blue #0078D4) — 「個人情報・機密情報の該当性を所属機関で確認」(14pt)
      - Gate 2: 🌐 「デプロイ地理」(Green #7FBA00) — 「japaneast リソースでも AOAI 経由の推論は他地域で処理されることあり」(14pt)
      - Gate 3: ⚖️ 「ライセンス・輸出管理」(Yellow #FFB900) — 「weights・データセットの再配布可否、EAR/ECCN 確認」(14pt)
      - Gate 4: 👤 「人間による検証」(Red #F25022) — 「AI 出力を論文・特許・臨床判断に用いる際は必ず研究者が検証」(14pt)
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「個別ライセンス」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「ライセンスの話。**このリポジトリのコードは MIT で商用利用可**、皆さんの研究成果に自由に組み込んでいただけます。ただし MIT は **本リポジトリの Bicep / Python コードにのみ** 適用です。**Phi-4-mini は MIT ライセンス**です。AlphaFold 3 はコードが Apache 2.0（main）ですが、モデル重みと推論結果には Google DeepMind の別途非商用条項があります。データセットはそれぞれ個別ライセンス。そして 4 つのプリフライトチェックを必ず確認してください: データ分類、デプロイ地理（japaneast でも推論が他地域で処理されることがある）、ライセンス・輸出管理、そして AI 出力の人間による検証。**本リポジトリはプロトタイプ用ベースラインであり、機関認証済みではありません**。各シナリオの `docs/07-ethics-and-limits.md` に要注意ポイントを整理しました。」

---

## Slide 19 — ロードマップとコミュニティ

**タイトル**: 使ってください。壊してください。返してください。

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 左 QR コード + 右 3 アクションカード + 下部ロードマップバー
- **アクセント色**: #FFB900 (Microsoft Yellow)
- **ヘッダー**: 右上に「🌱 コミュニティ」Yellow 枠バッジ (角丸 4px, #FFB900 border 1px, 白背景, 12pt #FFB900)
- **メインビジュアル**:
  - 左カラム (X=168px〜560px, Y=140px):
    - GitHub ロゴ (Octocat, 64×64px, #323130) + テキスト「nahisaho /」+ 「spread1000-azure-quickstart」(18pt Cascadia Code #323130) Y=140px
    - QR コード (幅 280px × 高さ 280px, Y=240px, 中央寄せ, #323130 モジュール, 4 コーナーを Microsoft 4色で装飾)
    - URL テキスト (14pt Cascadia Code #0078D4, Y=560px): `github.com/nahisaho/spread1000-azure-quickstart`
  - 右カラム (X=620px〜1752px, Y=140px):
    - 3 アクションカード (各 幅 360px, 高さ 260px, 白背景, 角丸 8px, 影 0 2px 8px rgba(0,0,0,0.08), 横並び):
      - Card 1: ⭐ Star アイコン (Yellow #FFB900, 64px) + 見出し「**Star**」(22pt Semibold #FFB900) + 本文 (16pt #605E5C): 「続きの開発モチベーション」
      - Card 2: 🐛 Bug アイコン (Red #F25022, 64px) + 見出し「**Issue**」(22pt Semibold #F25022) + 本文: 「「動かなかった」「別の SKU を試したい」を歓迎」
      - Card 3: 🔀 Merge アイコン (Green #7FBA00, 64px) + 見出し「**Pull Request**」(22pt Semibold #7FBA00) + 本文: 「皆さんの分野のシナリオ追加を大歓迎」
- **サブ要素**:
  - Y=780px ロードマップバー (幅 1584px, 高さ 120px, #F3F2F1 塗り, 角丸 8px):
    - タイトル「ロードマップ (予定)」(18pt Semibold #323130)
    - 3 タグ横並び (#FFFDE7 塗り, #FFB900 1px border, 角丸 12px, 14pt Noto Sans JP #323130):
      - 「令和 9 年度採択者向けに追加 15 本」
      - 「Azure Container Apps 系 PaaS ホスティング統合」
      - 「日本語 RAG の高度化」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「返して」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「これは私一人のものではありません。**皆さんの成功事例やハマりポイントを Issue や PR で戻していただけると、次の採択者が同じ穴に落ちなくて済みます**。既に病理・PDE・GraphRAG などは、レビューで指摘されて追加になりました。皆さんの手で育ててください。」

---

## Slide 20 — まとめ

**タイトル**: 明日から準備を始めてください。

**サブタイトル**: （なし）

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 3 段キーメッセージカード + 中央 QR コード + 下部キャッチコピー
- **アクセント色**: #0078D4 (Fluent Blue)
- **ヘッダー**: 右上に「✅ まとめ」Blue 枠バッジ (角丸 4px, #0078D4 border 1px, 白背景, 12pt #0078D4)
- **メインビジュアル**:
  - Y=130px 3 段キーメッセージカード (各 幅 1400px, 高さ 96px, 中央寄せ, 白背景, 角丸 8px, 影 0 2px 8px rgba(0,0,0,0.08), 行間 12px):
    - Row 1 (左端 #0078D4 accent stripe 8px):
      - 「1」Circle (#0078D4 塗り, 白「1」32pt, 直径 56px) + テキスト (26pt Noto Sans JP Semibold #323130): 「10 分野 35 シナリオ、コピペで動く（Track A: 22 本 / Track B: 13 本）」
    - Row 2 (左端 #7FBA00 accent stripe):
      - 「2」Circle (#7FBA00 塗り) + テキスト: 「外注構築費 **￥0** で、まず「動く」を体験する」— 「￥0」は #0078D4 Semibold
    - Row 3 (左端 #FFB900 accent stripe):
      - 「3」Circle (#FFB900 塗り) + テキスト: 「本番運用・ライセンスは専門家と一緒に」
  - Y=460px 中央 QR コード (幅 240px × 高さ 240px, 中央 X=840px, 4 コーナー Microsoft カラー装飾)
  - Y=720px URL テキスト (18pt Cascadia Code #0078D4, 中央): `github.com/nahisaho/spread1000-azure-quickstart`
- **サブ要素**:
  - Y=800px 資料 URL 小テキスト (14pt Noto Sans JP #605E5C, 右寄せ): 「本講演の資料 & 実験ノート: `axies-edutech-20260817`（後日公開）」
  - Y=900px キャッチコピー (36pt Segoe UI Semibold #0078D4, 中央, アクセントバー 4px #0078D4 上下 4px): 「**研究の時間を、研究に。**」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「明日から」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「まとめます。10 分野 35 シナリオ、今日から準備開始。外注構築費 ￥0 で、まず動かす。CPU シナリオは今日できる、GPU シナリオは来週からできる。本番運用やライセンスは専門家と一緒に。**AI 環境を組む時間を、研究する時間に取り戻してください**。皆さんの成果を楽しみにしています。ご清聴ありがとうございました。」

---

---

## 予備スライド（Q&A バックアップ）

---

## A1 — なぜ Azure？（AWS / GCP との比較）

**タイトル**: なぜ Azure を選んだのか

**サブタイトル**: 「他クラウドはダメ？」という質問への回答

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 中央 3 カラム比較ポイントカード
- **アクセント色**: #00A4EF (Microsoft Blue)
- **ヘッダー**: 右上に「A1 / Q&A」Blue 枠バッジ (角丸 4px, #00A4EF border 1px, 白背景, 12pt #00A4EF)
- **メインビジュアル**:
  - Y=140px タイトル下 3 カラムカード (各 幅 460px, 高さ 500px, 白背景, #605E5C 1px border, 角丸 8px, 影):
    - Card 1 (X=168px, 上部 Blue バー #00A4EF):
      ☁️ Azure アイコン (64px, #00A4EF) + 見出し「なぜ Azure を選んだか」(20pt Semibold #323130)
      本文 (16pt Noto Sans JP #323130):
      「本リポジトリは Azure 前提のリファレンス実装。Entra ID 統合・Azure ML の一貫性・Bicep IaC の一貫性が選択理由。」
    - Card 2 (X=730px, 上部 Grey バー #605E5C):
      🔀 アイコン (64px, #605E5C) + 見出し「AWS / GCP は？」(20pt Semibold #323130)
      本文: 「AWS / GCP が悪いわけではない。所属機関の方針・既存契約・ノウハウに合わせて選択。対応ノートは各シナリオ README に補足予定。」
    - Card 3 (X=1292px, 上部 Green バー #7FBA00):
      🏛 建物アイコン (64px, #7FBA00) + 見出し「機関の既存契約を活用」(20pt Semibold #323130)
      本文: 「所属機関にすでに他クラウドの契約・ノウハウがあれば、それを活用するほうが早い。本 repo はあくまで Azure の参考実装。」
  - Y=740px 情報バー (幅 1584px, 高さ 52px, #EFF6FF 塗り, #00A4EF 1px border, 角丸 8px):
    - ℹ️ + テキスト (16pt Noto Sans JP #323130): 「本リポジトリ = Azure リファレンス実装。他クラウドを否定するものではありません。」
- **サブ要素**: なし
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「Azure」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「「なぜ Azure か？」という質問、よく受けます。本リポジトリは Azure 前提のリファレンス実装です。技術的な選択理由としては Entra ID との統合や Azure ML の一貫性があります。AWS や GCP が悪いわけではなく、所属機関の方針や既存契約に合わせて選んでください。本 repo はあくまで Azure の参考実装です。」

---

## A2 — 成果物・IP の帰属

**タイトル**: コード・モデル・論文の帰属は？

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 中央 3 カラム IP 帰属マトリクス
- **アクセント色**: #7FBA00 (Microsoft Green)
- **ヘッダー**: 右上に「A2 / Q&A」Green 枠バッジ (角丸 4px, #7FBA00 border 1px, 白背景, 12pt #7FBA00)
- **メインビジュアル**:
  - Y=140px 3 カラム帰属マトリクス (各 幅 464px, 高さ 500px, 白背景, #605E5C 1px border, 角丸 8px, 影):
    - Card 1「リポジトリコード（MIT）」(上部 Green バー #7FBA00):
      MIT バッジ (#7FBA00 塗り, 白テキスト 14pt Semibold, 角丸 4px) 上部
      📄 コードアイコン (64px, #7FBA00) + 本文 (16pt Noto Sans JP #323130):
      「皆さんに帰属。改変・再配布自由。商用利用可。本ツールを利用した研究成果・論文にも自由に組み込み可。」
    - Card 2「学習済みモデル」(上部 Yellow バー #FFB900):
      🤖 AIアイコン (64px, #FFB900) + 本文:
      「元モデルのライセンス依存（MIT / Apache 2.0 / 非商用条項を継承）。AlphaFold 3 重みは non-commercial。Phi-4-mini は MIT。個別確認必須。」
    - Card 3「研究成果・論文」(上部 Blue バー #00A4EF):
      📚 本アイコン (64px, #00A4EF) + 本文:
      「研究者に帰属。本ツールを引用する場合は GitHub URL を記載。 `github.com/nahisaho/spread1000-azure-quickstart`」
  - Y=740px 情報バー (幅 1584px, 高さ 52px, #F0FFF4 塗り, #7FBA00 1px border, 角丸 8px):
    - ✅ + テキスト (16pt Noto Sans JP #323130): 「コードは MIT で研究者の皆さんのもの。モデルは元ライセンスを継承。成果・論文はあなたのもの。」
- **サブ要素**: なし
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「帰属」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「このリポジトリのコードは MIT なので皆さんに帰属します。ただし学習させたモデルは元モデルのライセンスを継承します。研究成果・論文はもちろん研究者の皆さんのものです。」

---

## A3 — セキュリティ監査対応

**タイトル**: 機関のセキュリティ審査に通るには？

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部注意バナー + 中央 3 ステップフロー + 下部注意ボックス
- **アクセント色**: #F25022 (Microsoft Red)
- **ヘッダー**: 右上に「A3 / セキュリティ」Red 枠バッジ (角丸 4px, #F25022 border 1px, 白背景, 12pt #F25022)
- **メインビジュアル**:
  - Y=130px 上部バナー (幅 1584px, 高さ 80px, #FFF4F1 塗り, #F25022 左端 8px accent stripe, 角丸 8px):
    - 🔒 セキュリティアイコン (40px, #F25022) + テキスト (24pt Segoe UI Semibold #323130): 「本 repo はプロトタイプ用ベースライン。本番環境適用には機関固有のセキュリティ要件追加が必要。」
  - Y=260px 3 ステップフロー (水平, 幅 1400px, 中央寄せ):
    - Step 1 (幅 420px, 高さ 240px, #F3F2F1 背景, 角丸 8px, #0078D4 上部バー):
      「1」Circle (#0078D4) + 「Azure Policy 設定」(20pt Semibold #323130) + 本文 (14pt): 「リソース命名規則・許可リージョン・タグ必須ルールをポリシーで強制」
    - Step 2 (幅 420px, #F3F2F1, #7FBA00 上部バー):
      「2」Circle (#7FBA00) + 「Defender for Cloud」+ 本文: 「セキュリティスコア確認・推奨事項対応・CSPM でリスク可視化」
    - Step 3 (幅 420px, #F3F2F1, #FFB900 上部バー):
      「3」Circle (#FFB900) + 「Log Analytics 監査ログ」+ 本文: 「操作ログ・診断ログを集約。機関の CISO / 情報セキュリティ部門と設計を協議」
    - ステップ間を 2px #605E5C 矢印で接続
  - Y=600px 注意ボックス (幅 1584px, 高さ 100px, #FFFDE7 塗り, #FFB900 2px border, 角丸 8px):
    - ⚠️ + テキスト (16pt Noto Sans JP Semibold #323130): 「実装は所属機関の CISO / 情報セキュリティ部門と協議。本 repo はプロトタイプ用ベースライン、機関認証済みではありません。」
- **サブ要素**: なし
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「セキュリティ審査」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「機関のセキュリティ審査が要る場合、Azure Policy や Defender for Cloud で監査ログを整備できます。ただし本 repo はプロトタイプ用ベースラインで、機関認証済みではありません。CISO と相談の上、追加の管理策を実装してください。」

---

## A4 — 輸出管理（EAR / 経産省貿管令）

**タイトル**: モデル重みの越境利用と輸出管理

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 上部注意バナー + 中央 2 カラム (対象モデル + 確認フロー) + 下部情報カード
- **アクセント色**: #FFB900 (Microsoft Yellow)
- **ヘッダー**: 右上に「A4 / 輸出管理」Yellow 枠バッジ (角丸 4px, #FFB900 border 1px, 白背景, 12pt #FFB900)
- **メインビジュアル**:
  - Y=130px 上部バナー (幅 1584px, 高さ 80px, #FFFDE7 塗り, #FFB900 左端 8px accent stripe, 角丸 8px):
    - ⚠️ アイコン (40px, #FFB900) + テキスト (22pt Segoe UI Semibold #323130): 「一部のモデル weights は米国 EAR / 日本貿易管理令の対象になりうる」
  - Y=260px 左カラム (X=168px〜760px):
    - 「対象になりうるもの」見出し (20pt Semibold #323130, アンダーライン Yellow 4px)
    - リスト (18pt Noto Sans JP #323130, 行間 48px):
      - ⚠️ 「米国制御リスト該当品になりうるモデル weights」
      - ⚠️ 「国際共同研究での海外機関へのモデル転送」
      - ⚠️ 「輸出先国・エンドユーザーによる制限」
  - Y=260px 右カラム (X=840px〜1752px):
    - 確認フロー (3 ステップ縦フロー):
      - Step 1 (Yellow): 「モデルの ECCN / EAR 分類を確認」
      - Step 2 (Blue): 「海外機関との共有前に法務・コンプライアンス部門に照会」
      - Step 3 (Green): 「経産省 貿易管理令の適用有無を確認」
  - Y=640px 情報カード (幅 1584px, 高さ 140px, #F3F2F1 塗り, 角丸 8px):
    - 📄 + テキスト (16pt Noto Sans JP #323130): 「本リポジトリは Bicep / Python コードのみを提供。モデル weights は各ライセンス条項に従って個別ダウンロード。本 repo 自体は weights を同梱していない。」
- **サブ要素**: なし
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「輸出管理」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「国際共同研究をされる方へ。一部のモデル重みは米国の輸出管理規制（EAR）や日本の貿易管理令の対象になる可能性があります。海外機関との共同研究でモデルを共有する場合は、事前に法務・コンプライアンス部門に確認してください。」

---

## A5 — 税金アカウンタビリティ（研究費・公金の証跡）

**タイトル**: Azure 利用費の研究課題別証跡管理

**説明** (16:9 / 白背景 / Microsoft カラー / インフォグラフィック):

- **レイアウト**: 左タグ設計図 + 右コスト管理ダッシュボードモックアップ
- **アクセント色**: #0078D4 (Fluent Blue)
- **ヘッダー**: 右上に「A5 / 研究費証跡」Blue 枠バッジ (角丸 4px, #0078D4 border 1px, 白背景, 12pt #0078D4)
- **メインビジュアル**:
  - 左カラム (X=168px〜760px, Y=140px):
    - 「タグ設計例」見出し (22pt Segoe UI Semibold #323130, アンダーライン Blue #0078D4 4px)
    - 3 タグカード (各 幅 540px, 高さ 80px, #EFF6FF 塗り, #0078D4 1px border, 角丸 8px, 行間 8px):
      - タグ 1: 🏷️ (16pt Cascadia Code #0078D4): `project=SPReAD1000-課題番号`
      - タグ 2: 🏷️: `pi=研究代表者名`
      - タグ 3: 🏷️: `env=prod/dev/test`
    - 矢印 (↓ 2px #0078D4, Y=420px) + テキスト (16pt #323130): 「Azure Cost Management でタグ別集計」
    - ↓ + テキスト: 「月次明細で証跡確保」
    - ↓ + テキスト: 「科研費・JSPS 支出報告に対応」
  - 右カラム (X=800px〜1752px, Y=140px):
    - Azure Cost Management ダッシュボードモックアップ (幅 820px, 高さ 500px, 白背景, #605E5C 1px border, 角丸 8px):
      - 上部タイトルバー (高さ 36px, #0078D4 塗り): 「Cost Management — 課題別内訳」(14pt Cascadia Code 白)
      - 棒グラフ (課題番号別コスト, 4 棒, Microsoft 4色:  #F25022/#7FBA00/#00A4EF/#FFB900, 各棒に ¥金額ラベル)
      - X 軸: 課題番号 (14pt #605E5C)
      - Y 軸: コスト (円) (14pt #605E5C)
      - 凡例: env=prod/#F25022 / env=dev/#7FBA00 / env=test/#00A4EF
- **サブ要素**:
  - Y=760px 情報バー (幅 1584px, 高さ 52px, #EFF6FF 塗り, #0078D4 1px border, 角丸 8px):
    - 📊 + テキスト (16pt Noto Sans JP #323130): 「タグ設計例は README の Cost Management 節に記載。公的研究費の支出証跡管理に活用してください。」
- **タイポグラフィ**: タイトル 48pt Segoe UI Semibold #323130 (「証跡管理」のみ #0078D4)、本文 20pt Noto Sans JP
- **フッターエリアなし** (ページ番号・フッターバー・ウォーターマーク全て無し)
- **余白**: 左右 168px / 上下 96px マージン

**トークスクリプト**:
「公的研究費を Azure に使う場合、支出の証跡が必要です。Azure Cost Management のタグ機能で研究課題番号別に集計し、月次明細を保管してください。タグ設計例は README の Cost Management 節に記載しています。」

---

## タイミング配分（合計 20 分 本編）

| # | スライド | 文字数目安 | 約 秒 (380字/分) |
|---:|---|---:|---:|
| 1 | タイトル | 220 | 35 |
| 2 | GitHub 公開紹介 | 280 | 44 |
| 3 | なぜ今 | 250 | 40 |
| 4 | 前提チェック | 300 | 47 |
| 5 | 3 段階プラン | 310 | 49 |
| 6 | 10 分野マップ | 380 | 60 |
| 7 | 動くの定義（2 トラック） | 360 | 57 |
| 8 | 共通原則 | 280 | 44 |
| 9 | 生命科学例 | 220 | 35 |
| 10 | 電気・情報例 | 190 | 30 |
| 11 | 芸術・人文例 | 180 | 28 |
| 12 | アーキテクチャ | 200 | 32 |
| 13 | コスト | 400 | 63 |
| 14 | GPU クォータ | 380 | 60 |
| 15 | AI アシスト内部レビュー | 280 | 44 |
| 16 | 使い方 | 230 | 36 |
| 17 | 相談先 | 380 | 60 |
| 18 | ライセンス・倫理 | 380 | 60 |
| 19 | ロードマップ | 200 | 32 |
| 20 | まとめ | 200 | 32 |
| **合計** | | **~5,620** | **≒ 888 秒 ≒ 14 分 48 秒** |

バッファ: 残り約 5 分は Q&A への自然な移行、スライド間のトランジション、デモの補足説明に充てる。長引きそうなら Slides 9-11 の分野例を 1〜2 分野に絞る（各 30 秒削減 × 2 = 1 分短縮可能）。

