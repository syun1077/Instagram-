# Instagram 自動投稿Bot セットアップガイド

すべて無料で完了します。所要時間は約20〜30分です。

---

## ステップ 1: ライブラリのインストール

コマンドプロンプト（またはターミナル）を開き、プロジェクトフォルダに移動して以下を実行:

```bash
cd C:\Users\kasyu\Instagram
pip install -r requirements.txt
```

成功すると以下のようなメッセージが出ます:
```
Successfully installed Pillow-10.x.x python-dotenv-1.x.x requests-2.x.x
```

---

## ステップ 2: .env ファイルを作成

```bash
copy .env.example .env
```

これで `.env` ファイルが作成されます。
この後のステップで取得するキーを、このファイルに書き込んでいきます。

---

## ステップ 3: Imgur Client ID を取得する（所要時間: 約5分）

Imgurは画像を一時的にWebにアップロードするために使います。
Instagram APIは「画像のURL」を要求するため、ローカルの画像を一旦Webに上げる必要があります。

### 3-1. Imgurアカウントを作成
1. ブラウザで https://imgur.com/ を開く
2. 右上の「Sign Up」をクリック
3. メールアドレスとパスワードを入力して登録
4. 届いた確認メールのリンクをクリック

### 3-2. APIアプリケーションを登録
1. ログインした状態で https://api.imgur.com/oauth2/addclient を開く
2. フォームを以下のように入力:

| 項目 | 入力内容 |
|---|---|
| **Application name** | `insta-bot`（何でもOK） |
| **Authorization type** | 「OAuth 2 authorization **without** a callback URL」を選択 |
| **Email** | 自分のメールアドレス |
| **Description** | 空欄でOK |

3. 「Submit」をクリック
4. 次の画面に **Client ID** と **Client Secret** が表示される
5. **Client ID** だけをコピーする（`Client Secret` は今回使いません）

### 3-3. .env に書き込む
`.env` ファイルをメモ帳やVSCodeで開いて:

```
IMGUR_CLIENT_ID=ここにコピーしたClient IDを貼り付け
```

例:
```
IMGUR_CLIENT_ID=a1b2c3d4e5f6g7h
```

> ⚠ 引用符（""や''）は付けないでください。

---

## ステップ 4: Instagram をビジネスアカウントに切り替える（所要時間: 約3分）

Instagram Graph API を使うには「ビジネスアカウント」または「クリエイターアカウント」が必要です。
切り替えは無料で、いつでも個人アカウントに戻せます。

### 4-1. Instagramアプリで切り替え
1. Instagramアプリを開く
2. 右下のプロフィールアイコンをタップ
3. 右上の「≡」メニューをタップ
4. 「設定とプライバシー」をタップ
5. 「アカウントの種類とツール」をタップ
6. 「プロアカウントに切り替える」をタップ
7. カテゴリを選ぶ（何でもOK。例: 「個人ブログ」「アーティスト」など）
8. 「クリエイター」または「ビジネス」を選択（どちらでもOK）

### 4-2. Facebookページとリンクする
切り替え途中で「Facebookページにリンク」する画面が出ます。

**Facebookページをまだ持っていない場合:**
1. https://www.facebook.com/pages/create にアクセス
2. ページ名を入力（Instagramのアカウント名と同じでOK）
3. カテゴリを選択（何でもOK）
4. 「Facebookページを作成」をクリック

**リンクの手順:**
1. Instagramアプリの設定で「Facebookページにリンク」
2. 作成したFacebookページを選択して「完了」

---

## ステップ 5: Meta Developers でアプリを作成する（所要時間: 約5分）

### 5-1. Meta Developers にログイン
1. ブラウザで https://developers.facebook.com/ を開く
2. 右上の「ログイン」→ Facebookアカウントでログイン
3. 初回はデベロッパー登録が求められるので、規約に同意して登録

### 5-2. アプリを作成
1. 上部メニューの「マイアプリ」をクリック
2. 「アプリを作成」ボタンをクリック
3. 以下のように設定:

| 項目 | 選択・入力内容 |
|---|---|
| **ユースケース** | 「その他」を選択 → 「次へ」 |
| **アプリタイプ** | 「ビジネス」を選択 → 「次へ」 |
| **アプリ名** | `Instagram Auto Bot`（何でもOK） |
| **メールアドレス** | 自動入力されている自分のアドレスでOK |

4. 「アプリを作成」をクリック
5. パスワードを入力して確認

---

## ステップ 6: Instagram Graph API のアクセストークンを取得する（所要時間: 約10分）

### 6-1. Graph API Explorer を開く
1. https://developers.facebook.com/tools/explorer/ にアクセス
2. 右上の「Meta App」ドロップダウンから、ステップ5で作ったアプリを選択

