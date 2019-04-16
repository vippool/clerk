# API document

## Terms of Use

All users shall use the API in accordance with this Terms of Use.

1. You may use the API free of charge.
2. THE API IS PROVIDED "AS IS" WITHOUT ANY WARRANTIES OR INDEMNITIES. YOU SHALL, WITHOUT EXCEPTION, BEAR RESPONSIBILITY FOR ANY USE OF THE API. VIPPOOL SHALL NOT IN ANY WAY BE RESPONSIBLE OR LIABLE FOR ANY LOSSES OR DAMAGES AS A RESULT OF USING THE API.
3. You shall not, directly or indirectly, take any of the following actions;
A)	Actions which may or will violate laws and regulations;
B)	Actions which may or will be contrary to public order or morality;
C)	Actions which may or will infringe the right of a third party;
D)	Actions which may or will interfere or obstruct VIPPOOL’s business or interest.
4. VIPPOOL may block your use of the API or terminate the vippool-clerk service without notification to you, for any reason, at VIPPOOL’s discretion.

## API の利用条件

本APIは、無償でご利用いただけます。

本APIは、現状有姿、非保証および免責での提供となります。本APIは、ユーザーの責任の下に利用されるものです。
当社は一切の責任を負いません。

法令違反、公序良俗違反、他人の権利を侵害する行為またはそのおそれがある行為に関連して利用することは禁止されます。
当社の業務妨害や利益を害する利用は禁止されます。

当社の判断により、理由の如何を問わず、ユーザーに通知なく、APIによる接続遮断や運用停止することができます。

## 接続先

API 実行時は `clerk.vippool.net` へ HTTPS で接続します。

以下、引数 `coind_type` は `monacoind`, `monacoind_test` のいずれかを選択します。

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
