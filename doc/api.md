# API document

## お知らせ

VIPPOOL Clerk の API 提供は 2022年5月31日 をもちまして終了させて頂くこととなりました。
今まで多くのユーザーの皆様にご利用いただき、心から御礼申し上げます。

## 共通引数

引数 `coind_type` は `monacoind`, `monacoind_test` のいずれかを選択します。

## エラー発生時

エラー発生時は json 形式でエラーの詳細が返ります。

引数のバリデーションに失敗した場合のレスポンスは以下です。
```typescript
{
  exception: 'validation',
  element: string,
  msg: string
}
```
`element` が異常と判断された引数です。

主に検索対象が存在しない場合、404 エラーなどの場合は以下のレスポンスになります。
```typescript
{
  exception: 'HTTPException',
  explanation: string
}
```

その他の例外が発生した場合は、例外クラスの詳細がレスポンスに含まれます。
```typescript
{
  exception: 'Exception',
  type: string,
  args: any
}
```
`args` の中身は `type` に依存します。

## エクスプローラ用 API

### GET /api/v1/recentblkid
最近追加されたブロックについての情報を取得します。

#### Parameters
```typescript
coind_type: string,
n: integer
```

#### Responses
```typescript
{
  height: integer,
  hash: string,
  miners: string[]
}[]
```

### GET /api/v1/block
指定したブロックの情報を取得します。

#### Parameters
```typescript
coind_type: string,
hash: string,
height: integer
```

`height` と `hash` はいずれか片方を指定してください。
両方指定した場合は `height` が優先されます。

#### Responses
coind の RPC、`getblock` に準じた json データを返します。

### GET /api/v1/recenttxid
最近追加されたトランザクションについての情報を取得します。

#### Parameters
```typescript
coind_type: string,
n: integer
```

#### Responses
```typescript
{
  height: integer,
  txid: string,
  time: integer,
  value: float
}[]
```
時刻は UNIX タイムです。

### GET /api/v1/transaction
指定したトランザクションの情報を取得します。

#### Parameters
```typescript
coind_type: string,
txid: string,
height?: integer
```

#### Responses
coind の RPC、`getrawtransaction` に準じた json データを返します。
ただし、以下の情報が追加されています。

+ 出力方向のリンク情報

また、`height` を指定しない場合は配列で返します。

### GET /api/v1/balance
各アドレスの残高情報、残高推移情報を取得します。

#### Parameters
```typescript
coind_type: string,
addresses: string,
offset?: integer,
limit?: integer
```
`addresses` はコインアドレスの文字列配列を json 化したものです。

#### Responses
```typescript
{
  balance: float,
  history: {
    height: integer,
    txid: string,
    time: integer,
    gain: float,
    balance: float
  }[]
}
```

### GET /api/v1/millionaires
長者番付を取得します。

#### Parameters
```typescript
coind_type: string,
offset?: integer,
limit?: integer
```

#### Responses
```typescript
{
  addresses: string[],
  balance: float
}[]
```

## ユーティリティ

### GET /api/v1/address
公開鍵からコインアドレスに変換します。

#### Parameters
```typescript
coind_type: string,
pub_key: string
```

#### Responses
```typescript
{
  address: string
}
```

## 送金処理用 API

### GET /api/v1/preparetx
送金処理の第一段階です。

#### Parameters
```typescript
coind_type: string,
params: string
```

`params` は以下のデータの json 形式です。
```typescript
from: string[],
to: string[],
req_sigs: integer,
value: integer,
fee: integer,
data?: string
```
`from` および `to` は送金元・送金先の公開鍵です。
MULTISIG を使用しない場合に限ってコインアドレスでも受け付けます。

`data` は `OP_RETURN` に書く任意データで、16進数文字列で75Byteまで受け付けます。

#### Responses
```typescript
{
  sign: {
    txid: string,
    hash: string,
    reqSigs: integer
  }[],
  payload: string
}
```

### POST /api/v1/submittx
送金処理の第二段階です。

#### Parameters
```typescript
coind_type: string,
params: string
```

`params` は以下のデータの json 形式です。
```typescript
{
  sign: string[][],
  pub_key?: string,
  payload: string
}
```
`sign` は `preparetx` で返された各 hash に対する電子署名で、
それぞれ `reqSigs` 個の配列となります。

`pub_key` は、MULTISIG を使用しない場合必要となります。
不要な場合は単純に無視されます。

`payload` は `preparetx` で返されたものをそのまま送信してください。
Base64 エンコードされているため、URL エンコードが必要な場合があります。