### 6-2. 権限（パーミッション）を追加する
1. 右側の「Permissions」欄の下にある「Add a Permission」をクリック
2. 以下の3つの権限を検索して追加:

```
instagram_basic
instagram_content_publish
pages_read_engagement
```

それぞれクリックして追加してください。

### 6-3. アクセストークンを生成
1. 「Generate Access Token」ボタンをクリック
2. ポップアップが出たら「続行」や「許可」をクリック
3. Facebookページへのアクセスを許可する画面で、ステップ4でリンクしたページにチェックを入れて「次へ」
4. Instagramアカウントへのアクセス許可で「次へ」
5. 最終確認で「完了」

**表示されたアクセストークン（長い文字列）をコピー。**

### 6-4. .env に書き込む
```
INSTAGRAM_ACCESS_TOKEN=ここにコピーしたトークンを貼り付け
```

> ⚠ このトークンは約1〜2時間で期限切れになります。
> テスト段階ではこれで十分ですが、本番運用時は「長期トークン」に交換してください（後述）。

---

## ステップ 7: Instagram Account ID を取得する（所要時間: 約5分）

引き続き Graph API Explorer（https://developers.facebook.com/tools/explorer/）で作業します。

### 7-1. FacebookページのIDを取得
1. 上部の入力欄に以下を入力:
```
me/accounts
```
2. HTTPメソッドが「GET」になっていることを確認
3. 「Submit」（送信）ボタンをクリック
4. レスポンス（右側のJSON）の中から、自分のFacebookページの情報を探す

```json
{
  "data": [
    {
      "name": "あなたのページ名",
      "id": "123456789012345"  ← これがページID
    }
  ]
}
```

**この `id` の数字をコピーしてください。**

### 7-2. Instagram Business Account ID を取得
1. 上部の入力欄を以下のように書き換え（{page_id} に先ほどの数字を入れる）:
```
123456789012345?fields=instagram_business_account
```
2. 「Submit」（送信）をクリック
3. レスポンス:

```json
{
  "instagram_business_account": {
    "id": "17841400000000000"  ← これがInstagram Account ID
  },
  "id": "123456789012345"
}
```

**`instagram_business_account` の `id` をコピー。**

### 7-3. .env に書き込む
```
INSTAGRAM_ACCOUNT_ID=ここにコピーしたIDを貼り付け
```

---

## ステップ 8: .env の最終確認

`.env` ファイルが以下のようになっているか確認:

```env
IMGUR_CLIENT_ID=a1b2c3d4e5f6g7h
INSTAGRAM_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
INSTAGRAM_ACCOUNT_ID=17841400000000000
```

3つの値がすべて入っていれば準備完了です。

---

## ステップ 9: 実行テスト

```bash
cd C:\Users\kasyu\Instagram
python main.py
```

実行すると:
```
==================================================
  Instagram 自動投稿Bot
==================================================

投稿モードを選択してください:
  1. AI画像生成（プロンプトからAI画像を作成）
  2. テキスト画像（文字を画像にして投稿）

モード [1/2] (デフォルト: 1):
```

「1」を入力してAI画像モードを試してみてください。
英語でプロンプトを入れると、AIが画像を生成して自動投稿されます。

---

## 補足: トークンの有効期限について

Graph API Explorerで取得したトークンは **短期トークン**（約1〜2時間）です。

### 長期トークンに交換する方法（最大60日間有効）

ブラウザで以下のURLにアクセス（各値を自分のものに置き換え）:

```
https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={短期トークン}
```

| 値 | 確認場所 |
|---|---|
| `{app_id}` | Meta Developers → マイアプリ → アプリ設定 → ベーシック → アプリID |
| `{app_secret}` | 同じ画面の「app secret」→「表示」をクリック |
| `{短期トークン}` | ステップ6で取得したトークン |

返ってきたJSONの `access_token` が長期トークンです。
`.env` の `INSTAGRAM_ACCESS_TOKEN` を新しいトークンに書き換えてください。

---

## トラブルシューティング

| エラー内容 | 原因と対処 |
|---|---|
| `IMGUR_CLIENT_ID が .env に設定されていません` | .envファイルにIMGUR_CLIENT_IDが未記入 |
| `Imgur アップロード失敗 (HTTP 403)` | Client IDが間違っている。Imgurで再確認 |
| `アクセストークンが無効または期限切れです` | トークンの有効期限切れ。Graph API Explorerで再生成 |
| `Instagram APIエラー (code=10)` | 権限不足。instagram_content_publishが付与されているか確認 |
| `画像のアスペクト比がInstagramの要件を満たしていません` | 通常は発生しない（1080x1080で生成しているため） |
| `instagram_business_account が返ってこない` | InstagramとFacebookページが正しくリンクされていない |
