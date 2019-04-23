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

## Access to the server

At runtime, the API connects to `clerk.vippool.net` using HTTPS.

In the following, `coind_type` stands for either `monacoind` or `monacoind_test`.

## When an error occurs

When an error occurs, details of the failure are returned in json format.

If the error was caused by invalid parameters, the following is returned:
```typescript
{
  exception: 'validation',
  element: string,
  msg: string
}
```
Where `element` contains the name of the parameter that was deemed invalid.

When there was an HTTP error, which is most often when the connection target was not found (error 404),
the response takes the following format:
```typescript
{
  exception: 'HTTPException',
  explanation: string
}
```

When occurs an error not covered by the cases above, a response of the `Exception` class is returned:
```typescript
{
  exception: 'Exception',
  type: string,
  args: any
}
```
Where the contents of the `args` variable depends on `type`. 

## API for Explorer

### GET /api/v1/recentblkid
Get the information of recently added blocks.

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
Get the information of the specified block.

#### Parameters
```typescript
coind_type: string,
hash: string,
height: integer
```

Please provide either `height` or `hash`.
If both are present, it's `height` that will be considered.

#### Responses
Returns the json output of a `getblock` RPC to coind.

### GET /api/v1/recenttxid
Get the information of recently added transactions.

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
The time is given in UNIX Epoch time.

### GET /api/v1/transaction
Get the information of the specified transaction.

#### Parameters
```typescript
coind_type: string,
txid: string,
height?: integer
```

#### Responses
Returns the json output of a `getrawtransaction` RPC to coind,
augmented with the information about the outgoing link.

If `height` is not provided, the output will be given as an array.

### GET /api/v1/balance
Get the balance and balance change for each address in the list.

#### Parameters
```typescript
coind_type: string,
addresses: string,
offset?: integer,
limit?: integer
```
`addresses` contains the coin addresses, as array of strings formatted in json.

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
Get the list of users holding the most coins.

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

## Utils

### GET /api/v1/address
Get the coin address corresponding to a public key.

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

## API for transactions

### GET /api/v1/preparetx
It's the first stage of a transaction.

#### Parameters
```typescript
coind_type: string,
params: string
```

`params` has the following json format:
```typescript
from: string[],
to: string[],
req_sigs: integer,
value: integer,
fee: integer,
data?: string
```
`from` is the public key of the source, and `to` the one of the destination.
If MULTISIG is not used, coin addresses can also be used instead of public keys.

`data` is some arbitrary data to be written with `OP_RETURN`.
It must be specified as an hexadecimal character string representing up to 75 bytes.

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
It's the second and final stage of a transaction.

#### Parameters
```typescript
coind_type: string,
params: string
```

`params` has the following json format:
```typescript
{
  sign: string[][],
  pub_key?: string,
  payload: string
}
```
`sign` is an array of arrays:
it contains, for each hash provided by preparetx,
an array (of size reqSigs) of signatures of this hash.

`pub_key` is required when MULTISIG is not used. In other cases it is ignored.

For `payload` please use the returned value of `preparetx` as it is.
As it is encoded in base64, it may be necessary to encode it as an URL.
